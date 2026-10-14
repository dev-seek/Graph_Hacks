"""Planner tests (spec 8.1). Hand-computed values; pure functions, no DB."""

from __future__ import annotations

import math
from typing import Literal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.engine.planner import (
    Askable,
    Plan,
    PlannerInput,
    entropy_bits,
    f_propagated,
    information_gain,
    plan_round,
)

Obs = Literal["home", "exam", "test"]

# Shared fixture numbers: post(A)=0.5, post(B)=0.4, p_D0=0.1, bg=0.01, eps=0.05.
# B has no annotations so p_B(q) = eps*bg = 0.0005 for every q, D0 uses bg = 0.01.
POSTS = {"A": 0.5, "B": 0.4}
P_D0 = 0.1


def _askable(
    term: str,
    obs: Obs = "home",
    system: str | None = None,
    min_age: int | None = None,
    bg: float = 0.01,
) -> Askable:
    return Askable(
        term=term,
        obs=obs,
        min_age=min_age,
        system=system if system is not None else f"sys_{term}",
        question=f"Does your child have {term}?",
        bg=bg,
    )


def build(
    askables: list[Askable],
    freq_a: dict[str, float] | None = None,
    extra_anc: dict[str, set[str]] | None = None,
    present: set[str] | None = None,
    absent: set[str] | None = None,
    asked: set[str] | None = None,
    age_months: int | None = 120,
    round_kind: Literal["home", "post_doctor"] = "home",
    annotations_b: dict[str, float] | None = None,
) -> PlannerInput:
    """Disease A is annotated with freq_a; B is annotated with annotations_b (default none)."""
    freq_a = freq_a or {}
    extra_anc = extra_anc or {}
    present = present or set()
    absent = absent or set()
    asked = asked or set()
    annotations_b = annotations_b or {}
    terms: set[str] = {a.term for a in askables}
    terms |= set(freq_a) | set(annotations_b) | present | absent | asked | set(extra_anc)
    for anc in extra_anc.values():
        terms |= anc
    ancestors = {t: {t} | extra_anc.get(t, set()) for t in terms}
    return PlannerInput(
        posteriors=dict(POSTS),
        p_d0=P_D0,
        annotations={"A": dict(freq_a), "B": dict(annotations_b)},
        askable={a.term: a for a in askables},
        ancestors=ancestors,
        present=present,
        absent=absent,
        asked=asked,
        age_months=age_months,
        round_kind=round_kind,
    )


def q_terms(plan: Plan) -> list[str]:
    return [q.term for q in plan.questions]


# ---------------------------------------------------------------- entropy_bits


def test_entropy_of_fair_coin_is_one_bit() -> None:
    assert entropy_bits([0.5, 0.5]) == pytest.approx(1.0, rel=1e-12)


def test_entropy_of_four_equal_outcomes_is_two_bits() -> None:
    assert entropy_bits([0.25] * 4) == pytest.approx(2.0, rel=1e-12)


def test_entropy_of_certain_outcome_is_zero_and_zero_terms_are_ignored() -> None:
    assert entropy_bits([1.0]) == 0.0
    assert entropy_bits([1.0, 0.0, 0.0]) == 0.0


def test_entropy_of_skewed_pair_matches_hand_value() -> None:
    # H(0.25, 0.75) = -0.25*log2(0.25) - 0.75*log2(0.75) = 0.5 + 0.75*0.4150375 = 0.8112781
    assert entropy_bits([0.25, 0.75]) == pytest.approx(0.8112781244591328, rel=1e-9)


# ---------------------------------------------------------------- f_propagated


def test_f_propagated_returns_direct_annotation_frequency() -> None:
    anc = {"T": {"T"}}
    assert f_propagated({"T": 0.4}, "T", anc) == pytest.approx(0.4)


def test_f_propagated_takes_max_over_annotated_descendants() -> None:
    anc = {"P": {"P"}, "C1": {"C1", "P"}, "C2": {"C2", "P"}}
    assert f_propagated({"C1": 0.3, "C2": 0.8}, "P", anc) == pytest.approx(0.8)


def test_f_propagated_includes_direct_annotation_in_max() -> None:
    anc = {"P": {"P"}, "C": {"C", "P"}}
    assert f_propagated({"P": 0.9, "C": 0.2}, "P", anc) == pytest.approx(0.9)


def test_f_propagated_is_none_when_only_an_ancestor_is_annotated() -> None:
    anc = {"P": {"P"}, "C": {"C", "P"}}
    assert f_propagated({"P": 0.9}, "C", anc) is None


