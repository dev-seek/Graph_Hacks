"""Aggregate a frozen-split checkpoint into the evaluation report (spec §14).

Aggregates only: nothing here prints or stores per-case results (AGENTS.md rule 9).
`python -m app.eval.frozen_report <split>` writes `eval/reports/<date>-<split>.json` (+ .md).
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from typing import Any

from app.engine.config import tuned_taus
from app.engine.gates import Taus
from app.engine.reasoner import Reasoner
from app.engine.config import PATH as ENGINE_YAML
from app.eval.cases import DevCase
from app.eval.frozen import (
    ROUNDS,
    TEST_IDS_SHA256,
    annotated_in,
    case_list,
    checkpoint_path,
    graph_names,
    plan,
    trace_from_dict,
)
from app.eval.gating import replay
from app.eval.metrics import Rank, paired_diff_ci, summarise, top_k
from app.eval.negatives import load_resolved
from app.eval.negatives_run import NegativeRun, negative_rates, run_negative
from app.eval.paths import DERIVED, REPORTS, SPLITS
from app.eval.runner import CaseTrace
from app.eval.taus import sweep_summary
from app.graph.client import connect
from app.kb.info import load_kb_info
from app.safety.engine import SafetyEngine


def load_traces(split: str) -> tuple[dict[str, dict[str, CaseTrace]], dict[str, int]]:
    """tag -> case_id -> trace, plus unresolved error counts per tag (never dropped silently)."""
    traces: dict[str, dict[str, CaseTrace]] = defaultdict(dict)
    failed: dict[str, set[str]] = defaultdict(set)
    for line in checkpoint_path(split).read_text().splitlines():
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "error" in d:
            failed[d["tag"]].add(d["cid"])
        else:
            traces[d["tag"]][d["cid"]] = trace_from_dict(d["trace"])
    errors = {t: len(c - set(traces.get(t, {}))) for t, c in failed.items()}
    return traces, errors


def ranks(
    traces: dict[str, CaseTrace], ids: Sequence[str], rnd: int, doctor: bool = False
) -> list[Rank]:
    out: list[Rank] = []
    for cid in ids:
        t = traces.get(cid)
        if t is None:
            continue
        rec = t.rounds[rnd]
        snap = rec.doctor if doctor and rec.doctor is not None else rec.snap
        out.append(snap.rank)
    return out


def _pct(xs: Sequence[float], q: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))] if s else float("nan")


def method_table(
    traces: dict[str, dict[str, CaseTrace]], kb: str, ids: Sequence[str]
) -> dict[str, Any]:
    ours = traces.get(f"{kb}:ours:0.10", {})
    b1 = traces.get(f"{kb}:b1:0.10", {})
    b2 = traces.get(f"{kb}:b2:0.10", {})
    common = [i for i in ids if i in ours and i in b1 and i in b2]
    out: dict[str, Any] = {"n": len(common)}
    out["B0 story only"] = summarise(ranks(ours, common, 0))
    out["B1 random x4"] = summarise(ranks(b1, common, ROUNDS))
    out["B2 frequent x4"] = summarise(ranks(b2, common, ROUNDS))
    out["Ours by round"] = {str(r): summarise(ranks(ours, common, r)) for r in range(ROUNDS + 1)}
    out["Ours after doctor"] = summarise(ranks(ours, common, ROUNDS, doctor=True))
    ro = ranks(ours, common, ROUNDS)
    for name, other in (
        ("B0", ranks(ours, common, 0)),
        ("B1", ranks(b1, common, ROUNDS)),
        ("B2", ranks(b2, common, ROUNDS)),
    ):
        lo, hi = paired_diff_ci(ro, other, lambda r: top_k(r, 10))
        out[f"top10_gain_vs_{name}"] = [lo, hi]
    asked = [t.rounds[ROUNDS].n_asked for i, t in ours.items() if i in set(common)]
    out["mean_questions_asked"] = statistics.fmean(asked) if asked else float("nan")
    lat = [r.score_ms + r.plan_ms for t in ours.values() for r in t.rounds]
    out["round_ms_median"] = statistics.median(lat) if lat else float("nan")
    out["round_ms_p90"] = _pct(lat, 0.9)
    return out


def referral(traces: dict[str, CaseTrace], ids: Sequence[str], taus: Taus) -> dict[str, Any]:
    outs = [replay(traces[i], taus) for i in ids if i in traces]
    n = len(outs) or 1
    g1 = [o.round for o in outs if o.see_doctor]
    return {
        "n": len(outs),
        "referral_sensitivity": sum(o.referral for o in outs) / n,
        "see_doctor": sum(o.see_doctor for o in outs) / n,
        "watch": sum(o.state == "WATCH" for o in outs) / n,
        "median_rounds_to_see_doctor": statistics.median(g1) if g1 else None,
    }


def negatives_for(kb: str, taus: Taus) -> tuple[dict[str, Any], list[NegativeRun]]:
    graph = connect().select_graph(graph_names()[kb])
    reasoner = Reasoner(graph)
    engine = SafetyEngine.from_file()
    runs = [run_negative(reasoner, c, engine) for c in load_resolved()]
    nr = negative_rates(runs, taus)
    return (
        {
            "n": nr.n,
            "false_referral": nr.false_referral,
            "false_see_doctor": nr.false_see_doctor,
            "safety_floor_see_doctor": nr.safety_floor_see_doctor,
        },
        runs,
    )


def build(split: str) -> dict[str, Any]:
    cases: list[DevCase] = case_list(split)
    ids = [c.case.case_id for c in cases]
    info = load_kb_info()
    assert info is not None  # noqa: S101
    traces, errors = load_traces(split)
    taus = tuned_taus()
    ann = annotated_in("lpo", cases)
    ids_ann = [i for i in ids if i in ann]
    ids_split = SPLITS / f"{split}_ids.txt"
    cov = json.loads((DERIVED / "coverage_P1.json").read_text())
    rep: dict[str, Any] = {
        "split": split,
        "date": date.today().isoformat(),
        "kb": info.release,
        "test_ids_sha256_expected": TEST_IDS_SHA256,
        "split_size": len(ids_split.read_text().split()),
        "cases_evaluated": len(ids),
        "lpo_target_still_annotated": len(ids_ann),
        "coverage": {
            "standard_pct": cov["cases_resolved_pct"],
            "lpo_test_pct": cov["lpo_test_cases_resolved_pct"],
        },
        "taus": [taus.t0, taus.t1, taus.t2],
        "engine_yaml_sha256": hashlib.sha256(ENGINE_YAML.read_bytes()).hexdigest(),
        "errors": dict(errors),
        "jobs": [j.tag for j in plan()],
        "completed": {k: len(v) for k, v in traces.items()},
    }
    for kb in ("lpo", "std"):
        rep[kb] = {
            "all": method_table(traces, kb, ids),
            "annotated_only": method_table(traces, kb, ids_ann),
            "referral": referral(traces.get(f"{kb}:ours:0.10", {}), ids, taus),
        }
        rep[kb]["negatives"], runs = negatives_for(kb, taus)
        rep[kb]["tau_sweep"] = sweep_summary(
            [t for i, t in traces.get(f"{kb}:ours:0.10", {}).items()], runs
        )
    rep["no_rate_sweep"] = {}
    for nr in ("0.00", "0.10", "0.30"):
        t = traces.get(f"lpo:ours:{nr}", {})
        common = [i for i in ids if i in t]
        rep["no_rate_sweep"][nr] = {
            "round4": summarise(ranks(t, common, ROUNDS)),
            "after_doctor": summarise(ranks(t, common, ROUNDS, doctor=True)),
            "referral": referral(t, common, taus),
        }
    return rep


def main(argv: list[str]) -> int:
    split = argv[0] if argv else "dev"
    rep = build(split)
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{rep['date']}-{split}.json"
    path.write_text(json.dumps(rep, indent=2, default=float) + "\n")
    print(f"wrote {path}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
