"""Tau sweeps replayed from recorded traces (spec §8.3). Dev + synthetic negatives only."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product

from app.engine.gates import Taus
from app.eval.gating import replay
from app.eval.negatives_run import NegativeRun, negative_rates
from app.eval.runner import CaseTrace

T0_GRID = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3)
T1_GRID = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99)
T2_GRID = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99)
MAX_FALSE_REFERRAL = 0.10
MAX_FALSE_SEE_DOCTOR = 0.30


@dataclass(frozen=True)
class TauPoint:
    taus: Taus
    sensitivity: float
    false_referral: float
    false_see_doctor: float


def sweep(positives: Sequence[CaseTrace], negatives: Sequence[NegativeRun]) -> list[TauPoint]:
    out: list[TauPoint] = []
    for t0, t1, t2 in product(T0_GRID, T1_GRID, T2_GRID):
        if not t0 < t1 <= t2:
            continue
        taus = Taus(t0, t1, t2)
        nr = negative_rates(list(negatives), taus)
        sens = (
            sum(replay(t, taus).referral for t in positives) / len(positives) if positives else 0.0
        )
        out.append(TauPoint(taus, sens, nr.false_referral, nr.false_see_doctor))
    return out


def feasible(points: Sequence[TauPoint]) -> list[TauPoint]:
    return [
        p
        for p in points
        if p.false_referral <= MAX_FALSE_REFERRAL and p.false_see_doctor <= MAX_FALSE_SEE_DOCTOR
    ]


def choose(points: Sequence[TauPoint]) -> TauPoint | None:
    """Max sensitivity among feasible points; ties -> more conservative (higher tau2, tau1)."""
    ok = feasible(points)
    if not ok:
        return None
    return max(ok, key=lambda p: (p.sensitivity, p.taus.t2, p.taus.t1, p.taus.t0))


def min_false_see_doctor(negatives: Sequence[NegativeRun]) -> float:
    """Lowest false see-doctor reachable with false referral <= 10% (feasibility of the params)."""
    best = 1.0
    for t0, t1 in product(T0_GRID, T1_GRID):
        if t0 >= t1:
            continue
        nr = negative_rates(list(negatives), Taus(t0, t1, 0.99))
        if nr.false_referral <= MAX_FALSE_REFERRAL:
            best = min(best, nr.false_see_doctor)
    return best


def sweep_summary(
    positives: Sequence[CaseTrace], negatives: Sequence[NegativeRun]
) -> dict[str, object]:
    """Report-only sensitivity sweep over the tau grid (no re-tuning on the frozen split)."""
    pts = sweep(positives, negatives)
    best = choose(pts)
    ok = feasible(pts)

    def row(p: TauPoint) -> dict[str, object]:
        return {
            "taus": [p.taus.t0, p.taus.t1, p.taus.t2],
            "sensitivity": p.sensitivity,
            "false_referral": p.false_referral,
            "false_see_doctor": p.false_see_doctor,
        }

    return {
        "points": len(pts),
        "feasible_points": len(ok),
        "best_feasible_by_preregistered_rule": row(best) if best else None,
        "sensitivity_range_feasible": [
            min(p.sensitivity for p in ok),
            max(p.sensitivity for p in ok),
        ]
        if ok
        else None,
        "by_tau2": {
            f"{t2:.2f}": max((p.sensitivity for p in ok if p.taus.t2 == t2), default=None)
            for t2 in T2_GRID
        },
    }
