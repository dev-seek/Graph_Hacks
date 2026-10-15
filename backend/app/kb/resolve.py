"""Term resolution (spec §10.9, Q0): parent words -> HPO term ids, by graph full-text and vector.

Full-text is RediSearch, which ANDs words by default, so parent sentences are reduced to content
tokens and OR-ed; an exact phrase query is ranked above it. The vector search (cosine *distance*,
lower = closer, docs/VERIFIED.md) catches rewordings. Results are fused by rank.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from falkordb import Graph
from pydantic import BaseModel

from app.graph.client import rows
from app.llm.port import EmbeddingPort

log = structlog.get_logger("kb.resolve")
STOPWORDS = frozenset(
    """a an and are as at be been being but by can could did do does for from get gets got had has
    have having he her hers him his how i if in into is it its just keeps kept lot lots me more my
    no not of on one or our out over she so some than that the their them then there they this to
    too up very was we were what when which who will with would you your child kid kids baby son
    daughter boy girl he's she's his her feels seems seem really quite always often""".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")
RRF_K = 60
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class ResolvedTerm(BaseModel):
    id: str
    name: str
    score: float
    via: list[str]


def content_tokens(text: str) -> list[str]:
    toks = [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]
    return toks or _TOKEN.findall(text.lower())


class TermResolver:
    def __init__(self, graph: Graph, embedder: EmbeddingPort) -> None:
        self._graph = graph
        self._embedder = embedder

    def _fulltext(self, query: str) -> list[dict[str, Any]]:
        return rows(self._graph, "q0_fulltext", {"q": query})

    def resolve(self, text: str, k: int = 3) -> list[ResolvedTerm]:
        toks = content_tokens(text)
        ranked: dict[str, ResolvedTerm] = {}
        if not toks:
            return []

        def add(source: str, hits: list[dict[str, Any]], weight: float) -> None:
            for rank, h in enumerate(hits):
                cur = ranked.setdefault(
                    h["id"], ResolvedTerm(id=h["id"], name=h["name"], score=0.0, via=[])
                )
                cur.score += weight / (RRF_K + rank + 1)
                if source not in cur.via:
                    cur.via.append(source)

        raw = _TOKEN.findall(text.lower())
        full, stripped = " ".join(raw), " ".join(toks)
        if len(raw) > 1:
            add("phrase", self._fulltext(f'"{full}"'), 5.0)
        if len(toks) > 1 and stripped != full:
            add("phrase", self._fulltext(f'"{stripped}"'), 2.0)
        add("fulltext", self._fulltext(" | ".join(toks)), 1.0)
        try:
            vec = self._embedder.embed([QUERY_PREFIX + full])[0]
        except Exception:  # noqa: BLE001 (model missing/offline: degrade to full-text only)
            log.warning("vector_search_unavailable")
        else:
            add("vector", rows(self._graph, "q0_vector", {"vec": vec}), 1.0)
        return sorted(ranked.values(), key=lambda r: (-r.score, r.id))[:k]
