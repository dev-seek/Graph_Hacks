"""Hypothesis invariants for the scoring engine (spec section 7, 'Invariants').

All randomness is seeded (derandomize=True); no I/O.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.engine.scoring import (
    LN100,
    Finding,
    Params,
    Rows,
    ScoreResult,
    TermMeta,
    lr_absent,
    lr_present,
    score_round,
)

P = Params()
SETTINGS = settings(
    max_examples=100,
    deadline=None,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

SOURCES = ["parent_story", "parent_answer", "doctor_exam", "lab_or_test"]
SYSTEMS: list[str | None] = [None, "S1", "S2", "S3"]
DISEASES = ["D1", "D2", "D3", "D4"]

freq = st.floats(min_value=0.001, max_value=1.0, allow_nan=False)
bgs = st.floats(min_value=0.0, max_value=0.99, allow_nan=False)


@st.composite
def worlds(
    draw: st.DrawFn, sources: list[str] | None = None, simple: bool = False
) -> tuple[list[Finding], Rows]:
    """A random small world: findings plus the graph rows that go with them.

    simple=True restricts links to exact / no link on present findings and F / no row on absent
    ones (the cases a tiny independent oracle can handle).
    """
    n_terms = draw(st.integers(min_value=1, max_value=5))
    n_dis = draw(st.integers(min_value=1, max_value=4))
    diseases = DISEASES[:n_dis]
    terms = [f"HP:{i}" for i in range(1, n_terms + 1)]
    srcs = sources or SOURCES
    findings = [
        Finding(t, draw(st.sampled_from(["present", "absent"])), draw(st.sampled_from(srcs)))
        for t in terms
    ]
    meta = {t: TermMeta(bg=draw(bgs), system=draw(st.sampled_from(SYSTEMS))) for t in terms}
    exact: dict[tuple[str, str], float] = {}
    broader: list[dict[str, Any]] = []
    not_present: set[tuple[str, str]] = set()
    absent_f: dict[tuple[str, str], float] = {}
    not_absent: set[tuple[str, str]] = set()
    kinds = ["none", "exact"] if simple else ["none", "exact", "broader", "not"]
    for f in findings:
        for d in diseases:
            kind = draw(st.sampled_from(kinds))
            if f.status == "present":
                if kind == "exact":
                    exact[(f.term, d)] = draw(freq)
                elif kind == "broader":
                    broader.append(
                        {
                            "finding": f.term,
                            "disease": d,
                            "via": f"HP:up{f.term}",
                            "freq": draw(freq),
                            "bg_via": draw(st.floats(min_value=0.001, max_value=0.99)),
                            "hops": draw(st.integers(min_value=1, max_value=4)),
                        }
                    )
                elif kind == "not":
                    not_present.add((f.term, d))
            elif kind == "exact":
                absent_f[(f.term, d)] = draw(freq)
            elif kind == "not":
                not_absent.add((f.term, d))
    prior_raw = {d: draw(st.floats(min_value=0.1, max_value=10.0)) for d in diseases}
    extra = draw(st.floats(min_value=0.0, max_value=50.0))
    rows = Rows(
        exact=exact,
        broader=broader,
        not_present=not_present,
        absent_F=absent_f,
        not_absent=not_absent,
        prior_raw=prior_raw,
        prior_total_raw=sum(prior_raw.values()) + extra,
        meta=meta,
    )
    return findings, rows


def posteriors(res: ScoreResult) -> dict[str, float]:
    return {c.disease: c.posterior for c in res.candidates}


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


# ------------------------------------------------------------------ finiteness / normalisation


@SETTINGS
@given(worlds())
def test_scores_are_finite_and_posteriors_in_unit_interval(
    world: tuple[list[Finding], Rows],
) -> None:
    findings, rows = world
    res = score_round(findings, rows, P)
    assert math.isfinite(res.p_d0) and 0.0 <= res.p_d0 <= 1.0
    assert math.isfinite(res.rare_mass) and math.isfinite(res.unlinked_mass)
    for c in res.candidates:
        assert math.isfinite(c.log_score)
        assert math.isfinite(c.posterior) and 0.0 <= c.posterior <= 1.0
        assert all(math.isfinite(v) for _, v in c.support)


@SETTINGS
@given(worlds())
def test_posteriors_d0_and_unlinked_share_always_sum_to_one(
    world: tuple[list[Finding], Rows],
) -> None:
    findings, rows = world
    res = score_round(findings, rows, P)
    total = sum(c.posterior for c in res.candidates) + res.p_d0 + res.unlinked_mass
    assert math.isclose(total, 1.0, rel_tol=1e-9)
    assert math.isclose(res.rare_mass, 1 - res.p_d0, rel_tol=1e-9, abs_tol=1e-12)


# ------------------------------------------------------------------ order invariance


@SETTINGS
@given(worlds(), st.data())
def test_ranking_and_scores_are_stable_under_finding_order(
    world: tuple[list[Finding], Rows], data: st.DataObject
) -> None:
    # Requires deterministic tie-breaking by finding id (also inside a disease's system groups).
    findings, rows = world
    shuffled = data.draw(st.permutations(findings))
    a = score_round(findings, rows, P)
    b = score_round(shuffled, rows, P)
    assert [c.disease for c in a.candidates] == [c.disease for c in b.candidates]
    pa, pb = posteriors(a), posteriors(b)
    assert all(close(pa[d], pb[d]) for d in pa)
    assert close(a.p_d0, b.p_d0) and close(a.unlinked_mass, b.unlinked_mass)
    assert a.n_systems == b.n_systems


# ------------------------------------------------------------------ adding a supportive finding


@SETTINGS
@given(
    worlds(sources=["doctor_exam"]),
    st.floats(min_value=0.001, max_value=0.9),
    st.floats(min_value=0.0, max_value=1.0),
    st.sampled_from(["present"]),
    st.sampled_from(SYSTEMS),
)
def test_adding_present_finding_with_f_above_bg_never_lowers_d_relative_to_unlinked_disease(
    world: tuple[list[Finding], Rows],
    bg: float,
    frac: float,
    status: str,
    system: str | None,
) -> None:
    # Statement: D and D' are both candidates before and after. New present finding T (bg_T) is
    # linked exactly to D with F > bg_T and not linked at all to D' (so D' gets eps).
    # Then (log_score(D) - log_score(D')) after >= before.
    # All sources are equal (w identical) on purpose: with unequal w the system-gamma re-ranking
    # that adding T causes can shift weight between findings and the property is not a theorem.
    findings, rows = world
    d, d2 = "D1", "D2"
    rows = replace(
        rows,
        exact={**rows.exact, ("HP:0", d): 0.5, ("HP:0", d2): 0.5},
        meta={**rows.meta, "HP:0": TermMeta(bg=0.5, system="S1")},
        prior_raw={**rows.prior_raw, d: 1.0, d2: 1.0},
        prior_total_raw=max(rows.prior_total_raw, 2.0 + sum(rows.prior_raw.values())),
    )
    base = [*findings, Finding("HP:0", "present", "doctor_exam")]
    before = score_round(base, rows, P)
    bc = {c.disease: c for c in before.candidates}
    f_val = min(1.0, bg + (1.0 - bg) * max(frac, 0.01))
    assert f_val > bg
    rows2 = replace(
        rows,
        exact={**rows.exact, ("HP:T", d): f_val},
        meta={**rows.meta, "HP:T": TermMeta(bg=bg, system=system)},
    )
    after = score_round([*base, Finding("HP:T", status, "doctor_exam")], rows2, P)  # type: ignore[arg-type]
    ac = {c.disease: c for c in after.candidates}
    gap_before = bc[d].log_score - bc[d2].log_score
    gap_after = ac[d].log_score - ac[d2].log_score
    assert gap_after >= gap_before - 1e-9


# ------------------------------------------------------------------ per-finding LR properties


@SETTINGS
@given(st.floats(min_value=0.0, max_value=0.5))
def test_absent_obligate_finding_has_lr_at_most_one_over_500_when_bg_at_most_half(
    bg: float,
) -> None:
    # NOTE: asserted on lr_absent alone (pre-clip, pre-weight). In the combined score the section 7
    # clip to +-ln100 caps the effect at x100, so the combined drop is at most that, not x500.
    assert lr_absent(1.0, bg, False) <= (1 / 500) * (1 + 1e-12)


@SETTINGS
@given(
    freq,
    st.floats(min_value=1e-4, max_value=0.99),
    st.floats(min_value=0.0, max_value=1.0),
    st.integers(min_value=1, max_value=4),
)
def test_broader_match_lr_never_exceeds_exact_match_lr_for_same_frequency_and_bg(
    f: float, bg_child: float, extra: float, hops: int
) -> None:
    # parent bg >= child bg (an ancestor is at least as common as its descendant)
    bg_parent = bg_child + extra * (1.0 - bg_child)
    exact = lr_present(f, bg_child, [], False, P)
    broad = lr_present(None, bg_child, [(f, bg_parent, hops)], False, P)
    assert broad <= exact * (1 + 1e-12)


@SETTINGS
@given(
    st.one_of(st.none(), freq),
    bgs,
    st.lists(
        st.tuples(freq, st.floats(min_value=1e-4, max_value=0.99), st.integers(-2, 8)),
        max_size=4,
    ),
    st.booleans(),
)
def test_lr_present_is_positive_finite_and_not_annotation_always_gives_point_001(
    f: float | None, bg: float, broader: list[tuple[float, float, int]], neg: bool
) -> None:
    v = lr_present(f, max(bg, 1e-4), broader, neg, P)
    assert math.isfinite(v) and v > 0
    if neg:
        assert v == 0.001


# ------------------------------------------------------------------ w = 0 == removed


@SETTINGS
@given(worlds())
def test_zero_weight_source_is_equivalent_to_removing_those_findings(
    world: tuple[list[Finding], Rows],
) -> None:
    # Requires findings with w == 0 to be dropped before system counting / gamma ranking.
    findings, rows = world
    p0 = replace(P, w={**P.w, "parent_story": 0.0})
    kept = [f for f in findings if f.source != "parent_story"]
    a = score_round(findings, rows, p0)
    b = score_round(kept, rows, p0)
    pa, pb = posteriors(a), posteriors(b)
    assert pa.keys() == pb.keys()
    assert all(close(pa[d], pb[d]) for d in pa)
    assert close(a.p_d0, b.p_d0) and close(a.unlinked_mass, b.unlinked_mass)
    assert a.n_systems == b.n_systems


# ------------------------------------------------------------------ gamma off


def oracle_gamma_off(findings: list[Finding], rows: Rows, p: Params) -> dict[str, float]:
    """Independent re-derivation for simple worlds (exact links only), gamma = 1 everywhere."""
    pri = {d: r * (1 - p.pi0) / rows.prior_total_raw for d, r in rows.prior_raw.items()}
    cands = {d for (_, d) in rows.exact}
    present = [f for f in findings if f.status == "present"]
    systems = {rows.meta[f.term].system for f in present} - {None}
    scores: dict[str, float] = {}
    for d in cands:
        s = math.log(pri[d])
        for f in findings:
            bg = max(rows.meta[f.term].bg, 1e-4)
            if f.status == "present":
                fv = rows.exact.get((f.term, d))
                lr = fv / bg if fv is not None else p.eps
            else:
                fa = rows.absent_F.get((f.term, d))
                lr = (1 - min(fa, 0.999)) / (1 - bg) if fa is not None else 1.0
            s += p.w[f.source] * max(-LN100, min(LN100, math.log(lr)))
        scores[d] = math.exp(s)
    scores["D0"] = p.pi0 * math.exp(-p.beta * max(0, len(systems) - 2))
    rest = (1 - p.pi0) - sum(pri[d] for d in cands)
    scores["U"] = rest * math.exp(sum(p.w[f.source] * math.log(p.eps) for f in present))
    z = sum(scores.values())
    return {k: v / z for k, v in scores.items()}


@SETTINGS
@given(worlds(simple=True))
def test_gamma_off_matches_an_independent_all_gamma_one_oracle(
    world: tuple[list[Finding], Rows],
) -> None:
    findings, rows = world
    res = score_round(findings, rows, replace(P, gamma_on=False))
    want = oracle_gamma_off(findings, rows, P)
    got = posteriors(res)
    assert got.keys() == {k for k in want if k not in ("D0", "U")}
    for d, v in got.items():
        assert math.isclose(v, want[d], rel_tol=1e-8, abs_tol=1e-12)
    assert math.isclose(res.p_d0, want["D0"], rel_tol=1e-8, abs_tol=1e-12)
    assert math.isclose(res.unlinked_mass, want["U"], rel_tol=1e-8, abs_tol=1e-12)


@SETTINGS
@given(worlds())
def test_gamma_on_equals_gamma_off_when_every_present_finding_is_in_its_own_system(
    world: tuple[list[Finding], Rows],
) -> None:
    findings, rows = world
    meta = {
        t: TermMeta(bg=m.bg, system=f"SYS-{i}")
        for i, (t, m) in enumerate(sorted(rows.meta.items()))
    }
    rows = replace(rows, meta=meta)
    on = score_round(findings, rows, P)
    off = score_round(findings, rows, replace(P, gamma_on=False))
    pa, pb = posteriors(on), posteriors(off)
    assert pa.keys() == pb.keys()
    assert all(close(pa[d], pb[d]) for d in pa)
    assert close(on.p_d0, off.p_d0) and close(on.unlinked_mass, off.unlinked_mass)
