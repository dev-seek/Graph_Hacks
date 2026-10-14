"""Question planner (spec §8.1): information gain over candidate diseases, pure arithmetic.

Inputs are graph rows (Q3a annotations, Q3b askable terms) plus the HPO ancestor-set cache.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Literal

D0_KEY = "D0"
MAX_BATCH = 5
MAX_PER_SYSTEM = 2
MIN_IG_BITS = 0.02
MAX_SUGGESTED_TESTS = 5
OBS_COST: Mapping[str, float] = {"home": 1.0, "exam": 0.5, "test": 0.3}
Obs = Literal["home", "exam", "test"]


@dataclass(frozen=True)
class Askable:
    term: str
    obs: Obs
    min_age: int | None
    system: str | None
    question: str
    bg: float


@dataclass
class PlannerInput:
    posteriors: dict[str, float]
    p_d0: float
    annotations: dict[str, dict[str, float]]
    askable: dict[str, Askable]
    ancestors: dict[str, set[str]]
    present: set[str]
    absent: set[str]
    asked: set[str]
    age_months: int | None
    round_kind: Literal["home", "post_doctor"]
    eps: float = 0.05


@dataclass
class Question:
    term: str
    text: str
    obs: str
    system: str | None
    ig: float
    p_yes: float
    ask_doctor: bool


@dataclass
class Plan:
    questions: list[Question] = field(default_factory=list[Question])
    suggested_tests: list[Question] = field(default_factory=list[Question])
    best_ig: dict[str, float] = field(default_factory=dict[str, float])
    pool: list[Question] = field(default_factory=list[Question])  # every eligible question


def entropy_bits(ps: Iterable[float]) -> float:
    return -sum(p * math.log2(p) for p in ps if p > 0.0)


def f_propagated(
    disease_ann: Mapping[str, float], q: str, ancestors: Mapping[str, set[str]]
) -> float | None:
    """F(D,q): max annotated frequency over annotated terms equal to or below q."""
    vals = [f for t, f in disease_ann.items() if q in ancestors.get(t, {t})]
    return max(vals) if vals else None


def information_gain(
    posts: Mapping[str, float], p_yes_by_disease: Mapping[str, float]
) -> tuple[float, float]:
    """(IG in bits, P(yes)); "not sure" is no update so only yes/no are modelled."""
    p_yes = sum(posts[d] * p_yes_by_disease[d] for d in posts)
    p_no = 1.0 - p_yes
    h_yes = h_no = 0.0
    if p_yes > 0.0:
        h_yes = entropy_bits(posts[d] * p_yes_by_disease[d] / p_yes for d in posts)
    if p_no > 0.0:
        h_no = entropy_bits(posts[d] * (1.0 - p_yes_by_disease[d]) / p_no for d in posts)
    ig = entropy_bits(posts.values()) - (p_yes * h_yes + p_no * h_no)
    return max(0.0, ig), p_yes


def _related(a: str, b: str, anc: Mapping[str, set[str]]) -> bool:
    return a == b or b in anc.get(a, {a}) or a in anc.get(b, {b})


def _eligible(q: Askable, inp: PlannerInput) -> bool:
    if q.min_age is not None and inp.age_months is not None and inp.age_months < q.min_age:
        return False
    anc = inp.ancestors
    if q.term in inp.present or q.term in inp.absent:
        return False
    # implied: an ancestor of a present finding, or at/below an absent finding
    if any(q.term in anc.get(t, {t}) for t in inp.present):
        return False
    if any(t in anc.get(q.term, {q.term}) for t in inp.absent):
        return False
    return not any(_related(q.term, a, anc) for a in inp.asked)


def propagate(inp: PlannerInput) -> dict[str, dict[str, float]]:
    """Per disease: every term at or above an annotation -> max annotated frequency below it."""
    out: dict[str, dict[str, float]] = {}
    for d in inp.posteriors:
        prop: dict[str, float] = {}
        for t, f in inp.annotations.get(d, {}).items():
            for a in inp.ancestors.get(t, {t}):
                if f > prop.get(a, -1.0):
                    prop[a] = f
        out[d] = prop
    return out


def _p_yes_by_disease(
    q: Askable, inp: PlannerInput, prop: Mapping[str, Mapping[str, float]]
) -> dict[str, float]:
    out: dict[str, float] = {D0_KEY: min(1.0, q.bg)}
    for d in inp.posteriors:
        f = prop[d].get(q.term)
        out[d] = f if f is not None else min(1.0, inp.eps * q.bg)
    return out


def plan_round(inp: PlannerInput) -> Plan:
    posts = {**inp.posteriors, D0_KEY: inp.p_d0}
    scored: list[Question] = []
    prop = propagate(inp)
    for term in sorted(inp.askable):
        q = inp.askable[term]
        if not _eligible(q, inp):
            continue
        ig, p_yes = information_gain(posts, _p_yes_by_disease(q, inp, prop))
        scored.append(
            Question(q.term, q.question, q.obs, q.system, ig, p_yes, ask_doctor=q.obs == "exam")
        )
    best = {obs: 0.0 for obs in ("home", "exam", "test")}
    allowed = {"home"} if inp.round_kind == "home" else {"home", "exam"}
    for s in scored:
        best[s.obs] = max(best[s.obs], s.ig)

    def rank(s: Question) -> tuple[float, str]:
        return (-s.ig * OBS_COST[s.obs], s.term)

    batch: list[Question] = []
    per_system: dict[str | None, int] = {}
    for s in sorted((s for s in scored if s.obs in allowed), key=rank):
        if len(batch) >= MAX_BATCH:
            break
        if s.ig < MIN_IG_BITS:
            continue
        if s.system is not None and per_system.get(s.system, 0) >= MAX_PER_SYSTEM:
            continue
        if any(_related(s.term, b.term, inp.ancestors) for b in batch):
            continue
        batch.append(s)
        per_system[s.system] = per_system.get(s.system, 0) + 1
    tests = sorted((s for s in scored if s.obs == "test"), key=rank)[:MAX_SUGGESTED_TESTS]
    return Plan(questions=batch, suggested_tests=tests, best_ig=best, pool=scored)
