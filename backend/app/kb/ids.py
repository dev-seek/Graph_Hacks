"""One normaliser for every identifier we ingest, so all sources emit the same form."""

from __future__ import annotations

import re

_URI_TAIL = re.compile(r"([A-Za-z]+)[_:](\d+)$")
_SOURCES = {"ORPHA": "ORPHA", "ORPHANET": "ORPHA", "OMIM": "OMIM"}


def norm_hpo(value: str) -> str:
    """`HP_0001250`, `HP:0001250` or an OBO URI -> `HP:0001250` (any ontology prefix)."""
    m = _URI_TAIL.search(value.strip())
    if not m:
        raise ValueError(f"not an ontology id: {value!r}")
    return f"{m.group(1).upper()}:{m.group(2)}"


def norm_disease(source: str, code: str) -> str:
    """('orphanet', '123') / ('ORPHA', 'ORPHA:123') -> `ORPHA:123`; OMIM likewise."""
    prefix = _SOURCES.get(source.strip().upper())
    if prefix is None:
        raise ValueError(f"unknown disease source: {source!r}")
    digits = re.sub(r"^[A-Za-z]+:", "", code.strip())
    if not digits.isdigit():
        raise ValueError(f"not a numeric disease code: {code!r}")
    return f"{prefix}:{digits}"
