"""Parent-facing wording check (spec §10.9, AGENTS.md rule 1, P1 review #7).

A rephrased question or explanation must not read like a diagnosis: no disease-flavoured words,
no eponyms, no probabilities. Used on every LLM-written parent text and on `cx_question` copy.
"""

from __future__ import annotations

import re

BANNED_WORDS = frozenset(
    """diagnosis diagnoses diagnosed diagnose syndrome disease disorder condition probability
    probable likelihood likely chance percent cancer tumour tumor carrier genetic mutation
    chromosomal retardation retarded mongoloid idiot imbecile handicap handicapped crippled
    deformed abnormal abnormality abnormalities anomaly anomalies morphology hypoplasia dysplasia
    aplasia agenesis""".split()
)
# Disease-flavoured suffixes (-ism, -itis, -osis, -pathy, -emia, -oma, -oid) with lay exceptions.
_SUFFIX = re.compile(r"\b[a-z]{2,}(?:ism|itis|osis|opathy|pathy|aemia|emia|oma|oid)\b")
_LAY_OK = frozenset(
    """tonsillitis bronchitis asthma stoma coma criticism organism rhythm schism mechanism
    prism symptom android""".split()
)
_EPONYM = re.compile(r"\b[A-Z][a-z]+(?:'s|’s)\s+(?:disease|syndrome|sign|palsy)\b")
_PERCENT = re.compile(r"\d\s*%")
_TOKEN = re.compile(r"[a-z]+")


def violations(text: str, extra_banned: frozenset[str] = frozenset()) -> list[str]:
    """Return the offending words/patterns in `text` (empty list = clean)."""
    out: list[str] = []
    lowered = text.lower()
    for tok in _TOKEN.findall(lowered):
        if tok in BANNED_WORDS or tok in extra_banned:
            out.append(tok)
    for m in _SUFFIX.finditer(lowered):
        if m.group(0) not in _LAY_OK:
            out.append(m.group(0))
    out += [m.group(0) for m in _EPONYM.finditer(text)]
    out += [m.group(0) for m in _PERCENT.finditer(text)]
    return sorted(set(out))


def is_clean(text: str, extra_banned: frozenset[str] = frozenset()) -> bool:
    return not violations(text, extra_banned)
