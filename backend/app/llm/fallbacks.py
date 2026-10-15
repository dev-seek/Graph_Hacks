"""Deterministic fallbacks shared by the router callers and the fake adapter (spec §10.2)."""

from __future__ import annotations

import re
from typing import Any

# "no fever", "never had a fit", "no sign of ...": the child does NOT have the thing. A clause like
# "does not walk" describes a present difficulty, so a bare "not" is not a negation here.
NEGATION = re.compile(
    r"^\W*(no|never|without|none|nor)\b|\b(no (sign|signs|history|evidence) of|has ?n[o']t had|"
    r"hasn't had|has not had|have not had|haven't had|never (had|has|been)|denies|denied|"
    r"(has|had|have|with) no)\b",
    re.IGNORECASE,
)
MIN_CLAUSE_WORDS = 3
MAX_ITEMS = 25
# Clauses are split on sentence punctuation and on "and"/"but" so each carries one observation.
_CLAUSE = re.compile(r"[^.;,!?\n]+")
_JOINER = re.compile(r"\s+(?:and|but|also|plus)\s+", re.IGNORECASE)


def clause_items(text: str) -> list[dict[str, Any]]:
    """Noun-phrase-ish split of free text; every `quote` is an exact substring of `text`."""
    items: list[dict[str, Any]] = []
    for m in _CLAUSE.finditer(text):
        base = m.start()
        piece = m.group(0)
        pos = 0
        parts: list[tuple[int, str]] = []
        for j in _JOINER.finditer(piece):
            parts.append((pos, piece[pos : j.start()]))
            pos = j.end()
        parts.append((pos, piece[pos:]))
        for off, part in parts:
            lead = len(part) - len(part.lstrip())
            quote = part.strip()
            if len(quote.split()) < MIN_CLAUSE_WORDS:
                continue
            start = base + off + lead
            items.append(
                {
                    "quote": quote,
                    "plain_label": " ".join(quote.split()[:8]),
                    "status": "absent" if NEGATION.search(quote) else "present",
                    "start": start,
                    "end": start + len(quote),
                }
            )
            if len(items) >= MAX_ITEMS:
                return items
    return items
