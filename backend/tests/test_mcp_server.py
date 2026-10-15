"""Integration: the MCP server lists its four read-only tools and answers calls (in-process)."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp.client import Client

from app.agents.deps import AgentDeps
from app.llm.router import LLMRouter
from app.mcp.server import build_server
from tests.agents.helpers import NoEmbedder
from tests.conftest import requires_kb

pytestmark = [pytest.mark.integration, requires_kb]


def _payload(result: Any) -> Any:
    return result.structured_content or result.content[0].text


def test_lists_four_tools_and_calls_two() -> None:
    deps = AgentDeps.build(router=LLMRouter(mode="off"), embedder=NoEmbedder())
    server = build_server(deps)

    async def go() -> tuple[set[str], Any, Any, Any]:
        async with Client(server) as c:
            tools = {t.name for t in (await c.list_tools()).tools}
            r1 = await c.call_tool("resolve_phenotype", {"text": "tiptoe walking"})
            r2 = await c.call_tool(
                "rank_candidates",
                {"findings": [{"term_id": "HP:0030051", "status": "present"}]},
            )
            r3 = await c.call_tool("centre_route_case", {"hpo_ids": ["HP:0030051"]})
            return tools, r1, r2, r3

    tools, r1, r2, r3 = asyncio.run(go())
    assert tools == {
        "resolve_phenotype",
        "rank_candidates",
        "explain_candidate",
        "centre_route_case",
    }
    assert "HP:" in str(_payload(r1))
    assert "disclaimer" in str(_payload(r2)).lower()
    assert "available" in str(_payload(r3))
