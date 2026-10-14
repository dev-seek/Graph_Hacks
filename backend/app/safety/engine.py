"""Safety engine (spec §8.4): rules first; an LLM may only add a flag, never remove one."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from app.safety.rules import (
    DEFAULT_RULES_PATH,
    Level,
    NegativeCase,
    Rule,
    load_rule_file,
    match,
)

LLM_EXTRA_ID = "llm_extra"
LLM_EXTRA_SUFFIX = " If you are worried, call emergency services."


class ExtraConcern(BaseModel):
    """What the `safety_extra` LLM task proposes. Treated as a suggestion, never as a decision."""

    quote: str
    level: Level
    why: str


class Flag(BaseModel):
    rule_id: str
    level: Level
    plain: str
    source: Literal["pattern", "hpo", "llm"] = "pattern"
    quote: str | None = None


class ScreenResult(BaseModel):
    flags: list[Flag]

    @property
    def emergency(self) -> bool:
        return any(f.level == "EMERGENCY" for f in self.flags)

    @property
    def urgent_soon(self) -> bool:
        return any(f.level == "URGENT_SOON" for f in self.flags)


class CorpusResult(BaseModel):
    total: int
    passed: int
    failures: list[str]


class SafetyEngine:
    def __init__(self, rules: list[Rule]) -> None:
        self.rules = rules

    @classmethod
    def from_file(cls, path: Path = DEFAULT_RULES_PATH) -> SafetyEngine:
        return cls(load_rule_file(path).rules)

    def screen(
        self,
        text: str,
        *,
        age_months: int | None = None,
        present_terms: Sequence[str] = (),
        ancestors: Mapping[str, set[str]] | None = None,
        extra: Sequence[ExtraConcern] = (),
    ) -> ScreenResult:
        flags = [
            Flag(rule_id=h.rule_id, level=h.level, plain=h.plain)
            for h in match(self.rules, text, age_months)
        ]
        seen = {f.rule_id for f in flags}
        anc = ancestors or {}
        for rule in self.rules:
            if rule.id in seen or not rule.hpo_ids:
                continue
            if any(set(rule.hpo_ids) & (anc.get(t, set()) | {t}) for t in present_terms):
                flags.append(
                    Flag(rule_id=rule.id, level=rule.level, plain=rule.plain, source="hpo")
                )
        flags.sort(key=lambda f: f.level != "EMERGENCY")
        lowered = text.lower()
        for concern in extra:
            quote = concern.quote.strip()
            if not quote or quote.lower() not in lowered or LLM_EXTRA_ID in seen:
                continue  # only quoted spans that really occur in the text are accepted
            plain = f"We noticed something that may need a doctor's attention: “{quote}”."
            if concern.level == "EMERGENCY":
                plain += LLM_EXTRA_SUFFIX
            flags.append(
                Flag(
                    rule_id=LLM_EXTRA_ID,
                    level="URGENT_SOON",
                    plain=plain,
                    source="llm",
                    quote=quote,
                )
            )
            seen.add(LLM_EXTRA_ID)
        return ScreenResult(flags=flags)


def run_corpus(path: Path = DEFAULT_RULES_PATH) -> CorpusResult:
    """Run the corpus embedded in the rules file against its own rules (must be all-pass)."""
    rf = load_rule_file(path)
    failures: list[str] = []
    total = 0
    for c in rf.corpus.should_flag:
        total += 1
        if c.expect_id not in [h.rule_id for h in match(rf.rules, c.text, c.age_months)]:
            failures.append(f"should flag {c.expect_id}: {c.text}")
    for n in rf.corpus.should_not_flag:
        total += 1
        case = NegativeCase(text=n) if isinstance(n, str) else n
        if match(rf.rules, case.text, case.age_months):
            failures.append(f"should not flag: {case.text}")
    return CorpusResult(total=total, passed=total - len(failures), failures=failures)
