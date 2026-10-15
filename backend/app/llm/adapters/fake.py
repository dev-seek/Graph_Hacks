"""Deterministic fake adapter for tests (spec §10.3): no network, scripted or rule-based output."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from app.llm.errors import LLMUnavailable
from app.llm.fallbacks import clause_items
from app.llm.port import BatchHandle, BatchItem, Message, T, TaskId

Handler = Callable[[str], BaseModel]
_INPUT = re.compile(r"<input>\n?(.*?)\n?</input>", re.DOTALL)


def unwrap_input(content: str) -> str:
    m = _INPUT.search(content)
    return m.group(1) if m else content


def _extract_clauses(text: str, schema: type[BaseModel]) -> BaseModel:
    items: list[dict[str, Any]] = []
    for it in clause_items(text):
        item = {k: it[k] for k in ("quote", "plain_label", "status")}
        if schema.__name__ == "DocExtraction":
            item["source"] = "doctor_exam"
        items.append(item)
    return schema.model_validate({"items": items})


class FakeAdapter:
    """Counts calls per task; `handlers[task](input_text)` overrides the defaults."""

    def __init__(self, handlers: dict[str, Handler] | None = None) -> None:
        self.handlers = handlers or {}
        self.calls: list[tuple[str, str]] = []

    def generate_structured(
        self, task: TaskId, messages: list[Message], schema: type[T], *, max_output_tokens: int
    ) -> T:
        text = unwrap_input(messages[0].content)
        self.calls.append((task, text))
        if task in self.handlers:
            return schema.model_validate(self.handlers[task](text).model_dump())
        if task in ("extract_story", "read_document"):
            return _extract_clauses(text, schema)  # type: ignore[return-value]
        if task == "phrase_question":
            q = json.loads(text)
            return schema.model_validate({"question": q["question"], "why": q["why"]})
        if task == "safety_extra":
            return schema.model_validate({"concerns": []})
        raise LLMUnavailable(f"fake adapter has no default for {task}")

    def submit_batch(self, task: TaskId, items: list[BatchItem], schema: type[T]) -> BatchHandle:
        raise LLMUnavailable("fake adapter has no batches")
