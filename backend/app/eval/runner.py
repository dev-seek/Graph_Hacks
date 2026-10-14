"""Run one simulated case through rounds with a question strategy (spec §14)."""

from __future__ import annotations

import random
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from app.engine.planner import PlannerInput, Question, plan_round, propagate
from app.engine.reasoner import Reasoner
from app.engine.scoring import Finding, ScoreResult
from app.eval.simulator import SimParent

Strategy = Literal["ours", "b1", "b2"]
DEFAULT_AGE_MONTHS = 60
QUESTIONS_PER_ROUND = 4
DOCTOR_EXAM_CHECKS = 5
DOCTOR_TESTS = 3


@dataclass
class Snapshot:
    rank: int | None
    rare_mass: float
    top10_share: float
    n_doctor_test_findings: int = 0


@dataclass
class RoundRecord:
    round: int
    snap: Snapshot
    best_home_ig: float
    best_exam_test_ig: float
    n_asked: int
    score_ms: float
    plan_ms: float
    doctor: Snapshot | None = None


@dataclass
class CaseTrace:
    case_id: str
    strategy: str
    rounds: list[RoundRecord] = field(default_factory=list[RoundRecord])


def rank_of(res: ScoreResult, hits: Sequence[str]) -> int | None:
    wanted = set(hits)
    for i, c in enumerate(res.candidates, start=1):
        if c.disease in wanted:
            return i
    return None


def snapshot(res: ScoreResult, hits: Sequence[str], n_dt: int = 0) -> Snapshot:
    top10 = sum(c.posterior for c in res.candidates[:10])
    share = top10 / res.rare_mass if res.rare_mass > 0 else 0.0
    return Snapshot(rank_of(res, hits), res.rare_mass, share, n_dt)


def _related(a: str, b: str, anc: Mapping[str, set[str]]) -> bool:
    return a == b or b in anc.get(a, {a}) or a in anc.get(b, {b})


def _pick(ordered: Sequence[Question], anc: Mapping[str, set[str]], n: int) -> list[Question]:
    out: list[Question] = []
    for q in ordered:
        if len(out) >= n:
            break
        if not any(_related(q.term, o.term, anc) for o in out):
            out.append(q)
    return out


def choose_questions(
    strategy: Strategy,
    inp: PlannerInput,
    res: ScoreResult,
    rng: random.Random,
) -> tuple[list[Question], float, float]:
    """(questions, best home IG, best exam/test IG) for this round."""
    plan = plan_round(inp)
    best_home = plan.best_ig.get("home", 0.0)
    best_et = max(plan.best_ig.get("exam", 0.0), plan.best_ig.get("test", 0.0))
    home_pool = [q for q in plan.pool if q.obs == "home"]
    if strategy == "ours":
        return plan.questions, best_home, best_et
    if strategy == "b1":
        shuffled = sorted(home_pool, key=lambda q: q.term)
        rng.shuffle(shuffled)
        return _pick(shuffled, inp.ancestors, QUESTIONS_PER_ROUND), best_home, best_et
    prop = propagate(inp)
    top10 = [c.disease for c in res.candidates[:10] if c.disease in prop]

    def freq(q: Question) -> tuple[int, float, str]:
        fs = [prop[d][q.term] for d in top10 if q.term in prop[d]]
        return (-len(fs), -sum(fs), q.term)

    return (
        _pick(sorted(home_pool, key=freq), inp.ancestors, QUESTIONS_PER_ROUND),
        best_home,
        best_et,
    )


def _ask(sim: SimParent, qs: Sequence[Question], source: str) -> list[Finding]:
    out: list[Finding] = []
    for q in qs:
        ans = sim.answer(q.term)
        if ans == "yes":
            out.append(Finding(q.term, "present", source))
        elif ans == "no":
            out.append(Finding(q.term, "absent", source))
    return out


def doctor_visit(
    reasoner: Reasoner,
    findings: Sequence[Finding],
    asked: set[str],
    age: int,
    sim: SimParent,
    hits: Sequence[str],
) -> Snapshot:
    """Exam checks from the doctor pack plus up to 3 suggested tests, answered by the simulator."""
    pruned, res = reasoner.score(findings)
    inp = reasoner.plan_input(pruned, res, asked, age, "post_doctor")
    plan = plan_round(inp)
    exams = sorted((q for q in plan.pool if q.obs == "exam"), key=lambda q: (-q.ig, q.term))
    checks = _pick(exams, inp.ancestors, DOCTOR_EXAM_CHECKS)
    tests = plan.suggested_tests[:DOCTOR_TESTS]
    new = _ask(sim, checks, "doctor_exam") + _ask(sim, tests, "lab_or_test")
    n_present = sum(1 for f in new if f.status == "present")
    _, res2 = reasoner.score([*findings, *new])
    return snapshot(res2, hits, n_present)


def run_case(
    reasoner: Reasoner,
    case_id: str,
    story: Sequence[str],
    sim: SimParent,
    hits: Sequence[str],
    *,
    strategy: Strategy,
    n_rounds: int,
    age_months: int | None,
    doctor_each_round: bool = False,
    seed: int = 0,
) -> CaseTrace:
    age = int(age_months) if age_months is not None else DEFAULT_AGE_MONTHS
    rng = random.Random(f"{case_id}:{seed}")  # noqa: S311
    findings = [Finding(t, "present", "parent_story") for t in story]
    asked: set[str] = set()
    trace = CaseTrace(case_id, strategy)
    for r in range(n_rounds + 1):
        t0 = time.perf_counter()
        pruned, res = reasoner.score(findings)
        t1 = time.perf_counter()
        inp = reasoner.plan_input(pruned, res, asked, age, "home")
        qs, best_home, best_et = choose_questions(strategy, inp, res, rng)
        t2 = time.perf_counter()
        rec = RoundRecord(
            r,
            snapshot(res, hits),
            best_home,
            best_et,
            len(asked),
            (t1 - t0) * 1000,
            (t2 - t1) * 1000,
        )
        if doctor_each_round or r == n_rounds:
            rec.doctor = doctor_visit(reasoner, findings, asked, age, sim, hits)
        trace.rounds.append(rec)
        if r < n_rounds:
            asked |= {q.term for q in qs}
            findings = [*findings, *_ask(sim, qs, "parent_answer")]
    return trace