def test_f_propagated_is_none_for_unrelated_term() -> None:
    anc = {"X": {"X"}, "Y": {"Y"}}
    assert f_propagated({"X": 0.5}, "Y", anc) is None


# ---------------------------------------------------------------- information_gain


def test_information_gain_matches_hand_computed_two_diseases_plus_d0() -> None:
    # posts: A=0.5, B=0.3, D0=0.2 ; p_yes: A=0.9, B=0.01 (=eps*bg=0.05*0.2), D0=0.2 (bg)
    # P(yes) = 0.5*0.9 + 0.3*0.01 + 0.2*0.2 = 0.45 + 0.003 + 0.04 = 0.493
    # post|yes = (0.45, 0.003, 0.04)/0.493 = (0.912779, 0.006085, 0.081136)
    # post|no  = (0.05, 0.297, 0.16)/0.507 = (0.098619, 0.585799, 0.315582)
    # H(post) = -(0.5 log2 .5 + 0.3 log2 .3 + 0.2 log2 .2) = 0.5 + 0.521090 + 0.464386 = 1.485475
    # H(yes) = 0.1208..., H(no) = 1.3107... (to 4 d.p.: 0.5115 and 1.2878 weighted below)
    # IG = H(post) - (0.493*H(yes) + 0.507*H(no)) = 0.5967372547
    ig, p_yes = information_gain({"A": 0.5, "B": 0.3, "D0": 0.2}, {"A": 0.9, "B": 0.01, "D0": 0.2})
    assert p_yes == pytest.approx(0.493, rel=1e-9)
    assert ig == pytest.approx(0.5967372547261968, rel=1e-9)


def test_information_gain_is_zero_when_every_disease_has_same_p_yes() -> None:
    # P(yes)=0.3 for all, so conditioning on the answer does not change the posterior.
    ig, p_yes = information_gain({"A": 0.5, "B": 0.3, "D0": 0.2}, {"A": 0.3, "B": 0.3, "D0": 0.3})
    assert p_yes == pytest.approx(0.3, rel=1e-9)
    assert ig == pytest.approx(0.0, abs=1e-12)


def test_information_gain_is_zero_and_finite_when_everyone_certainly_says_yes() -> None:
    ig, p_yes = information_gain({"A": 0.6, "D0": 0.4}, {"A": 1.0, "D0": 1.0})
    assert p_yes == pytest.approx(1.0)
    assert ig == pytest.approx(0.0, abs=1e-12)


def test_information_gain_is_one_bit_for_perfect_separator_of_two_equal_diseases() -> None:
    # A always yes, B always no, equal posts: answer reveals disease, IG = H(0.5,0.5) = 1.
    ig, _ = information_gain({"A": 0.5, "B": 0.5}, {"A": 1.0, "B": 0.0})
    assert ig == pytest.approx(1.0, rel=1e-9)


@settings(max_examples=200, derandomize=True, deadline=None)
@given(
    weights=st.lists(st.floats(min_value=0.001, max_value=1.0), min_size=2, max_size=6),
    data=st.data(),
)
def test_information_gain_is_never_negative(weights: list[float], data: st.DataObject) -> None:
    total = sum(weights)
    posts = {f"D{i}": w / total for i, w in enumerate(weights)}
    posts["D0"] = posts.pop("D0")  # keep a D0 key present
    p_yes = {k: data.draw(st.floats(min_value=0.0, max_value=1.0), label=f"p_{k}") for k in posts}
    ig, p = information_gain(posts, p_yes)
    assert math.isfinite(ig)
    assert ig >= -1e-12
    assert -1e-12 <= p <= 1 + 1e-12


# ---------------------------------------------------------------- plan_round: basics


def test_plan_round_question_carries_raw_ig_and_p_yes_matching_hand_values() -> None:
    # A: F=0.9 ; B: eps*bg=0.0005 ; D0: bg=0.01
    # P(yes) = 0.5*0.9 + 0.4*0.0005 + 0.1*0.01 = 0.45 + 0.0002 + 0.001 = 0.4512
    inp = build([_askable("T1", system="s1")], freq_a={"T1": 0.9})
    plan = plan_round(inp)
    assert q_terms(plan) == ["T1"]
    q = plan.questions[0]
    assert q.p_yes == pytest.approx(0.4512, rel=1e-9)
    assert q.ig == pytest.approx(0.7480589315689101, rel=1e-9)
    assert q.obs == "home"
    assert q.system == "s1"
    assert q.ask_doctor is False


