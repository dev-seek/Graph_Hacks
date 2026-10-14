"""Run the synthetic negatives (spec §14): false referral / false see-doctor rates."""

from __future__ import annotations

import zlib
from dataclasses import dataclass

from app.engine.gates import Taus
from app.engine.reasoner import Reasoner
from app.eval.gating import Outcome, replay
from app.eval.negatives import ResolvedNegative, load_negatives
from app.eval.runner import CaseTrace, Strategy, run_case
from app.eval.simulator import SimFeature, SimParent
from app.safety.engine import SafetyEngine


@dataclass
class NegativeRun:
    case: ResolvedNegative
    trace: CaseTrace
    emergency: bool
    urgent_soon: bool


def safety_flags(case: ResolvedNegative, engine: SafetyEngine) -> tuple[bool, bool]:
    texts = {c.id: c.summary + ". " + ". ".join(c.present) for c in load_negatives()}
    res = engine.screen(texts[case.id], age_months=case.age_months)
    return res.emergency, res.urgent_soon


def run_negative(
    reasoner: Reasoner,
    case: ResolvedNegative,
    engine: SafetyEngine,
    *,
    n_rounds: int = 4,
    strategy: Strategy = "ours",
) -> NegativeRun:
    present = [SimFeature(s.term) for s in case.present if s.term]
    excluded = [s.term for s in case.absent if s.term]
    anc = reasoner.cache.ancestors
    sim = SimParent(present, excluded, anc, no_rate=0.10, seed=zlib.crc32(case.id.encode()))
    story = [f.term for f in present[:3]]
    trace = run_case(
        reasoner,
        case.id,
        story,
        sim,
        [],
        strategy=strategy,
        n_rounds=n_rounds,
        age_months=case.age_months,
        doctor_each_round=True,
    )
    emergency, urgent = safety_flags(case, engine)
    return NegativeRun(case, trace, emergency, urgent)


@dataclass
class NegativeRates:
    n: int
    false_referral: float
    false_see_doctor: float
    safety_floor_see_doctor: float  # share that see a doctor from safety rules alone
    outcomes: dict[str, Outcome]


def negative_rates(runs: list[NegativeRun], taus: Taus) -> NegativeRates:
    outs = {
        r.case.id: replay(r.trace, taus, emergency=r.emergency, urgent_soon=r.urgent_soon)
        for r in runs
    }
    n = len(runs) or 1
    floor = sum(1 for r in runs if r.urgent_soon or r.emergency)
    return NegativeRates(
        len(runs),
        sum(o.referral for o in outs.values()) / n,
        sum(o.see_doctor or o.state == "URGENT" for o in outs.values()) / n,
        floor / n,
        outs,
    )
