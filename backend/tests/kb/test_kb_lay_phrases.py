"""Integration (real kb, `make kb` first): lay phrases resolve to the right HPO term in top 3."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from app.graph.client import connect
from app.kb.info import load_kb_info
from app.kb.resolve import TermResolver
from app.llm.adapters.embedding import get_embedder

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[3]
THRESHOLD = 0.80


def _accuracy(file: str) -> tuple[float, list[str]]:
    info = load_kb_info()
    if info is None or not (ROOT / "data/derived/embeddings.bge.bin").exists():
        pytest.skip("no real kb built (run make kb)")
    resolver = TermResolver(
        connect().select_graph(info.release),
        get_embedder("bge", ROOT / "data/derived/embeddings.bge.bin"),
    )
    doc = cast(dict[str, Any], yaml.safe_load((Path(__file__).parent / file).read_text()))
    phrases = cast(list[dict[str, str]], doc["phrases"])
    misses = [
        p["text"] for p in phrases if p["expect"] not in [r.id for r in resolver.resolve(p["text"])]
    ]
    return 1 - len(misses) / len(phrases), misses


def test_lay_phrase_top3_accuracy_gate() -> None:
    accuracy, misses = _accuracy("lay_phrases.yaml")
    print(f"lay phrases top-3: {accuracy:.0%}; misses: {misses}")
    assert accuracy >= THRESHOLD, f"top-3 {accuracy:.0%}; misses: {misses}"


def test_parent_rewordings_regression_floor() -> None:
    """Non-gated stretch set (sentences). Floor guards against regressions; value goes in docs."""
    accuracy, misses = _accuracy("lay_rewordings.yaml")
    print(f"rewordings top-3: {accuracy:.0%}; misses: {misses}")
    assert accuracy >= 0.4