def test_plan_round_uses_ancestor_propagation_for_askable_parent_of_annotated_child() -> None:
    # Parent P is askable; disease A is annotated only on child C with F=0.9 -> p_A(P)=0.9.
    inp = build([_askable("P")], freq_a={"C": 0.9}, extra_anc={"C": {"P"}})
    plan = plan_round(inp)
    assert q_terms(plan) == ["P"]
    assert plan.questions[0].p_yes == pytest.approx(0.4512, rel=1e-9)


def test_plan_round_orders_questions_by_information_gain_descending() -> None:
    # IG rises with F(A,q) in this fixture: 0.9 > 0.8 > 0.7 > 0.6.
    askables = [_askable(t) for t in ("Ta", "Tb", "Tc", "Td")]
    inp = build(askables, freq_a={"Ta": 0.6, "Tb": 0.9, "Tc": 0.7, "Td": 0.8})
    plan = plan_round(inp)
    assert q_terms(plan) == ["Tb", "Td", "Tc", "Ta"]
    igs = [q.ig for q in plan.questions]
    assert igs == sorted(igs, reverse=True)
    assert all(ig >= 0 for ig in igs)


def test_plan_round_breaks_ties_by_term_id_regardless_of_input_order() -> None:
    names = ["T3", "T1", "T2", "T4"]
    freq = dict.fromkeys(names, 0.9)
    plan1 = plan_round(build([_askable(t) for t in names], freq_a=freq))
    plan2 = plan_round(build([_askable(t) for t in reversed(names)], freq_a=freq))
    assert q_terms(plan1) == ["T1", "T2", "T3", "T4"]
    assert q_terms(plan2) == q_terms(plan1)


# ---------------------------------------------------------------- batch rules


def test_plan_round_returns_at_most_five_questions_when_many_are_informative() -> None:
    names = [f"T{i}" for i in range(1, 9)]
    inp = build([_askable(t) for t in names], freq_a=dict.fromkeys(names, 0.9))
    plan = plan_round(inp)
    assert q_terms(plan) == ["T1", "T2", "T3", "T4", "T5"]


def test_plan_round_returns_four_when_exactly_four_are_informative() -> None:
    names = ["T1", "T2", "T3", "T4"]
    plan = plan_round(build([_askable(t) for t in names], freq_a=dict.fromkeys(names, 0.9)))
    assert len(plan.questions) == 4


def test_plan_round_allows_at_most_two_questions_per_system() -> None:
    askables = [_askable(f"N{i}", system="neuro") for i in range(1, 5)]
    askables.append(_askable("E1", system="eye"))
    freq = {"N1": 0.9, "N2": 0.85, "N3": 0.8, "N4": 0.75, "E1": 0.6}
    plan = plan_round(build(askables, freq_a=freq))
    assert q_terms(plan) == ["N1", "N2", "E1"]


def test_plan_round_never_puts_ancestor_and_descendant_in_same_batch() -> None:
    # P is an ancestor of C; both askable and equally informative (A annotated on C at 0.9).
    askables = [_askable("P"), _askable("C"), _askable("X1"), _askable("X2")]
    inp = build(
        askables,
        freq_a={"C": 0.9, "X1": 0.8, "X2": 0.7},
        extra_anc={"C": {"P"}},
    )
    terms = q_terms(plan_round(inp))
    assert not ({"P", "C"} <= set(terms))
    assert {"P", "C"} & set(terms)
    assert {"X1", "X2"} <= set(terms)


def test_plan_round_stops_early_when_next_gain_is_below_two_hundredths_of_a_bit() -> None:
    # W: every disease has p=0.3 and D0 bg=0.3, so IG = 0 and it must not be asked.
    askables = [_askable("S1"), _askable("W", bg=0.3)]
    inp = build(
        askables,
        freq_a={"S1": 0.9, "W": 0.3},
        annotations_b={"W": 0.3},
    )
    # D0 uses bg(W)=0.3 as well; S1 is the only informative question (batch < 3 is allowed).
    plan = plan_round(inp)
    assert q_terms(plan) == ["S1"]


def test_plan_round_returns_no_questions_when_nothing_is_informative() -> None:
    inp = build([_askable("W", bg=0.3)], freq_a={"W": 0.3}, annotations_b={"W": 0.3})
    plan = plan_round(inp)
    assert plan.questions == []
    assert plan.best_ig["home"] == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------- filters


def test_plan_round_skips_term_when_child_is_younger_than_min_age() -> None:
    inp = build([_askable("T1", min_age=60)], freq_a={"T1": 0.9}, age_months=36)
    assert q_terms(plan_round(inp)) == []


def test_plan_round_keeps_term_when_child_age_equals_min_age() -> None:
    inp = build([_askable("T1", min_age=60)], freq_a={"T1": 0.9}, age_months=60)
    assert q_terms(plan_round(inp)) == ["T1"]


