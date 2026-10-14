"""Safety engine (spec §8.4): deterministic first, LLM add-only, corpus self-check."""

from __future__ import annotations

from app.safety.engine import (
    ExtraConcern,
    SafetyEngine,
    run_corpus,
)
from app.safety.rules import Rule

R_EMERG = Rule(
    id="e1", level="EMERGENCY", patterns=[r"\bblue lips\b"], plain="Call emergency", source="t"
)
R_SOON = Rule(
    id="s1",
    level="URGENT_SOON",
    patterns=[r"\bwobbly\b"],
    hpo_ids=["HP:0001251"],
    plain="See doctor soon",
    source="t",
)


def engine() -> SafetyEngine:
    return SafetyEngine([R_EMERG, R_SOON])


def test_emergency_first_and_gate_state() -> None:
    res = engine().screen("her lips are blue lips and she is wobbly")
    assert [f.rule_id for f in res.flags] == ["e1", "s1"]
    assert res.emergency and res.urgent_soon


def test_hpo_descendant_of_rule_term_fires() -> None:
    anc = {"HP:0002070": {"HP:0002070", "HP:0001251"}}
    res = engine().screen("", present_terms=["HP:0002070"], ancestors=anc)
    assert [f.rule_id for f in res.flags] == ["s1"] and res.flags[0].source == "hpo"


def test_llm_extra_can_only_add_urgent_soon_with_quote_in_text() -> None:
    text = "She seems quieter and keeps hiding in her room"
    extra = [ExtraConcern(quote="keeps hiding in her room", level="EMERGENCY", why="withdrawal")]
    res = engine().screen(text, extra=extra)
    assert [(f.rule_id, f.level) for f in res.flags] == [("llm_extra", "URGENT_SOON")]
    assert "call emergency services" in res.flags[0].plain.lower()
    assert not res.emergency


def test_llm_extra_with_quote_not_in_text_is_dropped() -> None:
    extra = [ExtraConcern(quote="never said this", level="URGENT_SOON", why="x")]
    assert engine().screen("hello", extra=extra).flags == []


def test_llm_extra_never_removes_a_deterministic_flag() -> None:
    res = engine().screen("blue lips", extra=[])
    assert res.emergency
    res2 = engine().screen(
        "blue lips", extra=[ExtraConcern(quote="zzz", level="URGENT_SOON", why="")]
    )
    assert res2.emergency


def test_run_corpus_reports_all_pass_for_reviewed_file() -> None:
    result = run_corpus()
    assert result.failures == [] and result.total >= 60 and result.passed == result.total
