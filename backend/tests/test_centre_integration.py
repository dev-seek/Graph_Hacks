"""Integration: the centre graph (seeded by `make centre`), Q7/Q8, what-if, API, latency budget."""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.runtime import get_centre
from app.centre.service import CentreService, NotFound
from app.engine.reasoner import Reasoner
from app.graph.client import connect, rows
from app.kb.info import load_kb_info
from app.main import app
from tests.conftest import requires_kb

pytestmark = [pytest.mark.integration, requires_kb]


def _centre_ready() -> bool:
    try:
        return "centre" in connect().list_graphs()
    except Exception:  # noqa: BLE001
        return False


needs_centre = pytest.mark.skipif(not _centre_ready(), reason="run `make centre` first")


@pytest.fixture(scope="module")
def svc() -> CentreService:
    db = connect()
    info = load_kb_info()
    assert info is not None
    cache: dict[str, Reasoner] = {}

    def reasoner_for(name: str) -> Reasoner:
        if name not in cache:
            cache[name] = Reasoner(db.select_graph(name))
        return cache[name]

    return CentreService(db, reasoner_for, None, reasoner_for(info.release).cache.ancestors)


@needs_centre
def test_seed_shape_and_labels(svc: CentreService) -> None:
    o = svc.overview()
    assert (o.cases, o.resolved) == (300, 250)
    assert 6 <= o.clinicians <= 8 and 5 <= o.protocols <= 8
    g = svc.g
    unlabeled = rows(
        g,
        "c_overview",
        {},
    )
    assert unlabeled
    bad = g.ro_query(
        "MATCH (n) WHERE (n:Case OR n:Clinician OR n:DiagnosticProtocol OR n:CaseDecision) "
        "AND NOT n.synthetic = true RETURN count(n)"
    ).result_set[0][0]
    assert bad == 0


@needs_centre
def test_open_cases_hide_the_diagnosis_and_every_case_is_managed(svc: CentreService) -> None:
    g = svc.g
    leaked = g.ro_query(
        "MATCH (c:Case) WHERE c.status <> 'resolved' AND "
        "(c.diagnosis_id IS NOT NULL OR c.diagnosis_name IS NOT NULL) RETURN count(c)"
    ).result_set[0][0]
    assert leaked == 0
    unmanaged = g.ro_query(
        "MATCH (c:Case) WHERE NOT ()-[:MANAGED]->(c) RETURN count(c)"
    ).result_set[0][0]
    assert unmanaged == 0


@needs_centre
def test_routing_returns_clinician_and_protocol_for_every_lookalike(svc: CentreService) -> None:
    open_cases = svc.cases("open", 5)
    assert open_cases
    for c in open_cases:
        r = svc.routing(c["case_id"])
        assert len(r.lookalikes) == 5
        assert all(x.clinician and x.protocol and x.turnaround_days for x in r.lookalikes)
        assert r.suggested_clinician and r.suggested_protocol


@needs_centre
def test_routing_by_hpo_ids_expands_ancestors(svc: CentreService) -> None:
    look = svc.lookalikes_for(["HP:0001250", "HP:0001263"])  # seizure, developmental delay
    assert look and all(x.shared_ic > 0 for x in look)
    assert svc.lookalikes_for(["not-an-id"]) == []


@needs_centre
def test_routing_unknown_case_is_not_found(svc: CentreService) -> None:
    with pytest.raises(NotFound):
        svc.routing("C-999")


@needs_centre
def test_algorithms_yield_rows(svc: CentreService) -> None:
    b = svc.bridges()
    assert b and b[0].score > 0 and b == sorted(b, key=lambda x: -x.score)
    assert svc.clusters("lp")
    assert all(c.size >= 2 for c in svc.clusters("wcc"))


@needs_centre
def test_notes_round_trip(svc: CentreService) -> None:
    n = svc.add_note("case", "C-001", "  reviewed   at clinic meeting  ")
    assert n.text == "reviewed at clinic meeting"
    assert any(x.id == n.id for x in svc.notes("C-001"))


@needs_centre
def test_whatif_copies_graph_and_leaves_centre_untouched(svc: CentreService) -> None:
    info = load_kb_info()
    assert info is not None
    if "kb_20250901" not in connect().list_graphs():
        pytest.skip("older kb not built (make kb-prev)")
    r = svc.whatif(info.release)
    assert r.from_version == "kb_20250901" and r.rescored == 50
    assert "centre_whatif" in connect().list_graphs()
    stale = svc.g.ro_query("MATCH (u:KbUpdate) RETURN count(u)").result_set[0][0]
    assert stale == 0  # the live centre is not modified; the copy carries the KbUpdate
    in_copy = (
        connect()
        .select_graph("centre_whatif")
        .ro_query("MATCH (u:KbUpdate)-[a:AFFECTED]->(c:Case) WHERE ID(a) >= 0 RETURN count(c)")
        .result_set[0][0]
    )
    assert in_copy == len(r.details)


@needs_centre
def test_query_latency_budget(svc: CentreService) -> None:
    """Routing p90 < 100 ms; every other centre query < 2 s (P5 gate)."""
    ids = [c["case_id"] for c in svc.cases("open", 30)]
    times: list[float] = []
    for cid in ids:
        t0 = time.perf_counter()
        svc.routing(cid)
        times.append((time.perf_counter() - t0) * 1000)
    p90 = sorted(times)[int(0.9 * len(times)) - 1]
    assert p90 < 100, f"routing p90 {p90:.0f} ms"
    others: dict[str, Callable[[], Any]] = {
        "overview": svc.overview,
        "bridges": svc.bridges,
        "clusters_lp": lambda: svc.clusters("lp"),
        "clusters_wcc": lambda: svc.clusters("wcc"),
        "protocols": svc.protocols,
        "workload": svc.workload,
    }
    for name, fn in others.items():
        t0 = time.perf_counter()
        fn()
        assert time.perf_counter() - t0 < 2.0, name
    assert statistics.median(times) < 100


@pytest.fixture
def client(svc: CentreService) -> Iterator[TestClient]:
    app.dependency_overrides[get_centre] = lambda: svc
    yield TestClient(app)
    app.dependency_overrides.clear()


@needs_centre
def test_centre_api_routes(client: TestClient) -> None:
    assert client.get("/api/centre/overview").json()["cases"] == 300
    cid = client.get("/api/centre/cases", params={"status": "open", "limit": 1}).json()[0][
        "case_id"
    ]
    r = client.get(f"/api/centre/routing/{cid}").json()
    assert len(r["lookalikes"]) == 5 and r["suggested_protocol"]
    assert "Illustrative" in r["disclaimer"]
    assert client.get("/api/centre/cases/C-999").status_code == 404
    assert client.get("/api/centre/cases/bad;id").status_code == 404
    assert client.get("/api/centre/bridges").json()
    assert client.get("/api/centre/clusters", params={"method": "nope"}).status_code == 400
    ask = client.post("/api/centre/ask", json={"question": f"who should take {cid}?"}).json()
    assert cid in ask["answer"] and "q7_centre_routing" in ask["query_ids"]
    bad = client.post("/api/centre/notes", json={"kind": "case", "target": "x'; DROP", "text": "t"})
    assert bad.status_code == 400
