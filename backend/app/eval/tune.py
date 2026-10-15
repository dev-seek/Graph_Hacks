"""Tuning on DEV + synthetic negatives only (spec §7, §8.3; ADRs 0003-0006). Never touches test ids.

Pre-declared rules (work order P2 task 7):
- eps, lambda, w, gamma on/off, pi0, beta: maximise dev MRR after 3 rounds subject to
  false referral <= 10% on the negatives (at the default taus).
- tau1/tau2/tau0: maximise referral sensitivity on dev positives subject to false referral <= 10%
  and false see-doctor <= 30% on negatives; ties -> the more conservative (higher tau2).
Run `python -m app.eval.tune <stage>` with stage in {grid, taus}. Results go to .build/logs/.
"""

from __future__ import annotations

import json
import pickle
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, replace
from itertools import product
from multiprocessing import Pool
from typing import Any

from app.engine.gates import Taus
from app.engine.reasoner import Reasoner
from app.engine.scoring import DEFAULT_WEIGHTS, Params
from app.eval.cases import DevCase, load_dev_cases
from app.eval.cli import home_terms, make_sim, sample
from app.eval.metrics import mrr, top_k
from app.eval.negatives import load_resolved
from app.eval.negatives_run import NegativeRun, negative_rates, run_negative
from app.eval.paths import ROOT
from app.eval.runner import CaseTrace, run_case
from app.eval.taus import choose, min_false_see_doctor, sweep
from app.graph.client import connect
from app.kb.info import load_kb_info
from app.safety.engine import SafetyEngine

LOGS = ROOT / ".build" / "logs"
TUNE_CASES = 120
ROUNDS = 3
MAX_ROUNDS = 4
MAX_FALSE_REFERRAL = 0.10
MAX_FALSE_SEE_DOCTOR = 0.30


class _State:
    reasoner: Reasoner | None = None
    cases: dict[str, DevCase] = {}  # noqa: RUF012
    homes: set[str] = set()  # noqa: RUF012
    engine: SafetyEngine | None = None


def _init(release: str, cases: list[DevCase], homes: set[str]) -> None:
    graph = connect().select_graph(release)
    _State.reasoner = Reasoner(graph)
    _State.homes = homes
    _State.cases.update({c.case.case_id: c for c in cases})
    _State.engine = SafetyEngine.from_file()


def _dev_task(arg: tuple[str, dict[str, Any], int, bool]) -> CaseTrace:
    case_id, pdict, rounds, doctor = arg
    r = _State.reasoner
    assert r is not None  # noqa: S101
    r.params = _params(pdict)
    dc = _State.cases[case_id]
    sim = make_sim(dc, r)
    return run_case(
        r,
        case_id,
        sim.story(_State.homes),
        sim,
        dc.hits,
        strategy="ours",
        n_rounds=rounds,
        age_months=int(dc.case.age_months) if dc.case.age_months is not None else None,
        doctor_each_round=doctor,
    )


def _neg_task(arg: tuple[int, dict[str, Any], int]) -> NegativeRun:
    idx, pdict, rounds = arg
    r, engine = _State.reasoner, _State.engine
    assert r is not None and engine is not None  # noqa: S101
    r.params = _params(pdict)
    return run_negative(r, load_resolved()[idx], engine, n_rounds=rounds)


def _params(d: dict[str, Any]) -> Params:
    return Params(**d)


@dataclass
class Evaluation:
    params: dict[str, Any]
    mrr: float
    top10: float
    false_referral: float
    false_see_doctor: float
    min_fsd: float
    seconds: float


def evaluate(
    pool: Any, case_ids: Sequence[str], n_neg: int, params: Params, rounds: int = ROUNDS
) -> Evaluation:
    t0 = time.time()
    pdict = asdict(params)
    dev = pool.map(_dev_task, [(c, pdict, rounds, False) for c in case_ids], chunksize=2)
    negs = pool.map(_neg_task, [(i, pdict, rounds) for i in range(n_neg)], chunksize=1)
    ranks = [t.rounds[rounds].snap.rank for t in dev]
    nr = negative_rates(negs, Taus())
    return Evaluation(
        pdict,
        mrr(ranks),
        top_k(ranks, 10),
        nr.false_referral,
        nr.false_see_doctor,
        min_false_see_doctor(negs),
        time.time() - t0,
    )


def _fmt(e: Evaluation) -> str:
    p = e.params
    return (
        f"pi0={p['pi0']} beta={p['beta']} eps={p['eps']} lam={p['lam']} gamma={p['gamma_on']} "
        f"w={p['w']['parent_story']}/{p['w']['parent_answer']} MRR={e.mrr:.3f} top10={e.top10:.2f} "
        f"FR={e.false_referral:.2f} FSD={e.false_see_doctor:.2f} minFSD={e.min_fsd:.2f} "
        f"({e.seconds:.0f}s)"
    )


def _best(evals: list[Evaluation]) -> Evaluation:
    """Feasible at the default taus (FR <= 10%, FSD <= 30% on the negatives), then max dev MRR.

    The default-tau feasibility check stops pi0 drifting towards "everything is rare" just because
    the dev positives are all rare-disease cases (see ADR-0005).
    """
    ok = [
        e
        for e in evals
        if e.false_referral <= MAX_FALSE_REFERRAL and e.false_see_doctor <= MAX_FALSE_SEE_DOCTOR
    ]
    return max(ok or evals, key=lambda e: (e.mrr, e.top10))


