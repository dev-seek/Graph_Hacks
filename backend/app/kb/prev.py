"""`make kb-prev`: build the previous-release knowledge base (spec §9 watcher, §11.3 what-if).

Same Orphanet files as the current kb; only HPO and HPOA differ (v2025-09-01 vs the current
release). This is real data from two real releases about a year apart, not invented knowledge.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import UTC, datetime
from typing import Any, cast

import yaml

from app.graph.client import connect
from app.kb.build import prepare, write_graph
from app.kb.cli import DERIVED, RAW, ROOT, load_label_overrides
from app.kb.info import KbInfo
from app.kb.parsers.hp import parse_hp_json
from app.kb.parsers.hpoa import parse_hpoa
from app.kb.parsers.orphanet import parse_prevalence, parse_product1
from app.llm.adapters.embedding import get_embedder

PREV_INFO = DERIVED / "kb_info_prev.json"


def main() -> int:
    t0 = time.monotonic()
    manifest = cast(dict[str, Any], yaml.safe_load((ROOT / "data" / "manifest.yaml").read_text()))
    src = cast(dict[str, dict[str, str]], manifest["sources"])
    include_iea = (os.environ.get("KB_INCLUDE_OMIM_IEA") or "").lower() == "true"
    ontology = parse_hp_json(RAW / src["hp_json_prev"]["file"])
    hpoa = parse_hpoa(RAW / src["hpoa_prev"]["file"], include_omim_iea=include_iea)
    prevalence = parse_prevalence(RAW / src["orpha_product9"]["file"])
    product1 = parse_product1(RAW / src["orpha_product1"]["file"])
    name = "kb_" + ontology.version.replace("-", "")
    kind = os.environ.get("EMBEDDER") or "bge"
    embedder = get_embedder(kind, DERIVED / f"embeddings.{kind}.bin")
    data = prepare(
        ontology,
        hpoa,
        prevalence,
        product1,
        exclude_pmids=frozenset(),
        label_overrides=load_label_overrides(),
    )
    info = KbInfo(
        release=name,
        hpo_version=ontology.version,
        hpoa_version=hpoa.version,
        orpha_version=src["orpha_product9"]["version"],
        product1_version=product1.version,
        embedding_model=embedder.model_id,
        include_omim_iea=include_iea,
        built_at=datetime.now(UTC).isoformat(timespec="seconds"),
        counts=data.stats,
    )
    graph_info: dict[str, Any] = {
        "kb_version": name,
        "hpo_version": info.hpo_version,
        "hpoa_version": info.hpoa_version,
        "orpha_version": info.orpha_version,
        "product1_version": info.product1_version,
        "built_at": info.built_at,
        "include_omim_iea": include_iea,
        "lpo_excluded_pmids_count": 0,
        "embedding_model": embedder.model_id,
    }
    timings = write_graph(connect(), name, data, embedder, graph_info)
    PREV_INFO.write_text(info.model_dump_json(indent=2), encoding="utf-8")
    print(f"{name}: {data.stats}")  # noqa: T201
    print(f"  timings(s): {timings}")  # noqa: T201
    print(f"total {time.monotonic() - t0:.1f}s")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
