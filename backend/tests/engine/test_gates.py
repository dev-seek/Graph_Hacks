"""Gate tests (spec 8.3). Pure function; thresholds tested at and just below the boundary."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.engine.gates import GateDecision, GateInputs, Taus, evaluate_gates

EPS = 1e-9


def base(**kw: float | int | bool) -> GateInputs:
    """Quiet defaults: no gate fires -> CONTINUE."""
    d: dict[str, float | int | bool] = {
        "rare_mass": 0.10,
        "home_rounds_done": 1,
        "best_home_ig": 0.5,
        "best_exam_test_ig": 0.0,
        "n_doctor_test_findings": 0,
        "top10_rare_share": 0.0,
        "emergency": False,
        "urgent_soon": False,
    }
    d.update(kw)
    return GateInputs(**d)  # type: ignore[arg-type]


def test_default_taus_are_five_thirty_seventy_percent() -> None:
    t = Taus()
    assert (t.t0, t.t1, t.t2) == (0.05, 0.30, 0.70)


def test_quiet_inputs_continue() -> None:
    d = evaluate_gates(base())
    assert d.state == "CONTINUE"
    assert d.fired == []


# ------------------------------------------------------------------ G0 / G0b


def test_emergency_returns_urgent_and_fires_only_g0() -> None:
    d = evaluate_gates(base(emergency=True))
    assert d.state == "URGENT"
    assert d.fired == ["G0"]


def test_emergency_overrides_referral_and_see_doctor_conditions() -> None:
    inp = base(
        emergency=True,
        rare_mass=0.99,
        n_doctor_test_findings=5,
        top10_rare_share=0.9,
        home_rounds_done=4,
    )
    d = evaluate_gates(inp)
    assert d.state == "URGENT"
    assert d.fired == ["G0"]


def test_urgent_soon_moves_to_see_doctor_even_before_any_home_round() -> None:
    d = evaluate_gates(base(urgent_soon=True, home_rounds_done=0, rare_mass=0.0))
    assert d.state == "SEE_DOCTOR"
    assert "G0b" in d.fired


def test_urgent_soon_does_not_override_referral_ready() -> None:
    inp = base(urgent_soon=True, rare_mass=0.8, n_doctor_test_findings=2, top10_rare_share=0.7)
    assert evaluate_gates(inp).state == "REFERRAL_READY"


# ------------------------------------------------------------------ G1


def test_see_doctor_not_fired_before_any_home_round_even_with_high_rare_mass() -> None:
    d = evaluate_gates(base(home_rounds_done=0, rare_mass=0.9))
    assert d.state == "CONTINUE"


def test_see_doctor_fires_after_one_home_round_when_rare_mass_equals_t1() -> None:
    d = evaluate_gates(base(home_rounds_done=1, rare_mass=0.30))
    assert d.state == "SEE_DOCTOR"
    assert "G1" in d.fired


def test_see_doctor_does_not_fire_when_rare_mass_just_below_t1() -> None:
    d = evaluate_gates(base(home_rounds_done=1, rare_mass=0.30 - EPS))
    assert d.state == "CONTINUE"


def test_see_doctor_honours_custom_t1() -> None:
    taus = Taus(t0=0.05, t1=0.5, t2=0.9)
    assert evaluate_gates(base(rare_mass=0.40), taus).state == "CONTINUE"
    assert evaluate_gates(base(rare_mass=0.50), taus).state == "SEE_DOCTOR"


def test_see_doctor_fires_when_home_gain_just_below_005_and_exam_gain_at_01() -> None:
    d = evaluate_gates(base(best_home_ig=0.05 - EPS, best_exam_test_ig=0.1))
    assert d.state == "SEE_DOCTOR"
    assert "G1" in d.fired


def test_see_doctor_does_not_fire_when_home_gain_exactly_005() -> None:
    d = evaluate_gates(base(best_home_ig=0.05, best_exam_test_ig=0.5))
    assert d.state == "CONTINUE"


def test_see_doctor_does_not_fire_when_exam_gain_just_below_01() -> None:
    d = evaluate_gates(base(best_home_ig=0.0, best_exam_test_ig=0.1 - EPS))
    assert d.state == "CONTINUE"


def test_see_doctor_gain_condition_needs_at_least_one_home_round() -> None:
    d = evaluate_gates(base(home_rounds_done=0, best_home_ig=0.0, best_exam_test_ig=0.5))
    assert d.state == "CONTINUE"


def test_see_doctor_fires_at_four_home_rounds_but_not_at_three() -> None:
    assert evaluate_gates(base(home_rounds_done=3)).state == "CONTINUE"
    d = evaluate_gates(base(home_rounds_done=4))
    assert d.state == "SEE_DOCTOR"
    assert "G1" in d.fired


# ------------------------------------------------------------------ G2


def _ref(**kw: float | int | bool) -> GateInputs:
    return base(
        **{
            "rare_mass": 0.70,
            "n_doctor_test_findings": 2,
            "top10_rare_share": 0.6,
            **kw,
        }
    )


def test_referral_ready_when_all_conditions_exactly_at_thresholds() -> None:
    d = evaluate_gates(_ref())
    assert d.state == "REFERRAL_READY"
    assert "G2" in d.fired


def test_referral_not_ready_when_rare_mass_just_below_t2() -> None:
    d = evaluate_gates(_ref(rare_mass=0.70 - EPS))
    assert d.state == "SEE_DOCTOR"  # still above t1, so G1 holds


def test_referral_not_ready_when_top10_share_just_below_06() -> None:
    assert evaluate_gates(_ref(top10_rare_share=0.6 - EPS)).state == "SEE_DOCTOR"


def test_referral_needs_two_doctor_findings_one_is_not_enough() -> None:
    assert evaluate_gates(_ref(n_doctor_test_findings=1)).state == "SEE_DOCTOR"


def test_referral_takes_precedence_over_see_doctor() -> None:
    d = evaluate_gates(_ref(home_rounds_done=4))
    assert d.state == "REFERRAL_READY"


def test_referral_honours_custom_t2() -> None:
    taus = Taus(t0=0.05, t1=0.30, t2=0.9)
    assert evaluate_gates(_ref(rare_mass=0.85), taus).state == "SEE_DOCTOR"
    assert evaluate_gates(_ref(rare_mass=0.90), taus).state == "REFERRAL_READY"


# ------------------------------------------------------------------ G3


def _watch(**kw: float | int | bool) -> GateInputs:
    return base(**{"home_rounds_done": 2, "rare_mass": 0.05 - EPS, **kw})


def test_watch_fires_after_two_home_rounds_when_rare_mass_below_t0() -> None:
    d = evaluate_gates(_watch())
    assert d.state == "WATCH"
    assert "G3" in d.fired


def test_watch_does_not_fire_when_rare_mass_exactly_t0() -> None:
    assert evaluate_gates(_watch(rare_mass=0.05)).state == "CONTINUE"


def test_watch_does_not_fire_after_only_one_home_round() -> None:
    assert evaluate_gates(_watch(home_rounds_done=1)).state == "CONTINUE"


def test_watch_blocked_by_urgent_soon_flag() -> None:
    d = evaluate_gates(_watch(urgent_soon=True))
    assert d.state == "SEE_DOCTOR"
    assert "G3" not in d.fired


def test_watch_blocked_by_emergency_flag() -> None:
    assert evaluate_gates(_watch(emergency=True)).state == "URGENT"


def test_see_doctor_by_gain_takes_precedence_over_watch() -> None:
    inp = _watch(best_home_ig=0.0, best_exam_test_ig=0.2)
    assert evaluate_gates(inp).state == "SEE_DOCTOR"


# ------------------------------------------------------------------ audit


def test_decision_echoes_every_input_number_for_audit() -> None:
    inp = base(
        rare_mass=0.42,
        home_rounds_done=3,
        best_home_ig=0.07,
        best_exam_test_ig=0.12,
        n_doctor_test_findings=1,
        top10_rare_share=0.55,
    )
    d = evaluate_gates(inp)
    assert isinstance(d, GateDecision)
    for key in (
        "rare_mass",
        "home_rounds_done",
        "best_home_ig",
        "best_exam_test_ig",
        "n_doctor_test_findings",
        "top10_rare_share",
        "emergency",
        "urgent_soon",
    ):
        assert key in d.inputs
    assert d.inputs["rare_mass"] == pytest.approx(0.42)
    assert d.inputs["home_rounds_done"] == 3
    assert d.inputs["emergency"] is False
    assert isinstance(d.rule, str) and d.rule


def test_decision_is_pure_same_inputs_give_equal_decisions() -> None:
    inp = base(rare_mass=0.5)
    assert evaluate_gates(inp) == evaluate_gates(replace(inp))
