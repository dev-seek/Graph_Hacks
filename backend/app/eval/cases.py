"""Dev evaluation cases (spec §14). Loads the DEV split only: test ids are never read here."""

from __future__ import annotations

import json
from pathlib import Path

from falkordb import Graph
from pydantic import BaseModel

from app.eval.paths import DERIVED, RAW, SPLITS
from app.graph.client import rows
from app.kb.parsers.phenopackets import EvalCase, parse_phenopackets

DEV_CASES_PATH = DERIVED / "dev_cases.json"
MIN_PRESENT = 5


class DevCase(BaseModel):
    case: EvalCase
    hits: list[str]  # target id + exact equivalents that carry annotations in the kb


def dev_ids(path: Path = SPLITS / "dev_ids.txt") -> set[str]:
    return set(path.read_text().split())


def _hit_set(graph: Graph, target: str, scored: set[str]) -> list[str]:
    ids = [target] if target in scored else []
    eq = rows(graph, "q5_exact_equivalents", {"target": target})
    if eq:
        ids += [o for o in eq[0]["exact_equivalents"] if o in scored]
    return ids


def build_dev_cases(graph: Graph) -> list[DevCase]:
    """Dev cases whose diagnosis resolves to scored kb disease(s) and with >= 5 present features."""
    wanted = dev_ids()
    cases = [c for c in parse_phenopackets(RAW / "all_phenopackets.zip") if c.case_id in wanted]
    scored = {r["disease"] for r in rows(graph, "q_scored_diseases", {})}
    cache: dict[str, list[str]] = {}
    out: list[DevCase] = []
    for c in cases:
        if len(c.present) < MIN_PRESENT:
            continue
        if c.disease_id not in cache:
            cache[c.disease_id] = _hit_set(graph, c.disease_id, scored)
        if cache[c.disease_id]:
            out.append(DevCase(case=c, hits=cache[c.disease_id]))
    return out


def load_dev_cases(graph: Graph, path: Path = DEV_CASES_PATH) -> list[DevCase]:
    if path.exists():
        return [DevCase.model_validate(x) for x in json.loads(path.read_text())]
    cases = build_dev_cases(graph)
    path.write_text(json.dumps([c.model_dump() for c in cases]) + "\n")
    return cases
