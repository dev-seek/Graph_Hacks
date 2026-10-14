"""Integration: write the fixture kb to FalkorDB; check indexes and Q0 / Q1 / Q5 (make test-int)."""

from __future__ import annotations

import pytest
from falkordb import FalkorDB

from app.graph.client import connect, rows
from app.kb.build import write_graph
from app.kb.resolve import TermResolver
from app.llm.adapters.embedding import FakeEmbedder
from tests.kb.test_kb_prepare import build

pytestmark = pytest.mark.integration
GRAPH = "kb_test_fixture"


@pytest.fixture(scope="module")
def db() -> FalkorDB:
    return connect()


@pytest.fixture(scope="module")
def graph(db: FalkorDB):  # noqa: ANN201
    write_graph(db, GRAPH, build(), FakeEmbedder(), {"kb_version": GRAPH})
    g = db.select_graph(GRAPH)
    yield g
    g.delete()


def test_counts_match_prepared_rows(graph) -> None:  # noqa: ANN001
    n = graph.ro_query("MATCH (t:Term) RETURN count(t)").result_set[0][0]
    assert n == build().stats["terms"]
    assert graph.ro_query("MATCH (k:KbInfo) RETURN k.kb_version").result_set == [[GRAPH]]


def test_range_fulltext_and_vector_indexes_exist(graph) -> None:  # noqa: ANN001
    types: dict[tuple[str, str], set[str]] = {}
    for label, _fields, per_field, *_ in graph.ro_query("CALL db.indexes()").result_set:
        for field, kinds in per_field.items():
            types.setdefault((label, field), set()).update(kinds)
    assert "RANGE" in types[("Term", "id")] and "RANGE" in types[("Disease", "id")]
    for f in ("name", "synonyms_text", "cx_lay_text"):
        assert "FULLTEXT" in types[("Term", f)]
    assert "VECTOR" in types[("Term", "embedding")]


def test_q0_fulltext_finds_layperson_synonym(graph) -> None:  # noqa: ANN001
    hits = rows(graph, "q0_fulltext", {"q": "clouding of the lens"})
    assert hits and hits[0]["id"] == "TEST:0021"


def test_q0_vector_returns_distance_lower_is_closer(graph) -> None:  # noqa: ANN001
    v = FakeEmbedder().embed(["Cataract; clouding of the lens"])[0]
    hits = rows(graph, "q0_vector", {"vec": v})
    assert hits[0]["id"] == "TEST:0021"
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores)


def test_resolver_merges_sources_and_handles_sentences(graph) -> None:  # noqa: ANN001
    res = TermResolver(graph, FakeEmbedder()).resolve("she keeps having a fit", k=3)
    assert res and res[0].id == "TEST:0011"


def test_q1a_drops_present_ancestors(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q1a_redundant_present", {"present": ["TEST:0012", "TEST:0011", "TEST:0021"]})
    assert {r["redundant"] for r in out} == {"TEST:0011"}


def test_q1b_drops_more_specific_absent(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q1b_redundant_absent", {"absent": ["TEST:0012", "TEST:0011", "TEST:0031"]})
    assert {r["redundant"] for r in out} == {"TEST:0012"}


def test_q5_exact_equivalents_only(graph) -> None:  # noqa: ANN001
    r = rows(graph, "q5_exact_equivalents", {"target": "OMIM:900001"})[0]
    assert r["exact_equivalents"] == ["ORPHA:900100"]
    r2 = rows(graph, "q5_exact_equivalents", {"target": "OMIM:900002"})[0]
    assert r2["exact_equivalents"] == []  # BTNT is not exact
    r3 = rows(graph, "q5_exact_equivalents", {"target": "ORPHA:900100"})[0]
    assert r3["exact_equivalents"] == ["OMIM:900001"]
