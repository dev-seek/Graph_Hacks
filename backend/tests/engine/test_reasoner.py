"""Reasoner: fails closed without FalkorDB (unit); runs the registry end to end (integration)."""

from __future__ import annotations

from typing import Any

import pytest
from falkordb import FalkorDB
from redis.exceptions import ConnectionError as RedisConnectionError

from app.engine.reasoner import AncestorCache, GraphUnavailable, Reasoner
from app.engine.scoring import Finding, Params
from app.graph.client import connect
from app.kb.build import write_graph
from app.llm.adapters.embedding import FakeEmbedder
from tests.kb.test_kb_prepare import build


class DeadGraph:
    def ro_query(self, *_a: Any, **_k: Any) -> Any:
        raise RedisConnectionError("connection refused")


def test_reasoner_fails_closed_when_graph_is_down() -> None:
    with pytest.raises(GraphUnavailable):
        AncestorCache.load(DeadGraph())  # type: ignore[arg-type]
    r = Reasoner(DeadGraph(), AncestorCache({"X": {"X"}}))  # type: ignore[arg-type]
    with pytest.raises(GraphUnavailable):
        r.score([Finding("X", "present", "parent_story")])


@pytest.mark.integration
class TestOnFixtureKb:
    GRAPH = "kb_test_reasoner"

    @pytest.fixture(scope="class")
    def reasoner(self):  # noqa: ANN201
        db: FalkorDB = connect()
        write_graph(db, self.GRAPH, build(), FakeEmbedder(), {"kb_version": self.GRAPH})
        g = db.select_graph(self.GRAPH)
        yield Reasoner(g, params=Params())
        g.delete()

    def test_scores_candidates_from_the_graph(self, reasoner: Reasoner) -> None:
        pruned, res = reasoner.score([Finding("TEST:0012", "present", "doctor_exam")])
        assert {c.disease for c in res.candidates} >= {"ORPHA:900100"}
        assert 0.0 < res.rare_mass < 1.0
        assert (
            abs(sum(c.posterior for c in res.candidates) + res.p_d0 + res.unlinked_mass - 1) < 1e-9
        )
        assert [f.term for f in pruned] == ["TEST:0012"]

    def test_prune_drops_present_ancestor(self, reasoner: Reasoner) -> None:
        fs = [
            Finding("TEST:0011", "present", "parent_story"),
            Finding("TEST:0012", "present", "parent_story"),
        ]
        assert [f.term for f in reasoner.prune(fs)] == ["TEST:0012"]

    def test_plan_runs_and_respects_asked(self, reasoner: Reasoner) -> None:
        fs = [Finding("TEST:0012", "present", "doctor_exam")]
        pruned, res = reasoner.score(fs)
        plan = reasoner.plan(pruned, res, {"TEST:0021"}, 60, "home")
        assert all(q.term != "TEST:0021" for q in plan.questions)
