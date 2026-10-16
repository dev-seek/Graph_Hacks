from __future__ import annotations

from collections.abc import Iterator

import pytest
from langchain_falkordb.checkpoint import FalkorDBSaver

from app.agents.deps import AgentDeps
from app.agents.service import FamilyService
from app.graph.client import connect
from app.kb.info import load_kb_info
from app.llm.adapters.fake import FakeAdapter
from app.llm.router import LLMRouter
from tests.agents.helpers import NoEmbedder


def _kb_ready() -> bool:
    info = load_kb_info()
    if info is None:
        return False
    try:
        return info.release in connect().list_graphs()
    except Exception:  # noqa: BLE001
        return False


requires_kb = pytest.mark.skipif(not _kb_ready(), reason="needs the built kb (make kb) + FalkorDB")


@pytest.fixture(scope="session")
def make_service() -> Iterator[object]:
    def factory(mode: str = "fake", adapter: FakeAdapter | None = None) -> FamilyService:
        saver = FalkorDBSaver(database="langgraph_checkpoints_test")  # fresh connection each time
        router = LLMRouter(mode=mode, adapter=adapter if mode == "fake" else None)  # type: ignore[arg-type]
        deps = AgentDeps.build(router=router, embedder=NoEmbedder())
        return FamilyService(deps, saver)

    yield factory
