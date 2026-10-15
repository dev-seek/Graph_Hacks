"""Recorded demo journeys: present, parent-safe, expected endings, served without FalkorDB."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.agents.demo import JOURNEYS, fingerprint, load_demo
from app.main import app
from tests.test_api_contract import forbidden_keys

INSPECTOR_KEYS = {"queries", "gate", "clinician", "phenopacket"}


@pytest.mark.parametrize("jid", sorted(JOURNEYS))
def test_recording_ends_as_expected_and_parent_steps_are_clean(jid: str) -> None:
    doc = load_demo(jid)
    assert doc["final_phase"] == JOURNEYS[jid]["expected"] == doc["expected_phase"]
    for step in doc["steps"]:
        parent_view: dict[str, Any] = {
            k: v for k, v in step["payload"].items() if k not in INSPECTOR_KEYS
        }
        assert forbidden_keys(parent_view) == [], step["screen"]
        assert isinstance(step["payload"].get("queries"), list)
    assert fingerprint(doc)


def test_kabir_shows_inspector_data_and_clinician_view() -> None:
    doc = load_demo("kabir")
    assert any(s["payload"]["queries"] for s in doc["steps"])
    last = doc["steps"][-1]["payload"]
    assert last["clinician"]["disclaimer"] and last["clinician"]["candidates"]
    assert last["phenopacket"]["metaData"]["phenopacketSchemaVersion"] == "2.0"
    gates = [s["payload"]["gate"]["state"] for s in doc["steps"] if "gate" in s["payload"]]
    assert gates[-1] == "REFERRAL_READY"


def test_maya_stops_at_the_urgent_screen() -> None:
    assert [s["screen"] for s in load_demo("maya")["steps"]] == ["story", "urgent"]


def test_demo_routes_serve_recordings_without_a_graph() -> None:
    c = TestClient(app)
    ids = [j["id"] for j in c.get("/api/demo/journeys").json()]
    assert ids == ["kabir", "arjun", "maya"]
    steps = c.get("/api/demo/kabir/steps").json()
    assert steps[0]["screen"] == "story" and steps[-1]["screen"] == "referral_ready"
    assert c.get("/api/demo/nobody/steps").status_code == 404
