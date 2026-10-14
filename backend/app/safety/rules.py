"""Deterministic red-flag matcher (spec §9, AGENTS.md rule 2).

Loads `review/safety_rules.yaml`. Matching is per sentence: a rule fires when one of its
patterns matches and none of its negations match in the same sentence. Optional age bounds
(`min_age_months` / `max_age_months`) gate a rule when the child's age is known.
The full engine in P2 builds on this; an LLM may only add flags, never remove them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

Level = Literal["EMERGENCY", "URGENT_SOON"]
DEFAULT_RULES_PATH = Path(__file__).resolve().parents[3] / "review" / "safety_rules.yaml"
# Split on sentence punctuation, but not on a "." between digits ("38.5C", "100.4F").
_SENTENCE_SPLIT = re.compile(r"(?<!\d)\.(?!\d)|[!?;\n]+")
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u02bc": "'", "`": "'"})


class Rule(BaseModel):
    id: str
    level: Level
    patterns: list[str]
    negations: list[str] = Field(default_factory=list)
    hpo_ids: list[str] = Field(default_factory=list)
    plain: str
    source: str
    min_age_months: int | None = None
    max_age_months: int | None = None


class CorpusCase(BaseModel):
    text: str
    expect_id: str
    age_months: int | None = None


class NegativeCase(BaseModel):
    text: str
    age_months: int | None = None


class Corpus(BaseModel):
    should_flag: list[CorpusCase]
    should_not_flag: list[NegativeCase | str]


class RuleFile(BaseModel):
    version: int
    required_ids: dict[Level, list[str]]
    crisis_lines: dict[str, str]
    emergency_numbers: dict[str, str]
    rules: list[Rule]
    corpus: Corpus


class Hit(BaseModel):
    rule_id: str
    level: Level
    plain: str


def load_rule_file(path: Path = DEFAULT_RULES_PATH) -> RuleFile:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return RuleFile.model_validate(raw)


def _age_ok(rule: Rule, age_months: int | None) -> bool:
    """Unknown age keeps age-gated rules active: over-flagging is safer than missing."""
    if age_months is None:
        return True
    if rule.min_age_months is not None and age_months < rule.min_age_months:
        return False
    return not (rule.max_age_months is not None and age_months > rule.max_age_months)


def _normalise(text: str) -> str:
    return text.translate(_APOSTROPHES).lower()


def _fires(rule: Rule, window: str) -> bool:
    """A pattern fires unless a negation match overlaps the pattern's own match span.

    Negations therefore only cancel the words they sit on, never an unrelated trigger elsewhere
    in the same window. A zero-width (lookahead-only) pattern
    is cancelled by any negation in the window.
    """
    negation_spans = [m.span() for n in rule.negations for m in re.finditer(n, window)]
    for pattern in rule.patterns:
        for m in re.finditer(pattern, window):
            start, end = m.span()
            if start == end:
                start, end = 0, len(window)
            if not any(ns < end and start < ne for ns, ne in negation_spans):
                return True
    return False


def match(rules: list[Rule], text: str, age_months: int | None = None) -> list[Hit]:
    """Return every rule that fires on `text`, most severe first.

    Each sentence and each pair of neighbouring sentences is a window, so facts split across
    sentences ("He had a seizure. It lasted 10 minutes.") are still caught.
    """
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(_normalise(text)) if s.strip()]
    windows = sentences + [f"{a}. {b}" for a, b in zip(sentences, sentences[1:], strict=False)]
    hits: list[Hit] = []
    for rule in rules:
        if _age_ok(rule, age_months) and any(_fires(rule, w) for w in windows):
            hits.append(Hit(rule_id=rule.id, level=rule.level, plain=rule.plain))
    hits.sort(key=lambda h: h.level != "EMERGENCY")
    return hits
