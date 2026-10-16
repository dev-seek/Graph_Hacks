"""Frozen-split evaluation runner (spec §14, ADR-0013).

Runs the pre-registered plan on a split (`dev` for dry runs, `test` for the frozen run) and
appends one JSON line per finished (kb, strategy, no_rate, case) to a git-ignored checkpoint file.
The checkpoint is never printed or opened by hand (AGENTS.md rule 9); only `frozen_report`
aggregates it. Resumable: finished keys are skipped. Failures are retried, then counted, never
dropped silently.
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass
from multiprocessing import Pool
from pathlib import Path
from typing import Any

from app.engine.reasoner import Reasoner
from app.eval.cases import DevCase, build_cases
from app.eval.cli import home_terms, make_sim
from app.eval.paths import ROOT, SPLITS
from app.eval.runner import CaseTrace, RoundRecord, Snapshot, Strategy, run_case
from app.graph.client import connect, rows
from app.kb.info import load_kb_info

ROUNDS = 4
RETRIES = 3
FROZEN_DIR = ROOT / ".build" / "frozen"
TEST_IDS_SHA256 = "223e60764140a0c696b991e828e742e7fe9c43293f30444494e0c3ef9791b6d5"


@dataclass(frozen=True)
class Job:
    kb: str  # "lpo" | "std"
    strategy: Strategy
    no_rate: float

    @property
    def tag(self) -> str:
        return f"{self.kb}:{self.strategy}:{self.no_rate:.2f}"


def plan() -> list[Job]:
    """Pre-registered scope (ADR-0013)."""
    jobs = [Job("lpo", s, 0.10) for s in ("ours", "b1", "b2")]
    jobs += [Job("std", s, 0.10) for s in ("ours", "b1", "b2")]
    jobs += [Job("lpo", "ours", 0.0), Job("lpo", "ours", 0.30)]
    return jobs


def split_ids(split: str) -> set[str]:
    path = SPLITS / f"{split}_ids.txt"
    if split == "test":
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if sha != TEST_IDS_SHA256:
            raise SystemExit(f"test split changed: {sha} != {TEST_IDS_SHA256}")
    return set(path.read_text().split())


def graph_names() -> dict[str, str]:
    info = load_kb_info()
    assert info is not None  # noqa: S101
    return {"std": info.release, "lpo": f"{info.release}_lpo"}


def case_list(split: str) -> list[DevCase]:
    """Case list fixed on the STANDARD kb and reused for the lpo run (ADR-0013)."""
    cache = FROZEN_DIR / f"{split}_cases.json"
    if cache.exists():
        return [DevCase.model_validate(x) for x in json.loads(cache.read_text())]
    FROZEN_DIR.mkdir(parents=True, exist_ok=True)
    graph = connect().select_graph(graph_names()["std"])
    cases = build_cases(graph, split_ids(split))
    cache.write_text(json.dumps([c.model_dump() for c in cases]) + "\n")
    return cases


def annotated_in(kb: str, cases: list[DevCase]) -> set[str]:
    """Case ids whose target (or exact equivalent) still carries annotations in `kb`."""
    graph = connect().select_graph(graph_names()[kb])
    scored = {r["disease"] for r in rows(graph, "q_scored_diseases", {})}
    return {c.case.case_id for c in cases if scored & set(c.hits)}


class _W:
    reasoners: dict[str, Reasoner] = {}  # noqa: RUF012
    cases: dict[str, DevCase] = {}  # noqa: RUF012
    homes: set[str] = set()  # noqa: RUF012
    names: dict[str, str] = {}  # noqa: RUF012


def _init(cases: list[DevCase], homes: set[str], names: dict[str, str]) -> None:
    db = connect()
    _W.reasoners = {k: Reasoner(db.select_graph(v)) for k, v in names.items()}
    _W.cases = {c.case.case_id: c for c in cases}
    _W.homes = homes
    _W.names = names


def trace_to_dict(t: CaseTrace) -> dict[str, Any]:
    return asdict(t)


def trace_from_dict(d: dict[str, Any]) -> CaseTrace:
    def snap(x: dict[str, Any] | None) -> Snapshot | None:
        return Snapshot(**x) if x else None

    recs: list[RoundRecord] = []
    for r in d["rounds"]:
        r = dict(r)
        r["snap"] = snap(r["snap"])
        r["doctor"] = snap(r.get("doctor"))
        recs.append(RoundRecord(**r))
    return CaseTrace(d["case_id"], d["strategy"], recs)


def _task(arg: tuple[Job, str]) -> dict[str, Any]:
    job, cid = arg
    dc = _W.cases[cid]
    reasoner = _W.reasoners[job.kb]
    last = ""
    for attempt in range(RETRIES):
        try:
            sim = make_sim(dc, reasoner, no_rate=job.no_rate)
            age = int(dc.case.age_months) if dc.case.age_months is not None else None
            trace = run_case(
                reasoner,
                cid,
                sim.story(_W.homes),
                sim,
                dc.hits,
                strategy=job.strategy,
                n_rounds=ROUNDS,
                age_months=age,
                doctor_each_round=job.strategy == "ours",
            )
            return {"tag": job.tag, "cid": cid, "trace": trace_to_dict(trace)}
        except Exception as e:  # noqa: BLE001 (counted and reported, never dropped silently)
            last = type(e).__name__ + ": " + str(e)[:120]
            time.sleep(1 + attempt)
    return {"tag": job.tag, "cid": cid, "error": last}


def checkpoint_path(split: str) -> Path:
    return FROZEN_DIR / f"{split}_checkpoint.jsonl"


def done_keys(path: Path) -> set[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue  # torn last line after a kill
            if "error" not in d:
                keys.add((d["tag"], d["cid"]))
    return keys


def run(split: str, limit: int | None, workers: int, tags: set[str] | None) -> int:
    cases = case_list(split)
    if limit:
        cases = sorted(cases, key=lambda c: c.case.case_id)[:limit]
    names = graph_names()
    graph = connect().select_graph(names["std"])
    homes = home_terms(graph, cases)
    path = checkpoint_path(split)
    done = done_keys(path)
    jobs = [j for j in plan() if tags is None or j.tag in tags]
    todo = [(j, c.case.case_id) for j in jobs for c in cases if (j.tag, c.case.case_id) not in done]
    print(f"frozen[{split}]: {len(cases)} cases, {len(jobs)} jobs, {len(todo)} to run")  # noqa: T201
    t0 = time.time()
    n_err = 0
    with (
        Pool(workers, initializer=_init, initargs=(cases, homes, names)) as pool,
        path.open("a") as out,
    ):
        for i, res in enumerate(pool.imap_unordered(_task, todo, chunksize=1), start=1):
            out.write(json.dumps(res) + "\n")
            out.flush()
            n_err += "error" in res
            if i % 200 == 0:
                rate = i / (time.time() - t0)
                print(  # noqa: T201
                    f"  {i}/{len(todo)} done, {n_err} errors, {rate:.2f}/s, "
                    f"eta {(len(todo) - i) / rate / 60:.0f} min"
                )
    print(f"frozen[{split}] finished in {(time.time() - t0) / 60:.1f} min, {n_err} errors")  # noqa: T201
    return 0


def main(argv: list[str]) -> int:
    split = argv[0] if argv else "dev"
    limit = int(argv[1]) if len(argv) > 1 and argv[1] != "all" else None
    workers = int(argv[2]) if len(argv) > 2 else 4
    return run(split, limit, workers, None)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
