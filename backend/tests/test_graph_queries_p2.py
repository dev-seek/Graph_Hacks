"""Integration: P2 registry queries Q2a–g, Q3, Q4 on the fixture kb (make test-int)."""

from __future__ import annotations

import pytest
from falkordb import FalkorDB

from app.graph.client import connect, rows
from app.kb.build import write_graph
from app.llm.adapters.embedding import FakeEmbedder
from tests.kb.test_kb_prepare import build

pytestmark = pytest.mark.integration
GRAPH = "kb_test_p2_queries"


@pytest.fixture(scope="module")
def graph():  # noqa: ANN201
    db: FalkorDB = connect()
    write_graph(db, GRAPH, build(), FakeEmbedder(), {"kb_version": GRAPH})
    g = db.select_graph(GRAPH)
    yield g
    g.delete()


def test_q2a_exact_and_more_specific_propagate_upward(graph) -> None:  # noqa: ANN001
    # ORPHA:900100 has the more specific Focal seizure (0012); Seizure (0011) finds it.
    out = rows(graph, "q2a_exact_or_specific", {"fid": "TEST:0011"})
    by = {r["disease"]: r for r in out}
    assert "ORPHA:900100" in by and "OMIM:900001" in by
    assert all(r["finding"] == "TEST:0011" and r["F"] is not None for r in out)
    assert by["OMIM:900001"]["prior"] > 0


def test_q2a_does_not_return_diseases_with_only_a_broader_annotation(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q2a_exact_or_specific", {"fid": "TEST:0012"})
    assert {r["disease"] for r in out} == {"ORPHA:900100"}


def test_q2b_returns_only_broader_hits_within_four_hops(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q2b_broader", {"present": ["TEST:0012"]})
    assert all(r["hops"] >= 1 and r["hops"] <= 4 for r in out)
    assert all(r["via"] != "TEST:0012" for r in out)


def test_q2c_not_annotation_covers_present_sign(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q2c_not_present", {"present": ["TEST:0031"]})
    assert "OMIM:900001" in {r["disease"] for r in out}  # 0/3 ORPHA row is also NOT


def test_q2d_absent_only_for_candidates(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q2d_absent", {"fid": "TEST:0021", "candidates": ["OMIM:900001"]})
    assert {r["disease"] for r in out} == {"OMIM:900001"}
    assert out[0]["F"] == pytest.approx(0.75)


def test_q2e_not_absent_for_candidates(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q2e_not_absent", {"absent": ["TEST:0031"], "candidates": ["OMIM:900001"]})
    assert {r["disease"] for r in out} == {"OMIM:900001"}


def test_q2f_term_meta_and_q2g_prior_total(graph) -> None:  # noqa: ANN001
    meta = rows(graph, "q2f_term_meta", {"ids": ["TEST:0011"]})
    assert meta[0]["bg"] > 0 and meta[0]["system"] == "TEST:0010"
    tot = rows(graph, "q2g_prior_total", {})[0]
    assert tot["n"] >= 3 and tot["total"] > 0


def test_q3_annotations_and_askable(graph) -> None:  # noqa: ANN001
    ann = rows(graph, "q3a_annotations", {"top": ["OMIM:900001"]})
    assert {r["term"] for r in ann} >= {"TEST:0011", "TEST:0021"}
    ask = rows(graph, "q3b_askable", {"askable": ["TEST:0011"]})
    assert ask[0]["obs"] in {"home", "exam", "test"} and ask[0]["question"]


def test_q3c_ancestors(graph) -> None:  # noqa: ANN001
    out = rows(graph, "q3c_ancestors", {"ids": ["TEST:0012"]})
    assert {"TEST:0012", "TEST:0011", "TEST:0010"} <= set(out[0]["ancestors"])


def test_q4_path_up_and_down(graph) -> None:  # noqa: ANN001
    up = rows(graph, "q4_explain_path", {"finding": "TEST:0012", "disease": "OMIM:900001"})
    assert up[0]["path"][0] == "TEST:0012" and up[0]["path"][-2:] == ["TEST:0011", "OMIM:900001"]
    down = rows(graph, "q4b_explain_path_down", {"finding": "TEST:0011", "disease": "ORPHA:900100"})
    assert down[0]["path"][0] == "TEST:0011" and down[0]["path"][-1] == "ORPHA:900100"
