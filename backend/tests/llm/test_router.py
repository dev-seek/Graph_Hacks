from __future__ import annotations

import json
from pathlib import Path

from app.llm.adapters.fake import FakeAdapter
from app.llm.adapters.replay import RecordingAdapter, ReplayAdapter
from app.llm.cache import LLMCache, cache_key
from app.llm.router import LLMRouter
from app.llm.schemas import Rephrase, StoryExtraction
from app.llm.settings import LLMSettings, load_settings, substitute


def _settings() -> LLMSettings:
    return load_settings()


def _fallback() -> StoryExtraction:
    return StoryExtraction(items=[])


def test_env_substitution_default_and_override() -> None:
    assert substitute("m: ${LLM_MODE:-replay}", {}) == "m: replay"
    assert substitute("m: ${LLM_MODE:-replay}", {"LLM_MODE": "fake"}) == "m: fake"


def test_settings_load_and_profiles() -> None:
    s = _settings()
    assert s.profile_for("extract_story").model.startswith("claude-")
    assert s.profile_for("read_document").max_output_tokens > 0


def test_off_mode_always_falls_back_without_adapter_calls() -> None:
    r = LLMRouter(_settings(), mode="off")
    res = r.run("extract_story", "he is floppy", StoryExtraction, _fallback)
    assert res.source == "fallback" and res.reason == "mode_off"


def test_fake_mode_returns_model_answer_and_counts_one_call() -> None:
    fake = FakeAdapter()
    r = LLMRouter(_settings(), mode="fake", adapter=fake)
    res = r.run("extract_story", "He is floppy, and he has no fever.", StoryExtraction, _fallback)
    assert res.source == "llm"
    assert [i.status for i in res.value.items] == ["present", "absent"]
    assert len(fake.calls) == 1


def test_repair_retry_then_success() -> None:
    attempts: list[int] = []

    def handler(_: str) -> StoryExtraction:
        attempts.append(1)
        if len(attempts) == 1:
            raise ValueError("bad quote")
        return StoryExtraction(items=[])

    r = LLMRouter(_settings(), mode="fake", adapter=FakeAdapter({"extract_story": handler}))
    res = r.run("extract_story", "x y", StoryExtraction, _fallback)
    assert res.source == "llm" and len(attempts) == 2


def test_two_invalid_answers_fall_back() -> None:
    def handler(_: str) -> StoryExtraction:
        raise ValueError("always bad")

    r = LLMRouter(_settings(), mode="fake", adapter=FakeAdapter({"extract_story": handler}))
    res = r.run("extract_story", "x y", StoryExtraction, _fallback)
    assert res.source == "fallback" and "invalid_after_repair" in (res.reason or "")


def test_validate_callback_failure_triggers_repair_then_fallback() -> None:
    def validate(_: StoryExtraction) -> None:
        raise ValueError("quote not in input")

    r = LLMRouter(_settings(), mode="fake", adapter=FakeAdapter())
    res = r.run("extract_story", "He is floppy", StoryExtraction, _fallback, validate=validate)
    assert res.source == "fallback"


def test_replay_miss_falls_back_without_error(tmp_path: Path) -> None:
    r = LLMRouter(_settings(), mode="replay", cache=LLMCache(tmp_path))
    res = r.run("extract_story", "never recorded", StoryExtraction, _fallback)
    assert res.source == "fallback" and "CacheMiss" in (res.reason or "")


def test_record_then_replay_roundtrip(tmp_path: Path) -> None:
    cache = LLMCache(tmp_path)
    fake = FakeAdapter()
    rec = LLMRouter(_settings(), mode="record", adapter=RecordingAdapter(fake, cache), cache=cache)
    first = rec.run("extract_story", "He is floppy now", StoryExtraction, _fallback)
    again = LLMRouter(_settings(), mode="replay", adapter=ReplayAdapter(cache), cache=cache)
    second = again.run("extract_story", "He  is FLOPPY now", StoryExtraction, _fallback)
    assert second.source == "llm" and second.value == first.value
    assert len(fake.calls) == 1  # whitespace/case-normalised key, no second live call


def test_cache_key_depends_on_task_schema_and_input() -> None:
    a = cache_key("extract_story", StoryExtraction, "<input>a</input>")
    assert a != cache_key("extract_story", StoryExtraction, "<input>b</input>")
    assert a != cache_key("phrase_question", Rephrase, "<input>a</input>")


def test_family_budget_exhausted_falls_back() -> None:
    s = _settings().model_copy(deep=True)
    s.budget.per_family_tokens = 1
    r = LLMRouter(s, mode="fake", adapter=FakeAdapter())
    r.run("extract_story", "He is floppy, he is small", StoryExtraction, _fallback, family_id="f1")
    res = r.run("extract_story", "again here", StoryExtraction, _fallback, family_id="f1")
    assert res.reason == "family_budget"


def test_daily_budget_exhausted_falls_back_and_resets_next_day() -> None:
    s = _settings().model_copy(deep=True)
    s.budget.daily_tokens = 1
    clock = [100.0]
    r = LLMRouter(s, mode="fake", adapter=FakeAdapter(), clock=lambda: clock[0])
    first = r.run("extract_story", "He is floppy, he is small", StoryExtraction, _fallback)
    assert first.source == "llm"
    res = r.run("extract_story", "again here", StoryExtraction, _fallback)
    assert (res.source, res.reason) == ("fallback", "daily_budget")
    clock[0] += 86400 * 1.1  # a new UTC day
    assert r.run("extract_story", "new day", StoryExtraction, _fallback).source == "llm"


def test_replay_mode_is_not_metered() -> None:
    s = _settings().model_copy(deep=True)
    s.budget.daily_tokens = 1
    r = LLMRouter(s, mode="replay", adapter=FakeAdapter())
    for _ in range(3):
        assert r.run("extract_story", "some story", StoryExtraction, _fallback).source == "llm"


def test_input_is_wrapped_in_input_tags() -> None:
    fake = FakeAdapter({"phrase_question": lambda t: Rephrase(question="q", why="w")})
    seen: list[str] = []
    orig = fake.generate_structured

    def spy(task, messages, schema, *, max_output_tokens):  # type: ignore[no-untyped-def]
        seen.append(messages[0].content)
        return orig(task, messages, schema, max_output_tokens=max_output_tokens)

    fake.generate_structured = spy  # type: ignore[method-assign]
    r = LLMRouter(_settings(), mode="fake", adapter=fake)
    r.run(
        "phrase_question",
        json.dumps({"question": "q", "why": "w"}),
        Rephrase,
        lambda: Rephrase(question="q", why="w"),
    )
    assert seen[0].startswith("<input>\n") and seen[0].endswith("\n</input>")