def setup() -> tuple[str, list[DevCase], set[str]]:
    info = load_kb_info()
    assert info is not None  # noqa: S101
    graph = connect().select_graph(info.release)
    cases = sample(load_dev_cases(graph), TUNE_CASES)
    return info.release, cases, home_terms(graph, cases)


def grid() -> int:
    release, cases, homes = setup()
    ids = [c.case.case_id for c in cases]
    n_neg = len(load_resolved())
    base = Params()
    log: list[dict[str, Any]] = []  # noqa: E501
    with Pool(8, initializer=_init, initargs=(release, cases, homes)) as pool:

        def stage(name: str, variants: list[Params]) -> Params:
            evals: list[Evaluation] = []
            for v in variants:
                e = evaluate(pool, ids, n_neg, v)
                evals.append(e)
                print(f"[{name}] {_fmt(e)}", flush=True)  # noqa: T201
                log.append({"stage": name, **asdict(e)})
            best = _best(evals)
            print(f"[{name}] -> best: {_fmt(best)}", flush=True)  # noqa: T201
            return _params(best.params)

        def weights(story: float, answer: float) -> dict[str, float]:
            return {**DEFAULT_WEIGHTS, "parent_story": story, "parent_answer": answer}

        cur = stage(
            "pi0-eps",
            [
                replace(base, pi0=a, eps=b)
                for a, b in product((0.3, 0.5, 0.7, 0.85, 0.97), (0.01, 0.02, 0.05))
            ],
        )
        cur = stage(
            "lam-beta",
            [replace(cur, lam=a, beta=b) for a, b in product((0.35, 0.6, 1.0), (0.45, 0.9))],
        )
        cur = stage(
            "weights",
            [replace(cur, w=weights(s, a)) for s, a in ((0.6, 0.7), (0.8, 0.9), (1.0, 1.0))],
        )
        cur = stage("gamma", [replace(cur, gamma_on=True), replace(cur, gamma_on=False)])
        cur = stage(
            "refine",
            [
                replace(cur, pi0=cur.pi0 + d, eps=max(0.005, cur.eps * f))
                for d, f in ((0.0, 1.0), (-0.1, 1.0), (0.1, 1.0), (0.0, 0.5), (0.0, 2.0))
            ],
        )
    (LOGS / "tune-grid2.json").write_text(json.dumps({"best": asdict(cur), "log": log}, indent=2))
    print("final:", json.dumps(asdict(cur)))  # noqa: T201
    return 0


def taus() -> int:
    """Stage 2: with the tuned scoring params, sweep tau0/tau1/tau2 (ADR-0006)."""
    best = json.loads((LOGS / "tune-grid2.json").read_text())["best"]
    params = _params(best)
    release, cases, homes = setup()
    ids = [c.case.case_id for c in cases]
    n_neg = len(load_resolved())
    pdict = asdict(params)
    with Pool(8, initializer=_init, initargs=(release, cases, homes)) as pool:
        pos = pool.map(_dev_task, [(c, pdict, MAX_ROUNDS, True) for c in ids], chunksize=2)
        negs = pool.map(_neg_task, [(i, pdict, MAX_ROUNDS) for i in range(n_neg)], chunksize=1)
    (LOGS / "tune-taus-traces.pkl").write_bytes(pickle.dumps((pos, negs)))
    points = sweep(pos, negs)
    chosen = choose(points)
    floor = sum(1 for r in negs if r.urgent_soon or r.emergency) / len(negs)
    out = {
        "params": best,
        "n_dev": len(pos),
        "n_neg": len(negs),
        "safety_floor_see_doctor": floor,
        "chosen": asdict(chosen) if chosen else None,
        "default": asdict(next(p for p in points if p.taus == Taus())),
        "points": [asdict(p) for p in points],
    }
    (LOGS / "tune-taus.json").write_text(json.dumps(out, indent=2))
    print(json.dumps({k: v for k, v in out.items() if k != "points"}, indent=2))  # noqa: T201
    return 0


def negatives() -> int:
    """Re-run only the negatives at the CHOSEN taus and tuned params (no re-tuning)."""
    best = json.loads((LOGS / "tune-grid2.json").read_text())["best"]
    chosen = json.loads((LOGS / "tune-taus.json").read_text())["chosen"]["taus"]
    release, cases, homes = setup()
    n_neg = len(load_resolved())
    with Pool(8, initializer=_init, initargs=(release, cases, homes)) as pool:
        negs = pool.map(_neg_task, [(i, best, MAX_ROUNDS) for i in range(n_neg)], chunksize=1)
    rates = negative_rates(negs, Taus(**chosen))
    out = {
        "taus": chosen,
        "n": rates.n,
        "false_referral": rates.false_referral,
        "false_see_doctor": rates.false_see_doctor,
        "safety_floor_see_doctor": rates.safety_floor_see_doctor,
    }
    (LOGS / "negatives-recheck.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))  # noqa: T201
    return 0


if __name__ == "__main__":
    stage_name = sys.argv[1] if len(sys.argv) > 1 else "grid"
    stages = {"grid": grid, "taus": taus, "negatives": negatives}
    sys.exit(stages[stage_name]())
