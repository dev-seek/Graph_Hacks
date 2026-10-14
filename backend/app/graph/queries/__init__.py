"""Query registry: every Cypher statement is a `<name>.cypher` file here (AGENTS.md rule 8)."""

from __future__ import annotations

from functools import cache
from pathlib import Path

_DIR = Path(__file__).parent


@cache
def load_query(name: str) -> str:
    return (_DIR / f"{name}.cypher").read_text(encoding="utf-8").strip()
