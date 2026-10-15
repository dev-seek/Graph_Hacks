"""Request shape of the live adapter, proven against a stub HTTP transport (no network, no key)."""

from __future__ import annotations

import json
from typing import Any

import anthropic
import httpx2
import pytest

from app.llm.adapters.anthropic_adapter import AnthropicAdapter
from app.llm.errors import LLMUnavailable
from app.llm.port import Message
from app.llm.schemas import StoryExtraction
from app.llm.settings import load_settings

BODY = {
    "id": "msg_1",
    "type": "message",
    "role": "assistant",
    "model": "claude-haiku-4-5",
    "content": [{"type": "text", "text": json.dumps({"items": []})}],
    "stop_reason": "end_turn",
    "stop_sequence": None,
    "usage": {"input_tokens": 10, "output_tokens": 5},
}


def _adapter(seen: list[httpx2.Request], body: dict[str, Any] = BODY) -> AnthropicAdapter:
    def handler(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json=body)

    client = anthropic.Anthropic(
        api_key="sk-test",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(handler)),
    )
    return AnthropicAdapter(load_settings(), client)


def test_plain_profile_request_shape() -> None:
    seen: list[httpx2.Request] = []
    s = load_settings().model_copy(update={"chosen": {"extract_story": "fast"}})
    a = _adapter(seen)
    a.settings = s
    out = a.generate_structured(
        "extract_story",
        [Message("user", "<input>x</input>")],
        StoryExtraction,
        max_output_tokens=900,
    )
    assert out.items == []
    req = json.loads(seen[0].content)
    assert req["model"] == s.profiles["fast"].model
    assert req["max_tokens"] == 900
    assert req["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert "tools" not in req
    assert a.last_usage["input"] == 10


def test_advisor_profile_uses_beta_endpoint_and_tool() -> None:
    seen: list[httpx2.Request] = []
    s = load_settings().model_copy(update={"chosen": {"read_document": "fast_advised"}})
    a = _adapter(seen)
    a.settings = s
    a.generate_structured(
        "read_document",
        [Message("user", "<input>x</input>")],
        StoryExtraction,
        max_output_tokens=1500,
    )
    req = json.loads(seen[0].content)
    tool = req["tools"][0]
    assert (
        tool["type"] == "advisor_20260301" and tool["name"] == "advisor" and tool["max_uses"] == 1
    )
    assert "advisor-tool-2026-03-01" in seen[0].headers["anthropic-beta"]


@pytest.mark.parametrize("stop", ["refusal", "max_tokens"])
def test_refusal_and_truncation_become_unavailable(stop: str) -> None:
    seen: list[httpx2.Request] = []
    a = _adapter(seen, {**BODY, "stop_reason": stop})
    with pytest.raises(LLMUnavailable):
        a.generate_structured(
            "extract_story",
            [Message("user", "<input>x</input>")],
            StoryExtraction,
            max_output_tokens=100,
        )
