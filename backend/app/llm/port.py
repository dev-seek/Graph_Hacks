"""LLM ports (spec §10.1). The only interface the rest of the code uses to reach a model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

TaskId = Literal[
    "extract_story",
    "phrase_question",
    "read_document",
    "draft_referral",
    "label_terms",
    "safety_extra",
    "centre_template_pick",
]


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class BatchItem:
    custom_id: str
    messages: list[Message]


@dataclass(frozen=True)
class BatchHandle:
    batch_id: str


class LLMPort(Protocol):
    def generate_structured(
        self, task: TaskId, messages: list[Message], schema: type[T], *, max_output_tokens: int
    ) -> T: ...

    def submit_batch(
        self, task: TaskId, items: list[BatchItem], schema: type[T]
    ) -> BatchHandle: ...  # offline only


class EmbeddingPort(Protocol):
    dim: int
    model_id: str  # recorded in KbInfo; changing it requires re-embedding (make kb)

    def embed(self, texts: list[str]) -> list[list[float]]: ...
