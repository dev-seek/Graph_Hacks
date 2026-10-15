"""The only module that imports the `anthropic` SDK (AGENTS.md rule 5).

Structured output through `messages.parse(output_format=<Pydantic>)`; the static system block is
marked for prompt caching; advisor profiles go through the beta endpoint with the advisor tool.
The key is read from `ANTHROPIC_API_KEY` by the SDK itself and never logged.
"""

from __future__ import annotations

from typing import Any, cast

import anthropic
from pydantic import BaseModel

from app.llm.errors import LLMUnavailable
from app.llm.port import BatchHandle, BatchItem, Message, T, TaskId
from app.llm.prompts import load_prompt
from app.llm.settings import LLMSettings, Profile

ADVISOR_BETA = "advisor-tool-2026-03-01"
ADVISOR_TOOL_TYPE = "advisor_20260301"


class AnthropicAdapter:
    def __init__(self, settings: LLMSettings, client: anthropic.Anthropic | None = None) -> None:
        self.settings = settings
        self.client = client or anthropic.Anthropic(
            timeout=settings.timeout_s, max_retries=1
        )  # key from ANTHROPIC_API_KEY
        self.last_usage: dict[str, int] = {}

    # --- request building (unit-tested through a stub transport) -----------------------------

    def request_kwargs(
        self, task: TaskId, messages: list[Message], max_output_tokens: int
    ) -> dict[str, Any]:
        profile = self.settings.profile_for(task)
        system_block: dict[str, Any] = {"type": "text", "text": load_prompt(task)}
        if self.settings.prompt_cache:
            system_block["cache_control"] = {"type": "ephemeral"}
        kwargs: dict[str, Any] = {
            "model": profile.model,
            "max_tokens": min(max_output_tokens, profile.max_output_tokens),
            "system": [system_block],
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if profile.advisor is not None:
            kwargs["betas"] = [ADVISOR_BETA]
            kwargs["tools"] = [
                {
                    "type": ADVISOR_TOOL_TYPE,
                    "name": "advisor",
                    "model": profile.advisor.model,
                    "max_uses": profile.advisor.max_uses,
                    "max_tokens": profile.advisor.max_tokens,
                }
            ]
        return kwargs

    def generate_structured(
        self, task: TaskId, messages: list[Message], schema: type[T], *, max_output_tokens: int
    ) -> T:
        profile: Profile = self.settings.profile_for(task)
        kwargs = self.request_kwargs(task, messages, max_output_tokens)
        try:
            if profile.advisor is not None:
                resp: Any = self.client.beta.messages.parse(output_format=schema, **kwargs)
            else:
                resp = self.client.messages.parse(output_format=schema, **kwargs)
        except anthropic.APIError as exc:
            raise LLMUnavailable(f"{type(exc).__name__}") from exc
        if resp.stop_reason in ("refusal", "max_tokens"):
            raise LLMUnavailable(f"stop_reason={resp.stop_reason}")
        usage = resp.usage
        self.last_usage = {
            "input": int(usage.input_tokens or 0),
            "output": int(usage.output_tokens or 0),
            "cache_read": int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        }
        parsed = resp.parsed_output
        if parsed is None:
            raise ValueError("model returned no parsable structured output")
        return cast(T, parsed)

    def submit_batch(self, task: TaskId, items: list[BatchItem], schema: type[T]) -> BatchHandle:
        profile = self.settings.profile_for(task)
        output_schema: type[BaseModel] = schema
        requests: list[Any] = [
            {
                "custom_id": it.custom_id,
                "params": {
                    "model": profile.model,
                    "max_tokens": profile.max_output_tokens,
                    "system": [
                        {
                            "type": "text",
                            "text": load_prompt(task),
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    "messages": [{"role": m.role, "content": m.content} for m in it.messages],
                    "output_config": {
                        "format": {
                            "type": "json_schema",
                            "schema": output_schema.model_json_schema(),
                        }
                    },
                },
            }
            for it in items
        ]
        batch = self.client.messages.batches.create(requests=requests)
        return BatchHandle(batch.id)
