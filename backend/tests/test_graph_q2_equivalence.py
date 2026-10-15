"""Integration: the rewritten Q2a-d return the same rows as the spec §11 (Q2) versions.

Reference queries are the spec text, with one unavoidable difference (docs/VERIFIED.md, ADR-0008):
Q2a/Q2d take one `$fid` per call (UNWIND + downward var-length returns 0 rows in 6.0.2).
The rewritten Q2b matches the IS_A path before the annotation edge, so its `length(p)` equals the
spec's `length(p) - 1`.
"""

from __future__ import annotations

from typing import Any, cast

import pytest
from falkordb import FalkorDB

from app.graph.client import connect, rows
from app.kb.build import write_graph
from app.llm.adapters.embedding import FakeEmbedder
from tests.kb.test_kb_prepare import build

pytestmark = pytest.mark.integration
GRAPH = "kb_test_q2_equiv"
FINDINGS = ["TEST:0010", "TEST:0011", "TEST:0012", "TEST:0013", "TEST:0021", "TEST:0031"]
CANDIDATES = ["OMIM:900001", "ORPHA:900100"]

SPEC_Q2A = (
    "MATCH (f:Term {id: $fid})<-[:IS_A*0..10]-(x:Term)<-[r:HAS_PHENOTYPE]-(d:Disease) "
    "WHERE ID(r) >= 0 "
    "RETURN $fid AS finding, d.id AS disease, d.prior AS prior, max(r.freq) AS F"
)
SPEC_Q2B = (
    "UNWIND $present AS fid "
    "MATCH p = (f:Term {id: fid})-[:IS_A*1..4]->(a:Term)<-[r:HAS_PHENOTYPE]-(d:Disease) "
    "WHERE a.depth >= 3 AND ID(r) >= 0 "
    "RETURN fid AS finding, d.id AS disease, d.prior AS prior, a.id AS via, "
    "r.freq AS freq, a.bg AS bg_via, length(p) - 1 AS hops"
)
SPEC_Q2C = (
    "UNWIND $present AS fid "
    "MATCH (f:Term {id: fid})-[:IS_A*0..]->(a:Term)<-[r:LACKS_PHENOTYPE]-(d:Disease) "
    "WHERE ID(r) >= 0 RETURN DISTINCT fid AS finding, d.id AS disease"
)
SPEC_Q2D = (
    "MATCH (f:Term {id: $fid})<-[:IS_A*0..10]-(x:Term)<-[r:HAS_PHENOTYPE]-(d:Disease) "
    "WHERE d.id IN $candidates AND ID(r) >= 0 "
    "RETURN $fid AS finding, d.id AS disease, max(r.freq) AS F"
)


@pytest.fixture(scope="module")
def graph():  # noqa: ANN201
    db: FalkorDB = connect()
    write_graph(db, GRAPH, build(), FakeEmbedder(), {"kb_version": GRAPH})
    g = db.select_graph(GRAPH)
    # The fixture ontology is shallow; make the broader-annotation branch (depth >= 3) reachable.
    g.query("MATCH (t:Term {id: 'TEST:0011'}) SET t.depth = 3, t.bg = 0.1")
    g.query(
        "MATCH (p:Term {id: 'TEST:0012'}) "
        "CREATE (c:Term {id: 'TEST:0013', depth: 5, bg: 0.01})-[:IS_A]->(p)"
    )
    yield g
    g.delete()


def spec_rows(graph: Any, text: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    res: Any = graph.ro_query(text, params, timeout=5000)
    cols = [str(h[1]) for h in cast(list[Any], res.header)]
    return [dict(zip(cols, row, strict=True)) for row in res.result_set]


def canon(rs: list[dict[str, Any]], keys: list[str]) -> list[tuple[Any, ...]]:
    return sorted(tuple(r[k] for k in keys) for r in rs)


def test_q2a_same_rows_as_spec(graph) -> None:  # noqa: ANN001
    keys = ["finding", "disease", "prior", "F"]
    total = 0
    for fid in FINDINGS:
        new = rows(graph, "q2a_exact_or_specific", {"fid": fid})
        ref = spec_rows(graph, SPEC_Q2A, {"fid": fid})
        assert canon(new, keys) == canon(ref, keys)
        total += len(ref)
    assert total > 0


def test_q2b_same_rows_as_spec(graph) -> None:  # noqa: ANN001
    keys = ["finding", "disease", "prior", "via", "freq", "bg_via", "hops"]
    new = rows(graph, "q2b_broader", {"present": FINDINGS})
    ref = spec_rows(graph, SPEC_Q2B, {"present": FINDINGS})
    assert canon(new, keys) == sorted(set(canon(ref, keys)))
    assert ref


def test_q2c_same_rows_as_spec(graph) -> None:  # noqa: ANN001
    keys = ["finding", "disease"]
    new = rows(graph, "q2c_not_present", {"present": FINDINGS})
    ref = spec_rows(graph, SPEC_Q2C, {"present": FINDINGS})
    assert canon(new, keys) == canon(ref, keys)
    assert ref


def test_q2d_same_rows_as_spec(graph) -> None:  # noqa: ANN001
    keys = ["finding", "disease", "F"]
    total = 0
    for fid in FINDINGS:
        p = {"fid": fid, "candidates": CANDIDATES}
        new = rows(graph, "q2d_absent", p)
        ref = spec_rows(graph, SPEC_Q2D, p)
        assert canon(new, keys) == canon(ref, keys)
        total += len(ref)
    assert total > 0
