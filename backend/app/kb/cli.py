"""`make kb`: build kb_<release> (and kb_<release>_lpo once the frozen split exists)."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml

from app.graph.client import connect
from app.kb.build import KbData, prepare, write_graph
from app.kb.info import KB_INFO_PATH, KbInfo
from app.kb.labels import TermLabel
from app.kb.parsers.hp import parse_hp_json
from app.kb.parsers.hpoa import parse_hpoa
from app.kb.parsers.orphanet import parse_prevalence, parse_product1
from app.llm.adapters.embedding import get_embedder

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
SPLITS = ROOT / "eval" / "splits"
LABELS_CACHE = DERIVED / "term_labels.v1.jsonl"


def load_label_overrides() -> dict[str, TermLabel]:
    """LLM-written labels (batch pass), when a cache exists; rules cover everything else."""
    out: dict[str, TermLabel] = {}
    if LABELS_CACHE.exists():
        for line in LABELS_CACHE.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if rec.get("label", {}).get("cx_label_source") == "llm":
                out[rec["id"]] = TermLabel.model_validate(rec["label"])
    return out


def main() -> int:
    t_start = time.monotonic()
    manifest = cast(dict[str, Any], yaml.safe_load((ROOT / "data" / "manifest.yaml").read_text()))
    src = cast(dict[str, dict[str, str]], manifest["sources"])
    include_iea = (os.environ.get("KB_INCLUDE_OMIM_IEA") or "").lower() == "true"
    ontology = parse_hp_json(RAW / src["hp_json"]["file"])
    hpoa = parse_hpoa(RAW / src["hpoa"]["file"], include_omim_iea=include_iea)
    prevalence = parse_prevalence(RAW / src["orpha_product9"]["file"])
    product1 = parse_product1(RAW / src["orpha_product1"]["file"])
    release = os.environ.get("KB_RELEASE") or "kb_" + ontology.version.replace("-", "")
    kind = os.environ.get("EMBEDDER") or "bge"
    embedder = get_embedder(kind, DERIVED / f"embeddings.{kind}.bin")
    overrides = load_label_overrides()
    db = connect()
    base_info = KbInfo(
        release=release,
        hpo_version=ontology.version,
        hpoa_version=hpoa.version,
        orpha_version=src["orpha_product9"]["version"],
        product1_version=product1.version,
        phenopacket_store_version=src["phenopackets"]["version"],
        embedding_model=embedder.model_id,
        include_omim_iea=include_iea,
        built_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    test_pmids_file = SPLITS / "test_pmids.txt"
    variants: list[tuple[str, frozenset[str]]] = [(release, frozenset())]
    if test_pmids_file.exists():
        pmids = frozenset(x.strip() for x in test_pmids_file.read_text().splitlines() if x.strip())
        variants.append((f"{release}_lpo", pmids))
    summary: dict[str, dict[str, int]] = {}
    for name, excluded in variants:
        data: KbData = prepare(
            ontology, hpoa, prevalence, product1, exclude_pmids=excluded, label_overrides=overrides
        )
        info = base_info.model_copy(
            update={
                "counts": data.stats,
                "lpo_excluded_pmids_count": len(excluded) if excluded else None,
                "lpo_dropped_rows": data.stats["annotations_lpo_dropped"] if excluded else None,
            }
        )
        graph_info: dict[str, Any] = {
            "kb_version": name,
            "hpo_version": info.hpo_version,
            "hpoa_version": info.hpoa_version,
            "orpha_version": info.orpha_version,
            "product1_version": info.product1_version,
            "built_at": info.built_at,
            "include_omim_iea": include_iea,
            "lpo_excluded_pmids_count": len(excluded),
            "embedding_model": embedder.model_id,
        }
        timings = write_graph(db, name, data, embedder, graph_info)
        print(f"{name}: {data.stats}")
        print(f"  timings(s): {timings}")
        summary[name] = data.stats
        if not excluded:
            DERIVED.mkdir(parents=True, exist_ok=True)
            KB_INFO_PATH.write_text(info.model_dump_json(indent=2), encoding="utf-8")
        else:
            (DERIVED / "kb_info_lpo.json").write_text(info.model_dump_json(indent=2))
    print(f"hpoa dropped OMIM+IEA rows: {hpoa.stats['dropped_omim_iea']} (include={include_iea})")
    print(f"total {time.monotonic() - t_start:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
