"""Reasoner + gatekeeper steps (spec §9): load findings, run the graph queries, score, plan, gate.

Everything numeric comes from `app.engine`; the graph supplies every row (AGENTS.md rules 3-4).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.agents.deps import AgentDeps
from app.engine.gates import GateDecision, GateInputs, evaluate_gates
from app.engine.planner import Plan, PlannerInput, plan_round
from app.engine.scoring import Finding, ScoreResult
from app.graph.client import rows
from app.graph.family import FamilyRepo, FindingRow

DOCTOR_SOURCES = ("doctor_exam", "lab_or_test")
SNAPSHOT_CANDIDATES = 10


@dataclass
class Reasoning:
    findings: list[FindingRow]
    pruned: list[Finding]
    result: ScoreResult
    plan_in: PlannerInput
    plan: Plan
    gate: GateDecision
    snapshot_at: str
    names: dict[str, str] = field(default_factory=dict[str, str])

    @property
    def top10_share(self) -> float:
        rm = self.result.rare_mass
        return sum(c.posterior for c in self.result.candidates[:10]) / rm if rm > 0 else 0.0


def engine_findings(rows_: list[FindingRow]) -> list[Finding]:
    return [
        Finding(f.term_id, f.status, f.source) for f in rows_ if f.status in ("present", "absent")
    ]  # type: ignore[arg-type]


def disease_names(deps: AgentDeps, ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {str(r["id"]): str(r["name"]) for r in rows(deps.kb, "q8_disease_names", {"ids": ids})}


def term_names(deps: AgentDeps, ids: list[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {str(r["id"]): str(r["name"]) for r in rows(deps.kb, "q2h_term_names", {"ids": ids})}


def reason(
    deps: AgentDeps,
    repo: FamilyRepo,
    *,
    persist: bool = True,
    round_kind: str = "home",
) -> Reasoning:
    """Score the family's active findings, plan the next questions and evaluate the gates."""
    info = repo.info()
    assert info is not None  # noqa: S101
    frows = repo.findings()
    pruned, res = deps.reasoner.score(engine_findings(frows))
    asked = repo.asked_terms()
    plan_in = deps.reasoner.plan_input(pruned, res, asked, info.age_months, round_kind)
    plan = plan_round(plan_in)
    flags = repo.flags()
    n_doc = sum(1 for f in frows if f.source in DOCTOR_SOURCES and f.status == "present")
    inputs = GateInputs(
        rare_mass=res.rare_mass,
        home_rounds_done=repo.round_count("home"),
        best_home_ig=plan.best_ig.get("home", 0.0),
        best_exam_test_ig=max(plan.best_ig.get("exam", 0.0), plan.best_ig.get("test", 0.0)),
        n_doctor_test_findings=n_doc,
        top10_rare_share=(
            sum(c.posterior for c in res.candidates[:10]) / res.rare_mass
            if res.rare_mass > 0
            else 0.0
        ),
        emergency=any(f["level"] == "EMERGENCY" for f in flags),
        urgent_soon=any(f["level"] == "URGENT_SOON" for f in flags),
    )
    gate = evaluate_gates(inputs, deps.taus)
    top = res.candidates[:SNAPSHOT_CANDIDATES]
    names = disease_names(deps, [c.disease for c in top])
    at = ""
    if persist:
        _, round_no = repo.get_state()
        at = repo.add_snapshot(
            round_no,
            info.kb_version,
            res.rare_mass,
            len(pruned),
            [
                {"id": c.disease, "name": names.get(c.disease, c.disease), "rank": i + 1,
                 "post": c.posterior}
                for i, c in enumerate(top)
            ],
        )  # fmt: skip
        repo.add_gate(round_no, at, gate.state, gate.inputs, gate.rule)
    return Reasoning(frows, pruned, res, plan_in, plan, gate, at, names)
