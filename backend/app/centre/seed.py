"""`make centre`: build the `centre` graph from DEV cases only (spec §11.3, ADR-0014).

Idempotent: deletes and rebuilds the graph with a fixed seed. Everything written is synthetic and
labelled so. The hidden diagnosis of an open case is never written to the graph.
"""

from __future__ import annotations

import random
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from falkordb import FalkorDB, Graph

from app.centre import rules
from app.engine.reasoner import AncestorCache
from app.eval.cases import DevCase
from app.eval.frozen import case_list, graph_names
from app.graph.client import connect, rows, write
from app.kb.info import load_kb_info

SEED = 20260901
N_RESOLVED = 250
N_OPEN = 38
N_REFERRED = 12
MAX_PER_DIAGNOSIS = 6
OPEN_WITH_SOLVED_LOOKALIKE = 40  # of the open+referred cases, diagnosis also seen among resolved
TOP_SIMILAR = 5
CLOSE_SCORE = 0.30  # strong-similarity edges for the WCC groups (SIMILAR_TO is one component)
ROOTS = frozenset({"HP:0000001", "HP:0000118"})
CLINIC_KB = "kb_20250901"  # the clinic opened these cases while the older release was current
CLINIC_TODAY = date(2026, 9, 1)
BATCH = 1000


def select_cases(cases: list[DevCase]) -> tuple[list[DevCase], list[DevCase]]:
    """(resolved, open) from the dev cases with a fixed seed; at most 6 resolved per diagnosis."""
    rng = random.Random(SEED)  # noqa: S311 (reproducible sample)
    ordered = sorted(cases, key=lambda c: c.case.case_id)
    rng.shuffle(ordered)
    per_dx: dict[str, int] = defaultdict(int)
    resolved: list[DevCase] = []
    rest: list[DevCase] = []
    for c in ordered:
        dx = c.case.disease_id
        if len(resolved) < N_RESOLVED and per_dx[dx] < MAX_PER_DIAGNOSIS:
            per_dx[dx] += 1
            resolved.append(c)
        else:
            rest.append(c)
    solved = {c.case.disease_id for c in resolved}
    n_open = N_OPEN + N_REFERRED
    known = [c for c in rest if c.case.disease_id in solved]
    unseen = [c for c in rest if c.case.disease_id not in solved]
    opened = known[:OPEN_WITH_SOLVED_LOOKALIKE]
    opened += unseen[: n_open - len(opened)]
    opened += known[OPEN_WITH_SOLVED_LOOKALIKE:][: n_open - len(opened)]
    return resolved, opened[:n_open]


def ic_overlap(a: set[str], b: set[str], ic: dict[str, float]) -> float:
    """IC-weighted Jaccard of two ancestor-closed term sets."""
    union = sum(ic[t] for t in a | b)
    return sum(ic[t] for t in a & b) / union if union > 0 else 0.0


def _batches(items: list[dict[str, Any]], n: int = BATCH) -> list[list[dict[str, Any]]]:
    return [items[i : i + n] for i in range(0, len(items), n)]


def _put(g: Graph, query: str, items: list[dict[str, Any]]) -> None:
    for chunk in _batches(items):
        write(g, query, {"rows": chunk})