def test_plan_round_does_not_age_skip_when_age_is_unknown() -> None:
    inp = build([_askable("T1", min_age=60)], freq_a={"T1": 0.9}, age_months=None)
    assert q_terms(plan_round(inp)) == ["T1"]


def test_plan_round_never_asks_a_term_already_asked() -> None:
    inp = build([_askable("T1"), _askable("T2")], freq_a={"T1": 0.9, "T2": 0.8}, asked={"T1"})
    assert q_terms(plan_round(inp)) == ["T2"]


def test_plan_round_branch_memory_skips_term_whose_ancestor_was_asked() -> None:
    inp = build(
        [_askable("C"), _askable("T2")],
        freq_a={"C": 0.9, "T2": 0.8},
        extra_anc={"C": {"P"}},
        asked={"P"},
    )
    assert q_terms(plan_round(inp)) == ["T2"]


def test_plan_round_branch_memory_skips_term_whose_descendant_was_asked() -> None:
    inp = build(
        [_askable("P"), _askable("T2")],
        freq_a={"P": 0.9, "T2": 0.8},
        extra_anc={"C": {"P"}},
        asked={"C"},
    )
    assert q_terms(plan_round(inp)) == ["T2"]


def test_plan_round_skips_term_that_is_present_and_its_ancestors() -> None:
    inp = build(
        [_askable("P"), _askable("C"), _askable("T2")],
        freq_a={"P": 0.9, "C": 0.9, "T2": 0.8},
        extra_anc={"C": {"P"}},
        present={"C"},
    )
    assert q_terms(plan_round(inp)) == ["T2"]


def test_plan_round_skips_term_that_is_absent_and_its_descendants() -> None:
    inp = build(
        [_askable("P"), _askable("C"), _askable("T2")],
        freq_a={"P": 0.9, "C": 0.9, "T2": 0.8},
        extra_anc={"C": {"P"}},
        absent={"P"},
    )
    assert q_terms(plan_round(inp)) == ["T2"]


def test_plan_round_still_asks_ancestor_of_an_absent_term() -> None:
    # Child absent says nothing certain about the broader parent term.
    inp = build(
        [_askable("P"), _askable("T2")],
        freq_a={"P": 0.9, "T2": 0.8},
        extra_anc={"C": {"P"}},
        absent={"C"},
    )
    assert q_terms(plan_round(inp)) == ["P", "T2"]


# ---------------------------------------------------------------- round kinds & observability


def test_home_round_returns_only_home_terms() -> None:
    askables = [_askable("H1"), _askable("E1", obs="exam"), _askable("X1", obs="test")]
    inp = build(askables, freq_a={"H1": 0.9, "E1": 0.9, "X1": 0.9}, round_kind="home")
    plan = plan_round(inp)
    assert q_terms(plan) == ["H1"]


def test_post_doctor_round_adds_exam_terms_flagged_ask_doctor() -> None:
    askables = [_askable("H1"), _askable("E1", obs="exam"), _askable("X1", obs="test")]
    inp = build(askables, freq_a={"H1": 0.9, "E1": 0.9, "X1": 0.9}, round_kind="post_doctor")
    plan = plan_round(inp)
    assert q_terms(plan) == ["E1", "H1"] or q_terms(plan) == ["H1", "E1"]
    by_term = {q.term: q for q in plan.questions}
    assert by_term["E1"].ask_doctor is True
    assert by_term["E1"].obs == "exam"
    assert by_term["H1"].ask_doctor is False


def test_test_terms_never_appear_in_questions_in_either_round_kind() -> None:
    askables = [_askable("X1", obs="test"), _askable("H1")]
    for kind in ("home", "post_doctor"):
        inp = build(askables, freq_a={"X1": 0.9, "H1": 0.9}, round_kind=kind)  # type: ignore[arg-type]
        assert "X1" not in q_terms(plan_round(inp))


