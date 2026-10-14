"""Per-round latency budget on the full dev kb with real phenopacket feature sets (spec §7).

Budget: Q1+Q2 < 300 ms, scoring < 100 ms, planner < 500 ms. Needs `make kb` (skipped otherwise).
"""

from __future__ import annotations

import statistics
import time

import pytest

from app.engine.planner import plan_round
from app.engine.reasoner import AncestorCache, Reasoner
from app.engine.scoring import Finding, score_round
from app.eval.cases import load_dev_cases
from app.graph.client import connect
from app.kb.info import load_kb_info

pytestmark = pytest.mark.integration


def test_round_latency_within_budget() -> None:
    info = load_kb_info()
    if info is None:
        pytest.skip("no kb built")
    graph = connect().select_graph(info.release)
    reasoner = Reasoner(graph, AncestorCache.load(graph))
    cases = load_dev_cases(graph)[::200][:10]
    retrieve, scoring, planner = [], [], []
    for dc in cases:
        fs = [Finding(f.term_id, "present", "parent_story") for f in dc.case.present[:6]]
        t0 = time.perf_counter()
        pruned = reasoner.prune(fs)
        rows = reasoner.retrieve(pruned)
        t1 = time.perf_counter()
        res = score_round(pruned, rows, reasoner.params)
        t2 = time.perf_counter()
        plan_round(reasoner.plan_input(pruned, res, set(), 60, "home"))
        t3 = time.perf_counter()
        retrieve.append(t1 - t0)
        scoring.append(t2 - t1)
        planner.append(t3 - t2)
    p = lambda xs: statistics.quantiles(xs, n=10)[-1] * 1000 if len(xs) > 1 else xs[0] * 1000  # noqa: E731
    print(f"p90 ms: retrieve {p(retrieve):.0f} score {p(scoring):.0f} plan {p(planner):.0f}")  # noqa: T201
    assert p(retrieve) < 300 and p(scoring) < 100 and p(planner) < 500