def build(db: FalkorDB | None = None) -> dict[str, int]:
    t0 = time.monotonic()
    db = db or connect()
    info = load_kb_info()
    assert info is not None  # noqa: S101
    kb = db.select_graph(graph_names()["std"])
    resolved, opened = select_cases(case_list("dev"))
    anc = AncestorCache.load(kb).ancestors
    rng = random.Random(SEED + 1)  # noqa: S311

    # ---- terms: signs of every case plus ancestors (minus the two roots)
    case_terms: dict[str, list[str]] = {}
    closure: dict[str, set[str]] = {}
    ordered_cases = [(c, "resolved") for c in resolved] + [(c, "open") for c in opened]
    ids: dict[str, str] = {}
    for i, (c, _) in enumerate(ordered_cases, start=1):
        cid = f"C-{i:03d}"
        ids[c.case.case_id] = cid
        terms = [f.term_id for f in c.case.present if f.term_id in anc]
        case_terms[cid] = terms
        closure[cid] = {a for t in terms for a in anc[t]} - ROOTS
    used = sorted({t for s in closure.values() for t in s})
    info_rows = rows(kb, "c_kb_terms", {"ids": used})
    meta = {str(r["id"]): r for r in info_rows}
    ic = {t: float(meta[t]["ic"] or 0.0) for t in used}
    dx_ids = sorted({c.case.disease_id for c in resolved})
    dx_names = {str(r["id"]): str(r["name"]) for r in rows(kb, "q8_disease_names", {"ids": dx_ids})}
    # a diagnosis may be an OMIM id whose name lives on an exact equivalent: fall back to the id
    dx_names = {d: dx_names.get(d, d) for d in dx_ids}

    # ---- fresh graph
    try:
        db.select_graph("centre").delete()
    except Exception:  # noqa: BLE001, S110 (first run: nothing to delete)
        pass
    g = db.select_graph("centre")
    for q in ("c_idx_case", "c_idx_term", "c_idx_clinician", "c_idx_protocol", "c_idx_decision"):
        write(g, q, {})
    _put(
        g,
        "c_add_terms",
        [
            {"id": t, "name": meta[t]["name"], "ic": ic[t], "system": meta[t]["system"]}
            for t in used
        ],
    )
    edges = rows(kb, "c_kb_is_a", {"ids": used})
    _put(g, "c_add_is_a", [{"s": r["s"], "o": r["o"]} for r in edges])

    # ---- rules: clinician from signs, protocol from diagnosis (resolved only)
    cases_out: list[dict[str, Any]] = []
    presented: list[dict[str, Any]] = []
    has_anc: list[dict[str, Any]] = []
    managed: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    n_ref = 0
    for c, kind in ordered_cases:
        cid = ids[c.case.case_id]
        clin = rules.pick_clinician(meta[a]["system"] for a in closure[cid] if a in meta)
        row: dict[str, Any] = {
            "case_id": cid,
            "age_band": rules.age_band(c.case.age_months),
            "kb_version": CLINIC_KB,
            "synthetic": True,
        }
        if kind == "resolved":
            row |= {
                "status": "resolved",
                "diagnosis_id": c.case.disease_id,
                "diagnosis_name": dx_names[c.case.disease_id],
            }
            proto = rules.pick_protocol(dx_names[c.case.disease_id], clin)
            days = rules.turnaround_days(proto, rng)
            decided = CLINIC_TODAY - timedelta(days=rng.randint(20, 3 * 365))
            started = decided - timedelta(days=days + rng.randint(7, 60))
            decisions.append(
                {
                    "id": f"D-{cid}",
                    "c": cid,
                    "p": proto.id,
                    "k": clin,
                    "outcome": "diagnosis confirmed",
                    "decided_at": decided.isoformat(),
                    "days": days,
                }
            )
            managed.append(
                {"k": clin, "c": cid, "from": started.isoformat(), "to": decided.isoformat()}
            )
        else:  # diagnosis hidden: not stored at all
            status = "referred" if n_ref < N_REFERRED else "open"
            n_ref += status == "referred"
            row["status"] = status
            started = CLINIC_TODAY - timedelta(days=rng.randint(5, 240))
            managed.append({"k": clin, "c": cid, "from": started.isoformat(), "to": None})
        cases_out.append(row)
        presented += [{"c": cid, "t": t, "source": "clinic_record"} for t in case_terms[cid]]
        has_anc += [{"c": cid, "t": t} for t in sorted(closure[cid])]
    _put(g, "c_add_cases", cases_out)
    _put(g, "c_link_presented", presented)
    _put(g, "c_link_anc", has_anc)
    _put(
        g,
        "c_add_clinicians",
        [
            {"id": k.id, "pseudonym": k.pseudonym, "specialty": k.specialty}
            for k in rules.CLINICIANS
        ],
    )
    _put(
        g,
        "c_add_protocols",
        [{"id": p.id, "name": p.name, "tests": list(p.tests)} for p in rules.PROTOCOLS],
    )
    _put(g, "c_link_managed", managed)
    _put(g, "c_add_decisions", decisions)

    # ---- SIMILAR_TO: IC-weighted overlap in Python, top 5 per case, written back
    sims: list[dict[str, Any]] = []
    keys = sorted(closure)
    for a in keys:
        scored = sorted(
            ((ic_overlap(closure[a], closure[b], ic), b) for b in keys if b != a),
            key=lambda x: (-x[0], x[1]),
        )
        sims += [{"a": a, "b": b, "score": round(s, 4)} for s, b in scored[:TOP_SIMILAR] if s > 0]
    _put(g, "c_link_similar", sims)
    close = [x for x in sims if x["score"] >= CLOSE_SCORE]
    _put(g, "c_link_close", close)
    stats = {
        "cases": len(cases_out),
        "resolved": len(resolved),
        "open": len(opened),
        "terms": len(used),
        "has_anc": len(has_anc),
        "similar_to": len(sims),
        "close_to": len(close),
        "seconds": round(time.monotonic() - t0),
    }
    return stats


def main() -> int:
    print(f"centre: {build()}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
