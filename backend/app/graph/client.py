"""FalkorDB connection helpers; every read uses `ro_query` with a timeout (AGENTS.md rule 8)."""

from __future__ import annotations

import os
from typing import Any, cast

from falkordb import FalkorDB, Graph

DEFAULT_TIMEOUT_MS = int(os.environ.get("FALKORDB_QUERY_TIMEOUT_MS") or 3000)


def connect() -> FalkorDB:
    return FalkorDB(
        host=os.environ.get("FALKORDB_HOST") or "localhost",
        port=int(os.environ.get("FALKORDB_PORT") or 6379),
        password=os.environ.get("FALKORDB_PASSWORD") or None,
    )


def select(graph_name: str, db: FalkorDB | None = None) -> Graph:
    return (db or connect()).select_graph(graph_name)


def rows(
    graph: Graph, name: str, params: dict[str, Any], timeout_ms: int | None = None
) -> list[dict[str, Any]]:
    """Run a registry query read-only and return rows as dicts keyed by column name."""
    from app.graph.queries import load_query

    result: Any = graph.ro_query(load_query(name), params, timeout=timeout_ms or DEFAULT_TIMEOUT_MS)
    header: list[Any] = cast(list[Any], result.header)
    cols = [str(h[1]) for h in header]  # header entries are [column_type, name]
    result_set: list[list[Any]] = cast(list[list[Any]], result.result_set)
    return [dict(zip(cols, row, strict=True)) for row in result_set]
