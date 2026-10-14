"""Phase-1 coverage report: how many Phenopacket Store diagnoses resolve to a scored disease node.

A diagnosis resolves if its disease node, or an exact (`E`) equivalent found by Q5, has at least one
HAS_PHENOTYPE edge ("scored"). Reported with the default OMIM+IEA filter and, from the parsed
files only, with `KB_INCLUDE_OMIM_IEA=true` for comparison.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from falkordb import Graph

from app.graph.client import connect, rows
from app.kb.info import load_kb_info
from app.kb.parsers.hpoa import parse_hpoa
from app.kb.parsers.orphanet import parse_product1
from app.kb.parsers.phenopackets import parse_phenopackets

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"


def _exact_bridge(product1_path: Path) -> dict[str, set[str]]:
    bridge: dict[str, set[str]] = {}
    for e in parse_product1(product1_path).equivalences:
        if e.relation == "E":
            bridge.setdefault(e.omim_id, set()).add(e.orpha_id)
            bridge.setdefault(e.orpha_id, set()).add(e.omim_id)
    return bridge


def main() -> int:
    info = load_kb_info()
    if info is None:
        print("no kb built: run make kb")
        return 1
    cases = parse_phenopackets(RAW / "all_phenopackets.zip")
    graph = connect().select_graph(info.release)
    targets = sorted({c.disease_id for c in cases})
    resolved, n_ann = _resolve(graph, targets)
    best = {t: max([n_ann.get(t, 0), *(n_ann.get(o, 0) for o in _eq(graph, t))]) for t in resolved}
    n_cases = len(cases)
    n_res = sum(1 for c in cases if c.disease_id in resolved)
    eligible = [c for c in cases if c.disease_id in resolved and len(c.present) >= 5]
    ge5 = sum(1 for t in resolved if best[t] >= 5)

    # comparison: the same count if OMIM IEA rows were kept (parsed files only, no graph)
    hp_iea = parse_hpoa(RAW / "phenotype.hpoa", include_omim_iea=True)
    scored_iea = {a.disease_id for a in hp_iea.annotations if not a.negated}
    bridge = _exact_bridge(RAW / "en_product1.json.tar.gz")
    res_iea = {t for t in targets if t in scored_iea or bridge.get(t, set()) & scored_iea}
    # Eligibility check only (aggregates); never feeds back into tuning (ADR-0003).
    # leave-publication-out: test-split diagnoses against the lpo graph (what evaluation will use)
    test_ids = set((ROOT / "eval" / "splits" / "test_ids.txt").read_text().split())
    test_cases = [c for c in cases if c.case_id in test_ids]
    lpo_graph = connect().select_graph(f"{info.release}_lpo")
    lpo_targets = sorted({c.disease_id for c in test_cases})
    lpo_resolved, _ = _resolve(lpo_graph, lpo_targets)
    lpo_cases = sum(1 for c in test_cases if c.disease_id in lpo_resolved)
    lpo_eligible = sum(
        1 for c in test_cases if c.disease_id in lpo_resolved and len(c.present) >= 5
    )
    out = {
        "kb": info.release,
        "include_omim_iea": info.include_omim_iea,
        "cases": n_cases,
        "distinct_diagnoses": len(targets),
        "cases_resolved": n_res,
        "cases_resolved_pct": round(100 * n_res / n_cases, 1),
        "diagnoses_resolved": len(resolved),
        "diagnoses_resolved_pct": round(100 * len(resolved) / len(targets), 1),
        "resolved_direct": sum(1 for v in resolved.values() if v == "direct"),
        "resolved_via_exact_equivalent": sum(
            1 for v in resolved.values() if v == "exact_equivalent"
        ),
        "diagnoses_with_ge5_annotations": ge5,
        "eligible_cases_resolved_and_ge5_features": len(eligible),
        "lpo_test_cases": len(test_cases),
        "lpo_test_cases_resolved_pct": round(100 * lpo_cases / len(test_cases), 1),
        "lpo_test_eligible_cases": lpo_eligible,
        "with_omim_iea_diagnoses_resolved_pct": round(100 * len(res_iea) / len(targets), 1),
    }
    (ROOT / "data" / "derived" / "coverage_P1.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
    return 0


def _resolve(graph: Graph, targets: list[str]) -> tuple[dict[str, str], dict[str, int]]:
    n_ann = {r["disease"]: int(r["n"]) for r in rows(graph, "q_scored_diseases", {})}
    resolved: dict[str, str] = {}
    for t in targets:
        if n_ann.get(t, 0) > 0:
            resolved[t] = "direct"
            continue
        eq = rows(graph, "q5_exact_equivalents", {"target": t})
        if eq and any(n_ann.get(o, 0) > 0 for o in eq[0]["exact_equivalents"]):
            resolved[t] = "exact_equivalent"
    return resolved, n_ann


def _eq(graph: object, target: str) -> list[str]:
    assert isinstance(graph, Graph)  # noqa: S101
    eq = rows(graph, "q5_exact_equivalents", {"target": target})
    return list(eq[0]["exact_equivalents"]) if eq else []


if __name__ == "__main__":
    sys.exit(main())
