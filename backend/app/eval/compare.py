"""Held-out dev comparison Ours vs B0/B1/B2 (parallel). Disjoint from the tuning sample."""

from __future__ import annotations

import json
import sys
from multiprocessing import Pool
from typing import Any

from app.engine.reasoner import Reasoner
from app.eval.cases import DevCase, load_dev_cases
from app.eval.cli import fmt, home_terms, make_sim, ranks_at, sample
from app.eval.metrics import Rank, paired_diff_ci, summarise, top_k
from app.eval.paths import ROOT
from app.eval.runner import CaseTrace, Strategy, run_case
from app.graph.client import connect
from app.kb.info import load_kb_info

ROUNDS = 3
HELD_OUT_SEED = 7
TUNE_SEED = 20260901
TUNE_CASES = 120


class _S:
    reasoner: Reasoner | None = None
    cases: dict[str, DevCase] = {}  # noqa: RUF012
    homes: set[str] = set()  # noqa: RUF012


def _init(release: str, cases: list[DevCase], homes: set[str]) -> None:
    _S.reasoner = Reasoner(connect().select_graph(release))
    _S.cases = {c.case.case_id: c for c in cases}
    _S.homes = homes


def _task(arg: tuple[str, Strategy]) -> CaseTrace:
    cid, strategy = arg
    r = _S.reasoner
    assert r is not None  # noqa: S101
    dc = _S.cases[cid]
    sim = make_sim(dc, r)
    age = int(dc.case.age_months) if dc.case.age_months is not None else None
    return run_case(
        r,
        cid,
        sim.story(_S.homes),
        sim,
        dc.hits,
        strategy=strategy,
        n_rounds=ROUNDS,
        age_months=age,
    )


def main(n: int) -> int:
    info = load_kb_info()
    assert info is not None  # noqa: S101
    graph = connect().select_graph(info.release)
    all_cases = load_dev_cases(graph)
    tuned = {c.case.case_id for c in sample(all_cases, TUNE_CASES, TUNE_SEED)}
    pool_cases = [c for c in all_cases if c.case.case_id not in tuned]
    cases = sample(pool_cases, n, HELD_OUT_SEED)
    homes = home_terms(graph, cases)
    ids = [c.case.case_id for c in cases]
    results: dict[str, list[CaseTrace]] = {}
    with Pool(8, initializer=_init, initargs=(info.release, cases, homes)) as pool:
        for strat in ("ours", "b1", "b2"):
            results[strat] = pool.map(_task, [(i, strat) for i in ids], chunksize=4)  # type: ignore[misc]
    table: list[tuple[str, list[Rank]]] = [
        ("B0 story only", ranks_at(results["ours"], 0)),
        ("B1 random x3", ranks_at(results["b1"], ROUNDS)),
        ("B2 frequent x3", ranks_at(results["b2"], ROUNDS)),
        ("Ours x3", ranks_at(results["ours"], ROUNDS)),
    ]
    report: dict[str, Any] = {"n": len(cases), "held_out_seed": HELD_OUT_SEED, "rounds": ROUNDS}
    lines = [f"held-out dev: {len(cases)} cases (disjoint from the 120 tuning cases)"]
    lines.append(f"{'method':16} {'top1 %':>16} {'top3 %':>16} {'top10 %':>16} {'MRR':>6}")
    for name, ranks in table:
        s = summarise(ranks)
        report[name] = s
        lines.append(
            f"{name:16} {fmt(s, 'top1')} {fmt(s, 'top3')} {fmt(s, 'top10')} {s['mrr']:.3f}"
        )
    ours = table[3][1]
    for name, ranks in table[:3]:
        lo, hi = paired_diff_ci(ours, ranks, lambda r: top_k(r, 10))
        report[f"top10_gain_vs_{name}"] = [lo, hi]
        lines.append(f"Ours - {name}: top10 gain 95% CI [{100 * lo:+.1f}, {100 * hi:+.1f}] pts")
    (ROOT / ".build" / "logs" / "eval-heldout.json").write_text(json.dumps(report, indent=2))
    print("\n".join(lines))  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 400))
