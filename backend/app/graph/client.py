"""FalkorDB connection helpers; every read uses `ro_query` with a timeout (AGENTS.md rule 8).

Writes go through `write()` (registry query + timeout). Both record into the live-inspector log
when one is active (spec §12 `/debug/queries`): name, Cypher, params without free text, rows, ms.
"""

from __future__ import annotations

import os
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, cast

from falkordb import FalkorDB, Graph

DEFAULT_TIMEOUT_MS = int(os.environ.get("FALKORDB_QUERY_TIMEOUT_MS") or 3000)
WRITE_TIMEOUT_MS = 10_000
REDACTED_KEYS = frozenset({"q", "text", "quote", "vec", "label"})  # free text / big vectors
MAX_LOG_ENTRIES = 500


@dataclass
class QueryLogEntry:
    name: str
    cypher: str
    params: dict[str, Any]
    rows: int
    ms: float


@dataclass
class QueryLog:
    entries: list[QueryLogEntry] = field(default_factory=list[QueryLogEntry])

    def add(self, entry: QueryLogEntry) -> None:
        self.entries.append(entry)
        del self.entries[:-MAX_LOG_ENTRIES]


_active_log: ContextVar[QueryLog | None] = ContextVar("query_log", default=None)


def set_query_log(log: QueryLog | None) -> None:
    _active_log.set(log)


def _safe_params(params: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in params.items():
        if k in REDACTED_KEYS:
            out[k] = "<redacted>"
        elif isinstance(v, list) and len(cast(list[Any], v)) > 50:
            out[k] = f"<list of {len(cast(list[Any], v))}>"
        else:
            out[k] = v
    return out


def _record(name: str, cypher: str, params: dict[str, Any], n_rows: int, t0: float) -> None:
    log = _active_log.get()
    if log is not None:
        ms = (time.perf_counter() - t0) * 1000
        log.add(QueryLogEntry(name, cypher, _safe_params(params), n_rows, ms))


def connect() -> FalkorDB:
    return FalkorDB(
        host=os.environ.get("FALKORDB_HOST") or "localhost",
        port=int(os.environ.get("FALKORDB_PORT") or 6379),
        password=os.environ.get("FALKORDB_PASSWORD") or None,
    )


def select(graph_name: str, db: FalkorDB | None = None) -> Graph:
    return (db or connect()).select_graph(graph_name)


def _as_dicts(result: Any) -> list[dict[str, Any]]:
    header: list[Any] = cast(list[Any], result.header)
    cols = [str(h[1]) for h in header]  # header entries are [column_type, name]
    result_set: list[list[Any]] = cast(list[list[Any]], result.result_set)
    return [dict(zip(cols, row, strict=True)) for row in result_set]


def rows(
    graph: Graph, name: str, params: dict[str, Any], timeout_ms: int | None = None
) -> list[dict[str, Any]]:
    """Run a registry query read-only and return rows as dicts keyed by column name."""
    from app.graph.queries import load_query

    cypher = load_query(name)
    t0 = time.perf_counter()
    result: Any = graph.ro_query(cypher, params, timeout=timeout_ms or DEFAULT_TIMEOUT_MS)
    out = _as_dicts(result)
    _record(name, cypher, params, len(out), t0)
    return out


def write(
    graph: Graph, name: str, params: dict[str, Any], timeout_ms: int | None = None
) -> list[dict[str, Any]]:
    """Run a registry write query (parameterised, with a timeout)."""
    from app.graph.queries import load_query

    cypher = load_query(name)
    t0 = time.perf_counter()
    result: Any = graph.query(cypher, params, timeout=timeout_ms or WRITE_TIMEOUT_MS)
    out = _as_dicts(result) if getattr(result, "header", None) else []
    _record(name, cypher, params, len(out), t0)
    return out