def test_exam_term_with_higher_raw_gain_loses_to_home_term_after_cost_weighting() -> None:
    # Raw IG: home (F=0.8) = 0.6001232, exam (F=1.0) = 0.9894349.
    # Weighted: exam 0.5*0.9894349 = 0.4947 < home 0.6001 * 1.0, so home is ranked first.
    ig_home, _ = information_gain(
        {"A": 0.5, "B": 0.4, "D0": 0.1}, {"A": 0.8, "B": 0.0005, "D0": 0.01}
    )
    ig_exam, _ = information_gain(
        {"A": 0.5, "B": 0.4, "D0": 0.1}, {"A": 1.0, "B": 0.0005, "D0": 0.01}
    )
    assert ig_exam > ig_home
    assert 0.5 * ig_exam < ig_home
    inp = build(
        [_askable("H1"), _askable("E1", obs="exam")],
        freq_a={"H1": 0.8, "E1": 1.0},
        round_kind="post_doctor",
    )
    plan = plan_round(inp)
    assert q_terms(plan) == ["H1", "E1"]
    assert plan.questions[0].ig == pytest.approx(ig_home, rel=1e-9)
    assert plan.questions[1].ig == pytest.approx(ig_exam, rel=1e-9)  # raw, not weighted


# ---------------------------------------------------------------- suggested tests & best_ig


def test_suggested_tests_are_ig_sorted_and_capped_at_five() -> None:
    names = [f"X{i}" for i in range(1, 8)]
    freq = {f"X{i}": 0.5 + 0.05 * i for i in range(1, 8)}  # X7 highest ... X1 lowest
    inp = build([_askable(t, obs="test") for t in names], freq_a=freq)
    plan = plan_round(inp)
    assert [q.term for q in plan.suggested_tests] == ["X7", "X6", "X5", "X4", "X3"]
    assert all(q.obs == "test" for q in plan.suggested_tests)
    assert plan.questions == []


def test_suggested_tests_are_returned_in_post_doctor_round_too() -> None:
    inp = build([_askable("X1", obs="test")], freq_a={"X1": 0.9}, round_kind="post_doctor")
    assert [q.term for q in plan_round(inp).suggested_tests] == ["X1"]


def test_suggested_tests_apply_age_branch_and_implied_filters() -> None:
    askables = [
        _askable("X_age", obs="test", min_age=200),
        _askable("X_asked", obs="test"),
        _askable("X_present", obs="test"),
        _askable("X_ok", obs="test"),
    ]
    freq = {"X_age": 0.9, "X_asked": 0.9, "X_present": 0.9, "X_ok": 0.8}
    inp = build(askables, freq_a=freq, age_months=100, asked={"X_asked"}, present={"X_present"})
    assert [q.term for q in plan_round(inp).suggested_tests] == ["X_ok"]


def test_best_ig_reports_max_raw_gain_per_observability() -> None:
    askables = [
        _askable("H1"),
        _askable("H2"),
        _askable("E1", obs="exam"),
        _askable("X1", obs="test"),
    ]
    freq = {"H1": 0.6, "H2": 0.8, "E1": 1.0, "X1": 0.7}
    plan = plan_round(build(askables, freq_a=freq))
    assert plan.best_ig["home"] == pytest.approx(0.6001232380564577, rel=1e-9)
    assert plan.best_ig["exam"] == pytest.approx(0.9894349077263698, rel=1e-9)
    assert plan.best_ig["test"] == pytest.approx(0.48392880671719485, rel=1e-9)


def test_best_ig_is_zero_for_observability_with_no_eligible_terms() -> None:
    plan = plan_round(build([_askable("H1")], freq_a={"H1": 0.9}))
    assert plan.best_ig["exam"] == 0.0
    assert plan.best_ig["test"] == 0.0
    assert set(plan.best_ig) == {"home", "exam", "test"}


def test_best_ig_ignores_terms_removed_by_filters() -> None:
    askables = [_askable("H1"), _askable("H2")]
    inp = build(askables, freq_a={"H1": 0.9, "H2": 0.6}, asked={"H1"})
    plan = plan_round(inp)
    assert plan.best_ig["home"] == pytest.approx(0.3867165929767751, rel=1e-9)


def test_subnormalised_posteriors_give_the_same_plan_as_normalised() -> None:
    from app.engine.planner import Askable, PlannerInput, plan_round

    def make(scale: float) -> PlannerInput:
        return PlannerInput(
            posteriors={"A": 0.3 * scale, "B": 0.2 * scale},
            p_d0=0.5 * scale,
            annotations={"A": {"T1": 0.9}, "B": {"T2": 0.8}},
            askable={
                "T1": Askable("T1", "home", None, "S1", "q1", 0.05),
                "T2": Askable("T2", "home", None, "S2", "q2", 0.05),
            },
            ancestors={"T1": {"T1"}, "T2": {"T2"}},
            present=set(),
            absent=set(),
            asked=set(),
            age_months=60,
            round_kind="home",
        )

    a, b = plan_round(make(1.0)), plan_round(make(0.97))
    assert [(q.term, round(q.ig, 12)) for q in a.questions] == [
        (q.term, round(q.ig, 12)) for q in b.questions
    ]
