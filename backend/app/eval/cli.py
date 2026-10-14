"""`make eval-smoke`: 30 dev cases x 3 rounds x {ours, B1, B2}; B0 = story only (round 0)."""

from __future__ import annotations

import json
import random
import sys
from collections.abc import Sequence
from typing import Any

from falkordb import Graph

from app.engine.reasoner import Reasoner
from app.eval.cases import DevCase, load_dev_cases
from app.eval.metrics import Rank, paired_diff_ci, summarise, top_k
from app.eval.paths import ROOT
from app.eval.runner import CaseTrace, Strategy, run_case
from app.eval.simulator import SimFeature, SimParent
from app.graph.client import connect, rows
from app.kb.info import load_kb_info

SMOKE_CASES = 30
SMOKE_ROUNDS = 3
LOG = ROOT / ".build" / "logs" / "eval-smoke.json"


def home_terms(graph: Graph, cases: Sequence[DevCase]) -> set[str]:
    ids = sorted({f.term_id for c in cases for f in c.case.present})
    out = rows(graph, "q3b_askable", {"askable": ids})
    return {str(r["id"]) for r in out if r["obs"] == "home"}


def make_sim(dc: DevCase, reasoner: Reasoner, *, no_rate: float = 0.10, seed: int = 0) -> SimParent:
    feats = [SimFeature(f.term_id, f.onset_months) for f in dc.case.present]
    return SimParent(
        feats,
        [f.term_id for f in dc.case.excluded],
        reasoner.cache.ancestors,
        no_rate=no_rate,
        seed=seed,
    )


def sample(cases: Sequence[DevCase], n: int, seed: int = 20260901) -> list[DevCase]:
    rng = random.Random(seed)  # noqa: S311
    ordered = sorted(cases, key=lambda c: c.case.case_id)
    return rng.sample(ordered, min(n, len(ordered)))


def run_strategy(
    reasoner: Reasoner,
    cases: Sequence[DevCase],
    homes: set[str],
    strategy: Strategy,
    n_rounds: int,
    *,
    no_rate: float = 0.10,
    doctor_each_round: bool = False,
) -> list[CaseTrace]:
    out: list[CaseTrace] = []
    for dc in cases:
        sim = make_sim(dc, reasoner, no_rate=no_rate)
        story = sim.story(homes)
        out.append(
            run_case(
                reasoner,
                dc.case.case_id,
                story,
                sim,
                dc.hits,
                strategy=strategy,
                n_rounds=n_rounds,
                age_months=int(dc.case.age_months) if dc.case.age_months is not None else None,
                doctor_each_round=doctor_each_round,
            )
        )
    return out


def ranks_at(traces: Sequence[CaseTrace], rnd: int) -> list[Rank]:
    return [t.rounds[rnd].snap.rank for t in traces]


def fmt(s: dict[str, float], key: str) -> str:
    return f"{100 * s[key]:5.1f} [{100 * s[key + '_lo']:4.1f},{100 * s[key + '_hi']:4.1f}]"


def smoke(n_cases: int = SMOKE_CASES) -> int:
    info = load_kb_info()
    if info is None:
        print("no kb built: run make kb")  # noqa: T201
        return 1
    graph = connect().select_graph(info.release)
    reasoner = Reasoner(graph)
    cases = sample(load_dev_cases(graph), n_cases)
    homes = home_terms(graph, cases)
    report: dict[str, Any] = {"kb": info.release, "cases": len(cases), "rounds": SMOKE_ROUNDS}
    print(f"eval-smoke: {len(cases)} dev cases, {SMOKE_ROUNDS} rounds, kb {info.release}")  # noqa: T201
    results: dict[str, list[CaseTrace]] = {}
    for strat in ("ours", "b1", "b2"):
        results[strat] = run_strategy(reasoner, cases, homes, strat, SMOKE_ROUNDS)  # type: ignore[arg-type]
    rows_out: list[tuple[str, list[Rank]]] = [
        ("B0 story only", ranks_at(results["ours"], 0)),
        ("B1 random x3", ranks_at(results["b1"], SMOKE_ROUNDS)),
        ("B2 frequent x3", ranks_at(results["b2"], SMOKE_ROUNDS)),
        ("Ours x3", ranks_at(results["ours"], SMOKE_ROUNDS)),
    ]
    print(f"{'method':16} {'top1 %':>16} {'top10 %':>16} {'MRR':>6}")  # noqa: T201
    for name, ranks in rows_out:
        s = summarise(ranks)
        report[name] = s
        print(f"{name:16} {fmt(s, 'top1')} {fmt(s, 'top10')} {s['mrr']:.3f}")  # noqa: T201
    ours = ranks_at(results["ours"], SMOKE_ROUNDS)
    for name, ranks in rows_out[:3]:
        lo, hi = paired_diff_ci(ours, ranks, lambda r: top_k(r, 10))
        report[f"top10_gain_vs_{name}"] = [lo, hi]
        print(f"Ours - {name}: top10 gain 95% CI [{100 * lo:+.1f}, {100 * hi:+.1f}] pts")  # noqa: T201
    lat = [r.score_ms + r.plan_ms for t in results["ours"] for r in t.rounds]
    report["round_ms_median"] = sorted(lat)[len(lat) // 2]
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(f"median round latency {report['round_ms_median']:.0f} ms (log: {LOG.relative_to(ROOT)})")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(smoke(int(sys.argv[1]) if len(sys.argv) > 1 else SMOKE_CASES))
