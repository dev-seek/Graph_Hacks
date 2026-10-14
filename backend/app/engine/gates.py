"""Deterministic gates (spec §8.3). Each decision echoes every number it used, for audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

State = Literal["URGENT", "REFERRAL_READY", "SEE_DOCTOR", "WATCH", "CONTINUE"]
TOP10_SHARE_MIN = 0.6
HOME_IG_FLOOR = 0.05
EXAM_TEST_IG_MIN = 0.1
MAX_HOME_ROUNDS = 4


@dataclass(frozen=True)
class Taus:
    t0: float = 0.05
    t1: float = 0.30
    t2: float = 0.70


@dataclass(frozen=True)
class GateInputs:
    rare_mass: float
    home_rounds_done: int
    best_home_ig: float
    best_exam_test_ig: float
    n_doctor_test_findings: int
    top10_rare_share: float
    emergency: bool
    urgent_soon: bool


@dataclass
class GateDecision:
    state: State
    fired: list[str]
    rule: str
    inputs: dict[str, float | int | bool]


def evaluate_gates(inp: GateInputs, taus: Taus = Taus()) -> GateDecision:  # noqa: B008
    echo: dict[str, float | int | bool] = {
        "rare_mass": inp.rare_mass,
        "home_rounds_done": inp.home_rounds_done,
        "best_home_ig": inp.best_home_ig,
        "best_exam_test_ig": inp.best_exam_test_ig,
        "n_doctor_test_findings": inp.n_doctor_test_findings,
        "top10_rare_share": inp.top10_rare_share,
        "emergency": inp.emergency,
        "urgent_soon": inp.urgent_soon,
        "tau0": taus.t0,
        "tau1": taus.t1,
        "tau2": taus.t2,
    }
    if inp.emergency:
        return GateDecision("URGENT", ["G0"], "G0: emergency safety rule fired", echo)
    if (
        inp.n_doctor_test_findings >= 2
        and inp.rare_mass >= taus.t2
        and inp.top10_rare_share >= TOP10_SHARE_MIN
    ):
        return GateDecision(
            "REFERRAL_READY",
            ["G2"],
            "G2: rare_mass >= tau2, >= 2 doctor/test findings, top-10 share >= 0.6",
            echo,
        )
    fired: list[str] = []
    reasons: list[str] = []
    if inp.urgent_soon:
        fired.append("G0b")
        reasons.append("urgent-soon safety rule")
    if inp.home_rounds_done >= 1:
        g1: list[str] = []
        if inp.rare_mass >= taus.t1:
            g1.append("rare_mass >= tau1")
        if inp.best_home_ig < HOME_IG_FLOOR and inp.best_exam_test_ig >= EXAM_TEST_IG_MIN:
            g1.append("home questions exhausted, exam/test informative")
        if inp.home_rounds_done >= MAX_HOME_ROUNDS:
            g1.append("4 home rounds done")
        if g1:
            fired.append("G1")
            reasons.extend(g1)
    if fired:
        return GateDecision("SEE_DOCTOR", fired, "; ".join(reasons), echo)
    if (
        inp.home_rounds_done >= 2
        and inp.rare_mass < taus.t0
        and not inp.emergency
        and not inp.urgent_soon
    ):
        return GateDecision("WATCH", ["G3"], "G3: rare_mass < tau0 after >= 2 home rounds", echo)
    return GateDecision("CONTINUE", [], "no gate fired", echo)
