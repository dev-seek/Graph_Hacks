"""Integration: HTTP API over the real agents. Auth on every route, parent-safe payloads."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api import runtime
from app.api.runtime import get_service
from app.graph.client import rows
from app.main import app
from tests.agents.helpers import scripted_llm
from tests.conftest import requires_kb
from tests.test_api_contract import forbidden_keys

pytestmark = [pytest.mark.integration, requires_kb]
TIPTOE = {"walked on tiptoes for a few months": ("HP:0030051", "home")}


@pytest.fixture
def client(make_service: Any) -> Iterator[TestClient]:
    svc = make_service("fake", scripted_llm(TIPTOE))
    app.dependency_overrides[get_service] = lambda: svc
    runtime.FAMILY_LIMIT._hits.clear()  # noqa: SLF001
    runtime.CREATE_LIMIT._hits.clear()  # noqa: SLF001
    yield TestClient(app)
    app.dependency_overrides.clear()


def _routes(tag: str) -> list[tuple[str, str]]:
    """(method, path) of every route carrying `tag`, from the live OpenAPI document."""
    out: list[tuple[str, str]] = []
    for path, ops in app.openapi()["paths"].items():
        for method, op in ops.items():
            if tag in op.get("tags", []):
                out.append((method.upper(), path))
    return out


def _fill(path: str) -> str:
    return path.replace("{family_id}", "nope").replace("{n}", "1")


def test_every_parent_route_rejects_missing_and_wrong_token(client: TestClient) -> None:
    parent = [(m, p) for m, p in _routes("parent") if p != "/api/families"]
    assert len(parent) >= 10
    for method, path in parent:
        url = _fill(path)
        assert client.request(method, url, json={}).status_code == 401, (method, path)
        bad = {"Authorization": "Bearer wrong"}
        assert client.request(method, url, json={}, headers=bad).status_code == 401, path


def test_every_clinician_route_needs_the_code(client: TestClient) -> None:
    assert _routes("clinician")
    for _method, path in _routes("clinician"):
        url = _fill(path)
        assert client.get(url).status_code == 422 or client.get(url).status_code == 401
        assert client.get(url, headers={"X-Clinician-Code": "WRONG"}).status_code == 401


def test_other_familys_token_is_rejected(client: TestClient) -> None:
    a = client.post("/api/families").json()
    b = client.post("/api/families").json()
    h = {"Authorization": f"Bearer {b['family_token']}"}
    assert client.get(f"/api/families/{a['family_id']}/state", headers=h).status_code == 401


def test_http_journey_is_parent_safe_and_clinician_sees_candidates(client: TestClient) -> None:
    svc = app.dependency_overrides[get_service]()
    c = client.post("/api/families").json()
    fid, h = c["family_id"], {"Authorization": f"Bearer {c['family_token']}"}
    seen: list[Any] = []

    def ok(resp: Any) -> Any:
        assert resp.status_code == 200, resp.text
        seen.append(resp.json())
        return resp.json()

    ok(client.get(f"/api/families/{fid}/state", headers=h))
    ex = ok(
        client.post(
            f"/api/families/{fid}/story",
            headers=h,
            json={"text": "He walked on tiptoes for a few months.", "child_age_months": 30},
        )
    )
    ids = [i["id"] for i in ex["extraction_to_confirm"]]
    st = ok(client.post(f"/api/families/{fid}/confirm", headers=h, json={"accept": ids}))
    if st["phase"] == "questions":
        rnd = ok(client.get(f"/api/families/{fid}/round", headers=h))
        body = {"answers": [{"qid": q["qid"], "value": "no"} for q in rnd["questions"]]}
        ok(
            client.post(
                f"/api/families/{fid}/round/{rnd['round_no']}/answers", headers=h, json=body
            )
        )
    ok(client.get(f"/api/families/{fid}/timeline", headers=h))
    ok(client.get(f"/api/families/{fid}/constellation", headers=h))
    ok(client.post(f"/api/families/{fid}/advance", headers=h))

    blob = json.dumps(seen).lower()
    assert forbidden_keys(seen) == []
    signs = {str(r["name"]).lower() for r in rows(svc.deps.kb, "q_all_term_names", {})}
    names = [  # a disease named exactly like an HPO sign is a sign (ADR-0012)
        str(r["name"]).lower()
        for r in rows(svc.deps.kb, "q_all_disease_names", {})
        if len(str(r["name"])) >= 10 and str(r["name"]).lower() not in signs
    ]
    leaked = [n for n in names if n in blob]
    assert not leaked, leaked[:5]

    code = svc.deps.repo(fid).auth()[1]
    view = client.get(f"/api/clinician/{fid}", headers={"X-Clinician-Code": code})
    assert view.status_code == 200 and view.json()["disclaimer"]
    assert (
        client.get(
            f"/api/clinician/{fid}/phenopacket", headers={"X-Clinician-Code": code}
        ).status_code
        == 409
    )
    assert client.get(f"/api/debug/queries?family_id={fid}", headers=h).status_code == 403
    assert client.delete(f"/api/families/{fid}", headers=h).status_code == 204
    assert client.get(f"/api/families/{fid}/state", headers=h).status_code == 401


def test_bad_requests_are_409_not_500(client: TestClient) -> None:
    c = client.post("/api/families").json()
    fid, h = c["family_id"], {"Authorization": f"Bearer {c['family_token']}"}
    assert client.get(f"/api/families/{fid}/round", headers=h).status_code == 409
    assert client.get(f"/api/families/{fid}/pack", headers=h).status_code == 409
    r = client.post(
        f"/api/families/{fid}/round/1/answers",
        headers=h,
        json={"answers": [{"qid": "x", "value": "yes"}]},
    )
    assert r.status_code == 409


def test_rate_limit_returns_429(client: TestClient) -> None:
    c = client.post("/api/families").json()
    h = {"Authorization": f"Bearer {c['family_token']}"}
    codes = {
        client.get(f"/api/families/{c['family_id']}/state", headers=h).status_code
        for _ in range(125)
    }
    assert 429 in codes


def test_demo_family_exposes_query_log(client: TestClient) -> None:
    svc = app.dependency_overrides[get_service]()
    fid, token = svc.create_family(demo=True)
    h = {"Authorization": f"Bearer {token}"}
    client.post(
        f"/api/families/{fid}/story",
        headers=h,
        json={"text": "He walked on tiptoes for a few months.", "child_age_months": 30},
    )
    log = client.get(f"/api/debug/queries?family_id={fid}", headers=h).json()
    assert log and all({"name", "cypher", "params", "rows", "ms"} <= set(e) for e in log)
    assert all("tiptoes" not in json.dumps(e["params"]) for e in log)
