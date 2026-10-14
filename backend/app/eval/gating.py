"""Replay recorded round snapshots through the gates (tau sweeps without re-running the graph)."""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.gates import GateInputs, State, Taus, evaluate_gates
from app.eval.runner import CaseTrace, Snapshot


@dataclass(frozen=True)
class Outcome:
    state: State
    round: int
    see_doctor: bool  # reached SEE_DOCTOR or REFERRAL_READY (a doctor visit is advised)
    referral: bool
    final: Snapshot | None  # state of the case when the journey ended


def replay(
    trace: CaseTrace,
    taus: Taus,
    *,
    emergency: bool = False,
    urgent_soon: bool = False,
) -> Outcome:
    start = 0 if urgent_soon or emergency else 1  # G0b can fire before any home round
    for rec in trace.rounds[start:]:
        base = GateInputs(
            rare_mass=rec.snap.rare_mass,
            home_rounds_done=rec.round,
            best_home_ig=rec.best_home_ig,
            best_exam_test_ig=rec.best_exam_test_ig,
            n_doctor_test_findings=0,
            top10_rare_share=rec.snap.top10_share,
            emergency=emergency,
            urgent_soon=urgent_soon,
        )
        d = evaluate_gates(base, taus)
        if d.state == "URGENT":
            return Outcome("URGENT", rec.round, False, False, rec.snap)
        if d.state == "WATCH":
            return Outcome("WATCH", rec.round, False, False, rec.snap)
        if d.state == "SEE_DOCTOR":
            doc = rec.doctor
            if doc is None:
                return Outcome("SEE_DOCTOR", rec.round, True, False, rec.snap)
            after = evaluate_gates(
                GateInputs(
                    rare_mass=doc.rare_mass,
                    home_rounds_done=rec.round,
                    best_home_ig=rec.best_home_ig,
                    best_exam_test_ig=rec.best_exam_test_ig,
                    n_doctor_test_findings=doc.n_doctor_test_findings,
                    top10_rare_share=doc.top10_share,
                    emergency=emergency,
                    urgent_soon=urgent_soon,
                ),
                taus,
            )
            if after.state == "REFERRAL_READY":
                return Outcome("REFERRAL_READY", rec.round, True, True, doc)
            return Outcome("SEE_DOCTOR", rec.round, True, False, doc)
    last = trace.rounds[-1]
    return Outcome("CONTINUE", last.round, False, False, last.snap)
