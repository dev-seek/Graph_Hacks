"""Replay adapter (spec §10.7) and the recording wrapper used by `record` mode."""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.cache import LLMCache, cache_key
from app.llm.errors import CacheMiss
from app.llm.port import BatchHandle, BatchItem, LLMPort, Message, T, TaskId


class ReplayAdapter:
    """Answers only from `data/llm_cache`; a miss raises `CacheMiss` (router falls back)."""

    def __init__(self, cache: LLMCache | None = None) -> None:
        self.cache = cache or LLMCache()

    def generate_structured(
        self, task: TaskId, messages: list[Message], schema: type[T], *, max_output_tokens: int
    ) -> T:
        hit = self.cache.get(task, cache_key(task, schema, messages[0].content))
        if hit is None:
            raise CacheMiss(f"{task}: no recorded answer")
        return schema.model_validate(hit)

    def submit_batch(self, task: TaskId, items: list[BatchItem], schema: type[T]) -> BatchHandle:
        raise CacheMiss("batches are not replayable")


class RecordingAdapter:
    """Reads the cache first (free), otherwise calls `inner` and writes the answer."""

    def __init__(self, inner: LLMPort, cache: LLMCache | None = None) -> None:
        self.inner = inner
        self.cache = cache or LLMCache()

    def generate_structured(
        self, task: TaskId, messages: list[Message], schema: type[T], *, max_output_tokens: int
    ) -> T:
        key = cache_key(task, schema, messages[0].content)
        hit = self.cache.get(task, key)
        if hit is not None:
            return schema.model_validate(hit)
        out: BaseModel = self.inner.generate_structured(
            task, messages, schema, max_output_tokens=max_output_tokens
        )
        self.cache.put(task, key, out)
        return out  # type: ignore[return-value]

    def submit_batch(self, task: TaskId, items: list[BatchItem], schema: type[T]) -> BatchHandle:
        return self.inner.submit_batch(task, items, schema)
