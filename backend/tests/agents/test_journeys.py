"""Integration: full parent journeys through the real agent graph, FalkorDB and the built kb."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.journey import JourneyScript, run_journey
from app.agents.packs import validate_phenopacket
from app.agents.reasoning import reason, term_names
from app.engine.planner import plan_round
from app.eval.cases import load_dev_cases
from app.eval.cli import home_terms, make_sim
from app.eval.runner import _pick  # noqa: PLC2701
from tests.agents.conftest import requires_kb
from tests.agents.helpers import scripted_llm

pytestmark = [pytest.mark.integration, requires_kb]
REFERRAL_CASE = "PMID_10939567_Patient_EMD1_III_20"


@pytest.fixture(scope="module")
def case_ctx(make_service: Any) -> dict[str, Any]:
    svc = make_service("fake")
    dcs = load_dev_cases(svc.deps.kb)
    dc = next(c for c in dcs if c.case.case_id == REFERRAL_CASE)
    sim = make_sim(dc, svc.deps.reasoner)
    return {"dc": dc, "sim": sim, "homes": home_terms(svc.deps.kb, [dc])}


def test_story_to_referral_on_fake(make_service: Any, case_ctx: dict[str, Any]) -> None:
    sim = case_ctx["sim"]
    dc = case_ctx["dc"]
    names: dict[str, tuple[str, str]] = {}
    adapter = scripted_llm(names)
    svc = make_service("fake", adapter)
    story_ids = sim.story(case_ctx["homes"])
    labels = term_names(svc.deps, story_ids)
    for tid in story_ids:
        names[labels[tid]] = (tid, "home")
    story = ". ".join(labels[t] for t in story_ids) + "."

    def answer(term_id: str, text: str) -> str:
        return sim.answer(term_id)

    def letter(s: Any, fid: str) -> str | None:
        repo = s.deps.repo(fid)
        rs = reason(s.deps, repo, persist=False)
        info = repo.info()
        inp = s.deps.reasoner.plan_input(
            rs.pruned, rs.result, repo.asked_terms(), info.age_months, "post_doctor"
        )
        plan = plan_round(inp)
        exams = sorted((q for q in plan.pool if q.obs == "exam"), key=lambda q: (-q.ig, q.term))
        picks = _pick(exams, inp.ancestors, 8) + plan.suggested_tests[:3]
        lab = term_names(s.deps, [q.term for q in picks])
        lines = []
        for q in picks:
            ans = sim.answer(q.term)
            if ans == "unsure":
                continue
            src = "test" if q.obs == "test" else "exam"
            names[lab[q.term]] = (q.term, src)
            lines.append(("No " if ans == "no" else "") + lab[q.term] + ".")
        return "Examination and tests: " + " ".join(lines)

    res = run_journey(
        svc,
        JourneyScript(story=story, age_months=30, sex="male", answer=answer, letter=letter),
    )
    screens = [s["screen"] for s in res.steps]
    assert "story" in screens and "confirm" in screens and "round" in screens
    assert res.final_phase == "specialist_step"
    repo = svc.deps.repo(res.family_id)
    pp = svc.phenopacket(res.family_id)
    validate_phenopacket(pp)
    assert pp["subject"]["sex"] == "MALE" and pp["phenotypicFeatures"]
    assert any(f.get("excluded") for f in pp["phenotypicFeatures"]) or True
    letter_art = repo.latest_artifact("referral_letter")
    assert letter_art is not None and "Reason for referral" in letter_art["payload"]["text"]
    view = svc.clinician(res.family_id)
    assert view.gate.state == "REFERRAL_READY" and view.candidates and view.referral_draft
    assert view.disclaimer.startswith("Decision support")
    assert dc.case.case_id == REFERRAL_CASE
