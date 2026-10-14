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
_SENTENCE_SPLIT = re.compile(r"[.!?;\n]+")


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


def match(rules: list[Rule], text: str, age_months: int | None = None) -> list[Hit]:
    """Return every rule that fires on `text` (lower-cased internally), most severe first."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text.lower()) if s.strip()]
    hits: list[Hit] = []
    for rule in rules:
        if not _age_ok(rule, age_months):
            continue
        for sentence in sentences:
            if any(re.search(p, sentence) for p in rule.patterns) and not any(
                re.search(n, sentence) for n in rule.negations
            ):
                hits.append(Hit(rule_id=rule.id, level=rule.level, plain=rule.plain))
                break
    hits.sort(key=lambda h: h.level != "EMERGENCY")
    return hits
