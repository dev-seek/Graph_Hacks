"""Integration: full parent journeys through the real agent graph, FalkorDB and the built kb."""

from __future__ import annotations

from typing import Any

import pytest

from app.agents.journey import run_journey
from app.agents.packs import validate_phenopacket
from app.eval.cases import load_dev_cases
from tests.conftest import requires_kb

pytestmark = [pytest.mark.integration, requires_kb]
REFERRAL_CASE = "PMID_40215970_F11_II_2"


def test_story_to_referral_on_fake(make_service: Any) -> None:
    """The Kabir script (reviewed story + letter) on the fake model reaches REFERRAL_READY."""
    from app.agents.demo import CachedEmbedder, kabir_script, load_demo

    svc = make_service("fake")
    svc.deps.resolver._embedder = CachedEmbedder(None)  # noqa: SLF001 (recorded query vectors)
    case_id = load_demo("kabir")["case_id"]
    dc = next(c for c in load_dev_cases(svc.deps.kb) if c.case.case_id == case_id)
    res = run_journey(svc, kabir_script(svc, dc))
    assert svc.deps.router.adapter is not None  # a model (fake) answered, not the fallback
    _assert_referral(res, svc, dc)


def _assert_referral(res: Any, svc: Any, dc: Any) -> None:
    screens = [s["screen"] for s in res.steps]
    assert "story" in screens and "confirm" in screens and "round" in screens
    assert res.final_phase == "specialist_step"
    repo = svc.deps.repo(res.family_id)
    pp = svc.phenopacket(res.family_id)
    validate_phenopacket(pp)
    assert pp["subject"]["sex"] == "MALE" and pp["phenotypicFeatures"]
    letter_art = repo.latest_artifact("referral_letter")
    assert letter_art is not None and "Reason for referral" in letter_art["payload"]["text"]
    view = svc.clinician(res.family_id)
    assert view.gate.state == "REFERRAL_READY" and view.candidates and view.referral_draft
    assert view.disclaimer.startswith("Decision support")
