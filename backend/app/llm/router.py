"""LLM router (spec §10.1): mode -> adapter, budget, timeout, one repair retry, fallback.

Every call returns a value: the model's validated answer, or the deterministic fallback with the
reason recorded. Logs carry ids and sizes only, never parent text (AGENTS.md).
"""

from __future__ import annotations

import concurrent.futures
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Literal

import structlog
from pydantic import ValidationError

from app.llm.adapters.fake import FakeAdapter
from app.llm.adapters.replay import RecordingAdapter, ReplayAdapter
from app.llm.cache import LLMCache
from app.llm.errors import LLMUnavailable
from app.llm.port import LLMPort, Message, T, TaskId
from app.llm.settings import LLMSettings, Mode, load_settings

log = structlog.get_logger("llm")
Source = Literal["llm", "fallback"]
CHARS_PER_TOKEN = 4


@dataclass
class LLMResult(Generic[T]):  # noqa: UP046 (T is the port's shared TypeVar)
    value: T
    source: Source
    reason: str | None = None  # why the fallback was used


def wrap_input(text: str) -> str:
    """Parent text is data, never instructions (spec §10.9)."""
    return f"<input>\n{text}\n</input>"


class LLMRouter:
    def __init__(
        self,
        settings: LLMSettings | None = None,
        *,
        mode: Mode | None = None,
        adapter: LLMPort | None = None,
        cache: LLMCache | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.settings = settings or load_settings()
        self.mode: Mode = mode or self.settings.mode
        self.cache = cache or LLMCache()
        self.adapter = adapter or self._build_adapter()
        self.family_tokens: dict[str, int] = {}
        self._clock = clock
        self._day = -1
        self._day_tokens = 0

    def _build_adapter(self) -> LLMPort | None:
        if self.mode == "off":
            return None
        if self.mode == "fake":
            return FakeAdapter()
        if self.mode == "replay":
            return ReplayAdapter(self.cache)
        from app.llm.adapters.anthropic_adapter import AnthropicAdapter

        live = AnthropicAdapter(self.settings)
        return RecordingAdapter(live, self.cache) if self.mode == "record" else live

    def run(
        self,
        task: TaskId,
        input_text: str,
        schema: type[T],
        fallback: Callable[[], T],
        *,
        validate: Callable[[T], None] | None = None,
        family_id: str | None = None,
    ) -> LLMResult[T]:
        def fell_back(reason: str) -> LLMResult[T]:
            log.info("llm_fallback", task=task, reason=reason, mode=self.mode, family=family_id)
            return LLMResult(fallback(), "fallback", reason)

        if self.adapter is None:
            return fell_back("mode_off")
        budget = self.settings.budget.per_family_tokens
        used = self.family_tokens.get(family_id or "", 0)
        if family_id and used >= budget:
            return fell_back("family_budget")
        if self._metered and self._today_tokens() >= self.settings.budget.daily_tokens:
            return fell_back("daily_budget")
        max_out = self.settings.profile_for(task).max_output_tokens
        messages = [Message("user", wrap_input(input_text))]
        error: str | None = None
        for attempt in range(2):
            try:
                out = self._call(task, messages, schema, max_out)
                if validate is not None:
                    validate(out)
            except (ValidationError, ValueError) as exc:
                error = str(exc)[:500]
                messages = [
                    messages[0],
                    Message(
                        "user",
                        f"Your previous answer was invalid: {error}\nReturn a corrected answer.",
                    ),
                ]
                continue
            except LLMUnavailable as exc:
                return fell_back(f"unavailable:{type(exc).__name__}")
            except Exception as exc:  # noqa: BLE001 (any adapter/network failure degrades)
                return fell_back(f"error:{type(exc).__name__}")
            spent = (len(input_text) + len(out.model_dump_json())) // CHARS_PER_TOKEN
            if family_id:
                self.family_tokens[family_id] = used + spent
            if self._metered:
                self._day_tokens = self._today_tokens() + max(spent, 1)
            log.info("llm_ok", task=task, mode=self.mode, attempt=attempt, family=family_id)
            return LLMResult(out, "llm")
        return fell_back("invalid_after_repair")  # error text can echo parent words: not logged

    @property
    def _metered(self) -> bool:
        return self.mode != "replay"  # replay reads the cache and costs nothing

    def _today_tokens(self) -> int:
        day = int(self._clock() // 86400)
        if day != self._day:
            self._day, self._day_tokens = day, 0
        return self._day_tokens

    def _call(self, task: TaskId, messages: list[Message], schema: type[T], max_out: int) -> T:
        assert self.adapter is not None  # noqa: S101
        adapter = self.adapter
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        fut = pool.submit(
            adapter.generate_structured, task, messages, schema, max_output_tokens=max_out
        )
        try:
            return fut.result(timeout=self.settings.timeout_s)
        except concurrent.futures.TimeoutError as exc:
            raise LLMUnavailable("timeout") from exc
        finally:
            pool.shutdown(wait=False)
