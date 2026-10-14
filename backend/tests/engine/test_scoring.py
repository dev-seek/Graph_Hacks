"""Scoring engine (spec section 7): per-finding LR table and hand-computed end-to-end rounds.

Every expected value is derived by hand from the spec formulas (arithmetic in comments), not from
an implementation. Pure in-memory: no graph, no network.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

import pytest

from app.engine.scoring import (
    LN100,
    Candidate,
    Finding,
    Params,
    Rows,
    ScoreResult,
    TermMeta,
    candidate_ids,
    clip_log,
    lr_absent,
    lr_present,
    score_round,
)

P = Params()
LN_EPS = math.log(0.05)


def mk_rows(**kw: Any) -> Rows:
    base: dict[str, Any] = {
        "exact": {},
        "broader": [],
        "not_present": set(),
        "absent_F": {},
        "not_absent": set(),
        "prior_raw": {},
        "prior_total_raw": 10.0,
        "meta": {},
    }
    base.update(kw)
    return Rows(**base)


def by_id(res: ScoreResult) -> dict[str, Candidate]:
    return {c.disease: c for c in res.candidates}


def normalise(scores: dict[str, float]) -> dict[str, float]:
    z = sum(scores.values())
    return {k: v / z for k, v in scores.items()}


# ---------------------------------------------------------------- constants / clip


def test_ln100_constant_is_natural_log_of_one_hundred() -> None:
    assert LN100 == pytest.approx(4.605170185988092, rel=1e-12)


def test_params_defaults_match_spec_values() -> None:
    assert (P.eps, P.lam, P.pi0, P.beta, P.gamma_on) == (0.05, 0.35, 0.97, 0.45, True)
    assert dict(P.w) == {
        "parent_story": 0.6,
        "parent_answer": 0.7,
        "doctor_exam": 1.0,
        "lab_or_test": 1.0,
    }


@pytest.mark.parametrize(
    ("x", "expected"),
    [(10.0, LN100), (-10.0, -LN100), (1.0, 1.0), (-2.5, -2.5), (0.0, 0.0)],
)
def test_clip_log_clamps_to_plus_minus_ln100(x: float, expected: float) -> None:
    assert clip_log(x) == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------- lr_present table


def test_present_exact_annotation_gives_frequency_over_background() -> None:
    # 0.5 / 0.1 = 5
    assert lr_present(0.5, 0.1, [], False, P) == pytest.approx(5.0, rel=1e-12)


def test_present_exact_annotation_wins_over_broader_and_eps() -> None:
    assert lr_present(0.5, 0.1, [(1.0, 0.0001, 1)], False, P) == pytest.approx(5.0, rel=1e-12)


def test_present_not_annotation_gives_point_001_even_with_exact_link() -> None:
    assert lr_present(0.9, 0.1, [(0.9, 0.1, 1)], True, P) == pytest.approx(0.001, rel=1e-12)


def test_present_not_annotation_gives_point_001_without_any_link() -> None:
    assert lr_present(None, 0.1, [], True, P) == pytest.approx(0.001, rel=1e-12)


def test_present_broader_only_decays_by_exp_minus_lambda_hops() -> None:
    # 0.8 * exp(-0.35*2) / 0.2 = 4 * exp(-0.7)
    got = lr_present(None, 0.1, [(0.8, 0.2, 2)], False, P)
    assert got == pytest.approx(4 * math.exp(-0.7), rel=1e-12)


def test_present_broader_chooses_the_ancestor_maximising_lr() -> None:
    # a1: 0.8*exp(-0.7)/0.2 = 4*exp(-0.7) = 1.986 ; a2: 0.5*exp(-0.35)/0.05 = 10*exp(-0.35) = 7.05
    got = lr_present(None, 0.1, [(0.8, 0.2, 2), (0.5, 0.05, 1)], False, P)
    assert got == pytest.approx(10 * math.exp(-0.35), rel=1e-12)


def test_present_broader_at_four_hops_is_accepted() -> None:
    # 0.6 * exp(-1.4) / 0.3 = 2 * exp(-1.4)
    got = lr_present(None, 0.1, [(0.6, 0.3, 4)], False, P)
    assert got == pytest.approx(2 * math.exp(-1.4), rel=1e-12)


@pytest.mark.parametrize("hops", [5, 6, 0, -1])
def test_present_broader_outside_one_to_four_hops_is_ignored_giving_eps(hops: int) -> None:
    assert lr_present(None, 0.1, [(1.0, 0.0001, hops)], False, P) == pytest.approx(0.05, rel=1e-12)


def test_present_valid_broader_beats_ignored_out_of_range_broader() -> None:
    got = lr_present(None, 0.1, [(1.0, 0.0001, 5), (0.6, 0.3, 1)], False, P)
    assert got == pytest.approx(2 * math.exp(-0.35), rel=1e-12)


def test_present_without_any_link_gives_eps() -> None:
    assert lr_present(None, 0.1, [], False, P) == pytest.approx(0.05, rel=1e-12)


def test_present_respects_custom_eps_and_lambda() -> None:
    q = Params(eps=0.2, lam=0.5)
    assert lr_present(None, 0.1, [], False, q) == pytest.approx(0.2, rel=1e-12)
    # 0.4 * exp(-0.5*2) / 0.1 = 4 * exp(-1)
    assert lr_present(None, 0.1, [(0.4, 0.1, 2)], False, q) == pytest.approx(
        4 * math.exp(-1.0), rel=1e-12
    )


# ---------------------------------------------------------------- lr_absent table


def test_absent_with_annotation_is_one_minus_f_over_one_minus_bg() -> None:
    # (1 - 0.5) / (1 - 0.1) = 0.5 / 0.9
    assert lr_absent(0.5, 0.1, False) == pytest.approx(0.5 / 0.9, rel=1e-12)


def test_absent_obligate_annotation_caps_f_at_point_999() -> None:
    # (1 - 0.999) / (1 - 0.1) = 0.001 / 0.9
    assert lr_absent(1.0, 0.1, False) == pytest.approx(0.001 / 0.9, rel=1e-12)


def test_absent_f_equal_to_point_999_matches_f_of_one() -> None:
    assert lr_absent(0.999, 0.2, False) == pytest.approx(lr_absent(1.0, 0.2, False), rel=1e-12)


def test_absent_not_annotation_without_f_gives_one_point_five() -> None:
    assert lr_absent(None, 0.1, True) == pytest.approx(1.5, rel=1e-12)


def test_absent_without_any_annotation_gives_one() -> None:
    assert lr_absent(None, 0.1, False) == pytest.approx(1.0, rel=1e-12)


# ---------------------------------------------------------------- candidate_ids


def test_candidate_ids_is_union_of_exact_broader_and_not_present_diseases() -> None:
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5, ("HP:2", "D1"): 0.4},
        broader=[
            {
                "finding": "HP:3",
                "disease": "D2",
                "via": "HP:9",
                "freq": 0.5,
                "bg_via": 0.2,
                "hops": 1,
            }
        ],
        not_present={("HP:4", "D3")},
        absent_F={("HP:5", "D4"): 0.5},
        not_absent={("HP:5", "D5")},
    )
    assert candidate_ids(rows) == {"D1", "D2", "D3"}


def test_candidate_ids_of_empty_rows_is_empty() -> None:
    assert candidate_ids(mk_rows()) == set()


# ---------------------------------------------------------------- degenerate rounds


def test_no_findings_leaves_all_mass_on_prior_split() -> None:
    res = score_round([], mk_rows(), P)
    assert res.candidates == []
    assert res.p_d0 == pytest.approx(0.97, rel=1e-9)
    assert res.rare_mass == pytest.approx(0.03, rel=1e-9)
    assert res.unlinked_mass == pytest.approx(0.03, rel=1e-9)
    assert res.n_systems == 0


def test_present_finding_with_empty_rows_shifts_mass_only_to_d0_and_unlinked() -> None:
    # one present parent_story (w=0.6) finding, no candidates.
    # D0 = 0.97 ; unlinked = 0.03 * 0.05**0.6 ; Z = D0 + unlinked
    f = [Finding("HP:1", "present", "parent_story")]
    rows = mk_rows(meta={"HP:1": TermMeta(bg=0.1, system="S1")})
    u = 0.03 * 0.05**0.6
    res = score_round(f, rows, P)
    assert res.candidates == []
    assert res.p_d0 == pytest.approx(0.97 / (0.97 + u), rel=1e-9)
    assert res.unlinked_mass == pytest.approx(u / (0.97 + u), rel=1e-9)
    assert res.rare_mass == pytest.approx(u / (0.97 + u), rel=1e-9)


def test_absent_only_findings_without_rows_leave_prior_split_unchanged() -> None:
    # absent with no row => LR 1 for everything incl. unlinked; no present => M = 0.
    f = [Finding("HP:1", "absent", "doctor_exam")]
    res = score_round(f, mk_rows(meta={"HP:1": TermMeta(bg=0.1, system="S1")}), P)
    assert res.p_d0 == pytest.approx(0.97, rel=1e-9)
    assert res.unlinked_mass == pytest.approx(0.03, rel=1e-9)
    assert res.n_systems == 0


# ---------------------------------------------------------------- hand-computed end-to-end


def test_end_to_end_single_exact_finding_one_candidate() -> None:
    # Finding A present, doctor_exam (w=1), system S1, bg(A)=0.1.  D1: F(D1,A)=0.5 -> LR 5.
    # prior_raw D1=2, total=10 -> scaled prior = 2*0.03/10 = 0.006 ; non-candidate mass = 0.024.
    # D1  = 0.006*5            = 0.03
    # D0  = 0.97               (M=1 -> no decay)
    # U   = 0.024*0.05**1      = 0.0012
    # Z   = 1.0012
    rows = mk_rows(
        exact={("HP:A", "D1"): 0.5},
        prior_raw={"D1": 2.0},
        prior_total_raw=10.0,
        meta={"HP:A": TermMeta(bg=0.1, system="S1")},
    )
    res = score_round([Finding("HP:A", "present", "doctor_exam")], rows, P)
    z = 1.0012
    assert [c.disease for c in res.candidates] == ["D1"]
    assert res.candidates[0].posterior == pytest.approx(0.03 / z, rel=1e-9)
    assert res.p_d0 == pytest.approx(0.97 / z, rel=1e-9)
    assert res.unlinked_mass == pytest.approx(0.0012 / z, rel=1e-9)
    assert res.rare_mass == pytest.approx(0.0312 / z, rel=1e-9)
    assert res.n_systems == 1
    assert len(res.candidates[0].support) == 1
    name, val = res.candidates[0].support[0]
    assert name == "HP:A"
    assert val == pytest.approx(math.log(5), rel=1e-9)


def _ex2_rows() -> Rows:
    return mk_rows(
        exact={
            ("HP:A", "D1"): 0.8,
            ("HP:B", "D1"): 0.5,
            ("HP:C", "D1"): 0.6,
            ("HP:A", "D2"): 0.4,
            ("HP:C", "D2"): 0.5,
        },
        prior_raw={"D1": 3.0, "D2": 1.0},
        prior_total_raw=20.0,
        meta={
            "HP:A": TermMeta(bg=0.2, system="S1"),
            "HP:B": TermMeta(bg=0.1, system="S1"),
            "HP:C": TermMeta(bg=0.3, system="S2"),
        },
    )


_EX2_FINDINGS = [
    Finding("HP:A", "present", "doctor_exam"),
    Finding("HP:B", "present", "parent_answer"),
    Finding("HP:C", "present", "parent_story"),
]


def test_end_to_end_two_candidates_two_systems_applies_gamma_and_weights() -> None:
    # Priors: D1 = 3*0.03/20 = 0.0045 ; D2 = 1*0.03/20 = 0.0015 ; non-candidate = 0.03-0.006 = 0.024
    # LRs  D1: A 0.8/0.2=4, B 0.5/0.1=5, C 0.6/0.3=2
    #      D2: A 0.4/0.2=2, B eps=0.05 (no link), C 0.5/0.3=5/3
    # gamma (per disease, system S1={A,B}, S2={C}; sort by |ln LR| desc):
    #      D1: S1 -> B(1.609) g=1, A(1.386) g=0.6 ; S2 -> C g=1
    #      D2: S1 -> B(|ln .05|=2.996) g=1, A(0.693) g=0.6 ; S2 -> C g=1
    # weights: A doctor_exam 1.0, B parent_answer 0.7, C parent_story 0.6
    # D1 = 0.0045 * 5**0.7 * 4**(1*0.6) * 2**0.6
    # D2 = 0.0015 * 0.05**0.7 * 2**(1*0.6) * (5/3)**0.6
    # D0 = 0.97 (M = 2 -> max(0, 0) = 0)
    # U: all |ln eps| equal, ties broken by id: A g=1 (w1), B g=0.6 (w .7 -> .42), C g=1 (w .6)
    #    exponent = 1 + 0.42 + 0.6 = 2.02 ; U = 0.024 * 0.05**2.02
    raw = {
        "D1": 0.0045 * 5**0.7 * 4**0.6 * 2**0.6,
        "D2": 0.0015 * 0.05**0.7 * 2**0.6 * (5 / 3) ** 0.6,
        "D0": 0.97,
        "U": 0.024 * 0.05**2.02,
    }
    exp = normalise(raw)
    res = score_round(_EX2_FINDINGS, _ex2_rows(), P)
    got = by_id(res)
    assert got["D1"].posterior == pytest.approx(exp["D1"], rel=1e-9)
    assert got["D2"].posterior == pytest.approx(exp["D2"], rel=1e-9)
    assert res.p_d0 == pytest.approx(exp["D0"], rel=1e-9)
    assert res.unlinked_mass == pytest.approx(exp["U"], rel=1e-9)
    assert res.rare_mass == pytest.approx(1 - exp["D0"], rel=1e-9)
    assert res.n_systems == 2
    assert [c.disease for c in res.candidates] == sorted(("D1", "D2"), key=lambda d: -exp[d])
    # log_score differences are normalisation-independent
    assert got["D1"].log_score - got["D2"].log_score == pytest.approx(
        math.log(raw["D1"] / raw["D2"]), rel=1e-9
    )


def test_end_to_end_two_candidates_with_gamma_off_uses_gamma_one_everywhere() -> None:
    # Same world, gamma_on=False: every gamma = 1.
    # D1 = 0.0045 * 4**1 * 5**0.7 * 2**0.6 ; D2 = 0.0015 * 2**1 * 0.05**0.7 * (5/3)**0.6
    # U exponent = 1 + 0.7 + 0.6 = 2.3 ; D0 = 0.97
    raw = {
        "D1": 0.0045 * 4 * 5**0.7 * 2**0.6,
        "D2": 0.0015 * 2 * 0.05**0.7 * (5 / 3) ** 0.6,
        "D0": 0.97,
        "U": 0.024 * 0.05**2.3,
    }
    exp = normalise(raw)
    res = score_round(_EX2_FINDINGS, _ex2_rows(), replace(P, gamma_on=False))
    got = by_id(res)
    assert got["D1"].posterior == pytest.approx(exp["D1"], rel=1e-9)
    assert got["D2"].posterior == pytest.approx(exp["D2"], rel=1e-9)
    assert res.p_d0 == pytest.approx(exp["D0"], rel=1e-9)
    assert res.unlinked_mass == pytest.approx(exp["U"], rel=1e-9)


def test_end_to_end_three_systems_decay_not_annotation_broader_and_absent() -> None:
    # Findings: A present doctor_exam (S1, bg .1), B present lab_or_test (S2, bg .1),
    #           C present parent_story (S3, bg .1), E absent parent_answer (S1, bg .2).
    # Priors: D1 = D2 = 5*0.03/50 = 0.003 ; non-candidate = 0.03 - 0.006 = 0.024
    # D1: A exact F=0.2 -> 0.2/0.1 = 2 ; B exact F=0.3 -> 0.3/0.1 = 3 ;
    #     C broader (via 0.5, bg_via 0.25, 2 hops): 0.5*exp(-0.7)/0.25 = 2*exp(-0.7) = 0.9932
    #     E absent, F=0.5, bg=0.2: (1-0.5)/(1-0.2) = 0.625
    #     all present findings in different systems -> gamma = 1 ; absent gamma = 1
    #     D1 = 0.003 * 2**1 * 3**1 * (2*exp(-0.7))**0.6 * 0.625**0.7
    # D2: A,B no link -> eps each (w=1); C has NOT annotation -> 0.001, clipped to 0.01, w=0.6
    #     E absent, NOT annotation -> 1.5, w = 0.7
    #     D2 = 0.003 * 0.05 * 0.05 * 0.01**0.6 * 1.5**0.7
    # D0 = 0.97 * exp(-0.45*(3-2)) ; U = 0.024 * 0.05**(1 + 1 + 0.6)
    raw = {
        "D1": 0.003 * 2 * 3 * (2 * math.exp(-0.7)) ** 0.6 * 0.625**0.7,
        "D2": 0.003 * 0.05 * 0.05 * 0.01**0.6 * 1.5**0.7,
        "D0": 0.97 * math.exp(-0.45),
        "U": 0.024 * 0.05**2.6,
    }
    exp = normalise(raw)
    rows = mk_rows(
        exact={("HP:A", "D1"): 0.2, ("HP:B", "D1"): 0.3},
        broader=[
            {
                "finding": "HP:C",
                "disease": "D1",
                "via": "HP:Cp",
                "freq": 0.5,
                "bg_via": 0.25,
                "hops": 2,
            }
        ],
        not_present={("HP:C", "D2")},
        absent_F={("HP:E", "D1"): 0.5},
        not_absent={("HP:E", "D2")},
        prior_raw={"D1": 5.0, "D2": 5.0},
        prior_total_raw=50.0,
        meta={
            "HP:A": TermMeta(bg=0.1, system="S1"),
            "HP:B": TermMeta(bg=0.1, system="S2"),
            "HP:C": TermMeta(bg=0.1, system="S3"),
            "HP:E": TermMeta(bg=0.2, system="S1"),
        },
    )
    findings = [
        Finding("HP:A", "present", "doctor_exam"),
        Finding("HP:B", "present", "lab_or_test"),
        Finding("HP:C", "present", "parent_story"),
        Finding("HP:E", "absent", "parent_answer"),
    ]
    res = score_round(findings, rows, P)
    got = by_id(res)
    assert set(got) == {"D1", "D2"}
    assert got["D1"].posterior == pytest.approx(exp["D1"], rel=1e-9)
    assert got["D2"].posterior == pytest.approx(exp["D2"], rel=1e-9)
    assert res.p_d0 == pytest.approx(exp["D0"], rel=1e-9)
    assert res.unlinked_mass == pytest.approx(exp["U"], rel=1e-9)
    assert res.n_systems == 3
    # D1 support: unclipped ln LR, sorted by |.| desc: B 1.0986, A 0.6931, E -0.4700, C -0.00685
    names = [s[0] for s in got["D1"].support]
    assert names == ["HP:B", "HP:A", "HP:E", "HP:C"]
    vals = dict(got["D1"].support)
    assert vals["HP:B"] == pytest.approx(math.log(3), rel=1e-9)
    assert vals["HP:A"] == pytest.approx(math.log(2), rel=1e-9)
    assert vals["HP:E"] == pytest.approx(math.log(0.625), rel=1e-9)
    assert vals["HP:C"] == pytest.approx(math.log(2) - 0.7, rel=1e-9)
    # D2 support keeps the unclipped NOT likelihood ratio, strongest first
    assert got["D2"].support[0][0] == "HP:C"
    assert got["D2"].support[0][1] == pytest.approx(math.log(0.001), rel=1e-9)


# ---------------------------------------------------------------- single-rule end-to-end


def _single(findings: list[Finding], rows: Rows, p: Params = P) -> tuple[ScoreResult, Candidate]:
    res = score_round(findings, rows, p)
    assert len(res.candidates) == 1
    return res, res.candidates[0]


def test_gamma_damps_third_and_fourth_present_finding_in_one_system_to_point_35() -> None:
    # One system, LRs 9, 6, 3, 2 (F/bg with bg .1) => sorted gammas 1, 0.6, 0.35, 0.35 ; w = 1.
    # D1/D0 = (0.003 / 0.97) * 9 * 6**0.6 * 3**0.35 * 2**0.35   (M = 1: D0 undecayed)
    fs = [Finding(f"HP:{i}", "present", "doctor_exam") for i in range(1, 5)]
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.2, ("HP:2", "D1"): 0.3, ("HP:3", "D1"): 0.6, ("HP:4", "D1"): 0.9},
        prior_raw={"D1": 1.0},
        meta={f"HP:{i}": TermMeta(bg=0.1, system="S1") for i in range(1, 5)},
    )
    res, c = _single(fs, rows)
    want = (0.003 / 0.97) * 9 * 6**0.6 * 3**0.35 * 2**0.35
    assert c.posterior / res.p_d0 == pytest.approx(want, rel=1e-9)


def test_gamma_ranks_by_absolute_log_lr_so_strong_opposing_finding_takes_gamma_one() -> None:
    # Same system. A: LR 2 (ln .693) ; B: LR 0.05 (|ln| 2.996) -> B first (g=1), A second (g=.6).
    # D1/D0 = (0.003/0.97) * 0.05 * 2**0.6
    fs = [Finding("HP:A", "present", "doctor_exam"), Finding("HP:B", "present", "doctor_exam")]
    rows = mk_rows(
        exact={("HP:A", "D1"): 0.2},
        prior_raw={"D1": 1.0},
        meta={"HP:A": TermMeta(bg=0.1, system="S1"), "HP:B": TermMeta(bg=0.1, system="S1")},
    )
    res, c = _single(fs, rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 0.05 * 2**0.6, rel=1e-9)


@pytest.mark.parametrize(
    ("source", "w"),
    [("parent_story", 0.6), ("parent_answer", 0.7), ("doctor_exam", 1.0), ("lab_or_test", 1.0)],
)
def test_source_weight_exponentiates_the_likelihood_ratio(source: str, w: float) -> None:
    # LR = 0.5/0.1 = 5 ; D1/D0 = (0.003/0.97) * 5**w
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.1, system="S1")},
    )
    res, c = _single([Finding("HP:1", "present", source)], rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 5**w, rel=1e-9)


def test_strong_present_lr_is_clipped_to_ln100_in_the_sum_but_not_in_support() -> None:
    # F=0.5, bg=0.001 -> LR 500 > 100 : sum uses 100, support keeps ln 500.
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.001, system="S1")},
    )
    res, c = _single([Finding("HP:1", "present", "doctor_exam")], rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 100, rel=1e-9)
    assert c.support[0][1] == pytest.approx(math.log(500), rel=1e-9)


def test_not_annotation_on_present_finding_is_clipped_to_one_over_one_hundred() -> None:
    rows = mk_rows(
        not_present={("HP:1", "D1")},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.1, system="S1")},
    )
    res, c = _single([Finding("HP:1", "present", "doctor_exam")], rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 0.01, rel=1e-9)
    assert c.support[0][1] == pytest.approx(math.log(0.001), rel=1e-9)


def test_background_frequency_is_floored_at_1e_minus_4() -> None:
    # bg meta 0.0 -> floored to 1e-4 ; F = 2e-4 -> LR = 2 ; D1/D0 = (0.003/0.97) * 2
    rows = mk_rows(
        exact={("HP:1", "D1"): 2e-4},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.0, system="S1")},
    )
    res, c = _single([Finding("HP:1", "present", "doctor_exam")], rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 2, rel=1e-9)


def test_absent_finding_with_annotation_multiplies_by_one_minus_f_over_one_minus_bg() -> None:
    # present HP:1 (LR 5 via 0.5/0.1) plus absent HP:2 with F=0.4, bg=0.2 -> 0.6/0.8 = 0.75 (w=1)
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5},
        absent_F={("HP:2", "D1"): 0.4},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.1, system="S1"), "HP:2": TermMeta(bg=0.2, system="S1")},
    )
    fs = [Finding("HP:1", "present", "doctor_exam"), Finding("HP:2", "absent", "lab_or_test")]
    res, c = _single(fs, rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 5 * 0.75, rel=1e-9)


def test_absent_obligate_finding_is_capped_by_the_clip_at_one_over_one_hundred() -> None:
    # F=1 -> LR = 0.001/0.8 = 0.00125 < 0.01 -> clipped to 0.01 in the combined sum.
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5},
        absent_F={("HP:2", "D1"): 1.0},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.1, system="S1"), "HP:2": TermMeta(bg=0.2, system="S1")},
    )
    fs = [Finding("HP:1", "present", "doctor_exam"), Finding("HP:2", "absent", "doctor_exam")]
    res, c = _single(fs, rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 5 * 0.01, rel=1e-9)


def test_absent_finding_without_row_for_a_candidate_has_likelihood_ratio_one() -> None:
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5},
        prior_raw={"D1": 1.0},
        meta={"HP:1": TermMeta(bg=0.1, system="S1"), "HP:2": TermMeta(bg=0.2, system="S1")},
    )
    fs = [Finding("HP:1", "present", "doctor_exam"), Finding("HP:2", "absent", "doctor_exam")]
    res, c = _single(fs, rows)
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 5, rel=1e-9)


def test_absent_findings_do_not_count_towards_distinct_systems_and_use_gamma_one() -> None:
    # Present HP:1 (S1). Two absent findings in S1 and S2 with F rows: gamma stays 1 for both and
    # M stays 1. LR_abs: (1-.5)/(1-.1)=5/9 and (1-.2)/(1-.1)=8/9.
    rows = mk_rows(
        exact={("HP:1", "D1"): 0.5},
        absent_F={("HP:2", "D1"): 0.5, ("HP:3", "D1"): 0.2},
        prior_raw={"D1": 1.0},
        meta={
            "HP:1": TermMeta(bg=0.1, system="S1"),
            "HP:2": TermMeta(bg=0.1, system="S1"),
            "HP:3": TermMeta(bg=0.1, system="S2"),
        },
    )
    fs = [
        Finding("HP:1", "present", "doctor_exam"),
        Finding("HP:2", "absent", "doctor_exam"),
        Finding("HP:3", "absent", "doctor_exam"),
    ]
    res, c = _single(fs, rows)
    assert res.n_systems == 1
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * 5 * (5 / 9) * (8 / 9), rel=1e-9)


def test_distinct_systems_ignore_findings_without_a_system() -> None:
    fs = [
        Finding("HP:1", "present", "doctor_exam"),
        Finding("HP:2", "present", "doctor_exam"),
        Finding("HP:3", "present", "doctor_exam"),
        Finding("HP:4", "present", "doctor_exam"),
    ]
    meta = {
        "HP:1": TermMeta(bg=0.1, system="S1"),
        "HP:2": TermMeta(bg=0.1, system="S2"),
        "HP:3": TermMeta(bg=0.1, system=None),
        "HP:4": TermMeta(bg=0.1, system=None),
    }
    res = score_round(fs, mk_rows(meta=meta), P)
    assert res.n_systems == 2


def test_d0_multi_system_decay_applies_beta_per_system_beyond_two() -> None:
    # M = 4 -> D0 = 0.97 * exp(-0.45*2). One candidate D1 with LR 1 on every finding (F = bg),
    # so D1/D0 = (0.003/0.97 ) * exp(+0.9) * 1  (gamma = 1: one finding per system).
    fs = [Finding(f"HP:{i}", "present", "doctor_exam") for i in range(1, 5)]
    rows = mk_rows(
        exact={(f"HP:{i}", "D1"): 0.1 for i in range(1, 5)},
        prior_raw={"D1": 1.0},
        meta={f"HP:{i}": TermMeta(bg=0.1, system=f"S{i}") for i in range(1, 5)},
    )
    res, c = _single(fs, rows)
    assert res.n_systems == 4
    assert c.posterior / res.p_d0 == pytest.approx((0.003 / 0.97) * math.exp(0.9), rel=1e-9)


def test_candidates_are_sorted_by_posterior_descending() -> None:
    res = score_round(_EX2_FINDINGS, _ex2_rows(), P)
    posts = [c.posterior for c in res.candidates]
    assert posts == sorted(posts, reverse=True)


def test_posteriors_d0_and_unlinked_share_sum_to_one() -> None:
    res = score_round(_EX2_FINDINGS, _ex2_rows(), P)
    total = sum(c.posterior for c in res.candidates) + res.p_d0 + res.unlinked_mass
    assert total == pytest.approx(1.0, rel=1e-12)
    assert res.rare_mass == pytest.approx(1 - res.p_d0, rel=1e-12)
