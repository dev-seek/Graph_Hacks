"""Scoring maths (spec §7): pure arithmetic over the rows FalkorDB returned (AGENTS.md rules 3-4).

No I/O here. The caller runs Q1/Q2 (`app.graph.queries`) and hands the rows in as `Rows`.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

LN100 = math.log(100)
BG_FLOOR = 1e-4
NOT_PRESENT_LR = 0.001
NOT_ABSENT_LR = 1.5
GAMMAS = (1.0, 0.6, 0.35)
MAX_HOPS = 4
DEFAULT_WEIGHTS: Mapping[str, float] = {
    "parent_story": 0.6,
    "parent_answer": 0.7,
    "doctor_exam": 1.0,
    "lab_or_test": 1.0,
}


@dataclass(frozen=True)
class Params:
    eps: float = 0.05
    lam: float = 0.35
    pi0: float = 0.97
    beta: float = 0.45
    gamma_on: bool = True
    w: Mapping[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))


@dataclass(frozen=True)
class Finding:
    term: str
    status: Literal["present", "absent"]
    source: str


@dataclass(frozen=True)
class TermMeta:
    bg: float
    system: str | None


@dataclass
class Rows:
    exact: dict[tuple[str, str], float] = field(default_factory=dict[tuple[str, str], float])
    broader: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    not_present: set[tuple[str, str]] = field(default_factory=set[tuple[str, str]])
    absent_F: dict[tuple[str, str], float] = field(default_factory=dict[tuple[str, str], float])
    not_absent: set[tuple[str, str]] = field(default_factory=set[tuple[str, str]])
    prior_raw: dict[str, float] = field(default_factory=dict[str, float])
    prior_total_raw: float = 1.0
    meta: dict[str, TermMeta] = field(default_factory=dict[str, TermMeta])


@dataclass
class Candidate:
    disease: str
    posterior: float
    log_score: float
    support: list[tuple[str, float]]


@dataclass
class ScoreResult:
    candidates: list[Candidate]
    p_d0: float
    rare_mass: float
    unlinked_mass: float
    n_systems: int


def clip_log(x: float) -> float:
    return max(-LN100, min(LN100, x))


def lr_present(
    F: float | None,  # noqa: N803 (spec symbol F(D,t))
    bg: float,
    broader: Sequence[tuple[float, float, int]],
    neg: bool,
    p: Params,
) -> float:
    if neg:
        return NOT_PRESENT_LR
    if F is not None:
        return F / max(bg, BG_FLOOR)
    usable = [
        freq * math.exp(-p.lam * hops) / max(bg_a, BG_FLOOR)
        for freq, bg_a, hops in broader
        if 1 <= hops <= MAX_HOPS
    ]
    return max(usable) if usable else p.eps


def lr_absent(
    F: float | None,  # noqa: N803
    bg: float,
    neg_cover: bool,
) -> float:
    if F is not None:
        return (1.0 - min(F, 0.999)) / max(1.0 - max(bg, BG_FLOOR), BG_FLOOR)
    return NOT_ABSENT_LR if neg_cover else 1.0


def candidate_ids(rows: Rows) -> set[str]:
    ids = {d for _, d in rows.exact}
    ids |= {str(r["disease"]) for r in rows.broader}
    ids |= {d for _, d in rows.not_present}
    return ids


def _gammas(items: Sequence[tuple[str, str | None, float]], p: Params) -> dict[str, float]:
    """items = (finding term, system, |log LR|) for present findings -> gamma per term."""
    out: dict[str, float] = {}
    if not p.gamma_on:
        return {t: 1.0 for t, _, _ in items}
    groups: dict[str | None, list[tuple[str, float]]] = defaultdict(list)
    for term, system, mag in items:
        groups[system].append((term, mag))
    for members in groups.values():
        members.sort(key=lambda m: (-m[1], m[0]))
        for k, (term, _) in enumerate(members):
            out[term] = GAMMAS[min(k, len(GAMMAS) - 1)]
    return out


def _meta(rows: Rows, term: str) -> TermMeta:
    try:
        return rows.meta[term]
    except KeyError:
        raise ValueError(f"no term meta for finding {term}") from None


def _logsumexp(xs: Sequence[float]) -> float:
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def score_round(findings: Sequence[Finding], rows: Rows, p: Params) -> ScoreResult:
    present = [f for f in findings if f.status == "present" and p.w[f.source] > 0]
    absent = [f for f in findings if f.status == "absent" and p.w[f.source] > 0]
    scale = (1.0 - p.pi0) / rows.prior_total_raw
    broader_by: dict[tuple[str, str], list[tuple[float, float, int]]] = defaultdict(list)
    for r in rows.broader:
        broader_by[(str(r["finding"]), str(r["disease"]))].append(
            (float(r["freq"]), float(r["bg_via"]), int(r["hops"]))
        )

    systems = {_meta(rows, f.term).system for f in present} - {None}
    log_d0 = math.log(p.pi0) - p.beta * max(0, len(systems) - 2)

    cands = sorted(candidate_ids(rows))
    log_scores: dict[str, float] = {}
    supports: dict[str, list[tuple[str, float]]] = {}
    scaled_prior_sum = 0.0
    for d in cands:
        prior = rows.prior_raw[d] * scale
        scaled_prior_sum += prior
        lrs: list[tuple[Finding, float]] = []
        for f in present:
            bg = _meta(rows, f.term).bg
            lr = lr_present(
                rows.exact.get((f.term, d)),
                bg,
                broader_by.get((f.term, d), []),
                (f.term, d) in rows.not_present,
                p,
            )
            lrs.append((f, math.log(lr)))
        gam = _gammas([(f.term, _meta(rows, f.term).system, abs(x)) for f, x in lrs], p)
        total = math.log(prior)
        support: list[tuple[str, float]] = []
        for f, x in lrs:
            total += p.w[f.source] * gam[f.term] * clip_log(x)
            support.append((f.term, x))
        for f in absent:
            bg = _meta(rows, f.term).bg
            x = math.log(
                lr_absent(rows.absent_F.get((f.term, d)), bg, (f.term, d) in rows.not_absent)
            )
            total += p.w[f.source] * clip_log(x)
            support.append((f.term, x))
        support.sort(key=lambda s: (-abs(s[1]), s[0]))
        log_scores[d] = total
        supports[d] = support

    unlinked_prior = max(0.0, (1.0 - p.pi0) - scaled_prior_sum)
    terms: list[float] = [log_d0, *log_scores.values()]
    log_unlinked: float | None = None
    if unlinked_prior > 0.0:
        eps_items = [(f.term, _meta(rows, f.term).system, abs(math.log(p.eps))) for f in present]
        gam = _gammas(eps_items, p)
        log_unlinked = math.log(unlinked_prior) + sum(
            p.w[f.source] * gam[f.term] * clip_log(math.log(p.eps)) for f in present
        )
        terms.append(log_unlinked)
    z = _logsumexp(terms)
    out = [Candidate(d, math.exp(log_scores[d] - z), log_scores[d], supports[d]) for d in cands]
    out.sort(key=lambda c: (-c.posterior, c.disease))
    p_d0 = math.exp(log_d0 - z)
    unlinked = math.exp(log_unlinked - z) if log_unlinked is not None else 0.0
    return ScoreResult(out, p_d0, 1.0 - p_d0, unlinked, len(systems))
