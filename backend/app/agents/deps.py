"""Everything the agent nodes need, built once at startup (kb graph, reasoner, LLM, safety)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from falkordb import FalkorDB, Graph

from app.engine.config import tuned_taus
from app.engine.gates import Taus
from app.engine.reasoner import Reasoner
from app.graph.client import connect
from app.graph.family import FamilyRepo
from app.kb.info import KbInfo, load_kb_info
from app.kb.resolve import TermResolver
from app.llm.adapters.embedding import FastEmbedder
from app.llm.port import EmbeddingPort
from app.llm.router import LLMRouter
from app.ports.notifier import NotifierPort
from app.safety.engine import SafetyEngine


class LogNotifier:
    """Hackathon notifier (spec §17.1): the watcher log; the UI shows the banner."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def notify(self, family_id: str, kind: str, plain_text: str) -> None:
        self.sent.append((family_id, kind, plain_text))


@dataclass
class AgentDeps:
    db: FalkorDB
    kb: Graph
    kb_version: str
    hpo_version: str
    reasoner: Reasoner
    resolver: TermResolver
    router: LLMRouter
    safety: SafetyEngine
    taus: Taus = field(default_factory=Taus)
    notifier: NotifierPort = field(default_factory=LogNotifier)
    new_kb: Callable[[], str | None] = lambda: None  # latest kb release newer than kb_version

    def repo(self, family_id: str) -> FamilyRepo:
        return FamilyRepo(family_id, self.db)

    @classmethod
    def build(
        cls,
        router: LLMRouter | None = None,
        embedder: EmbeddingPort | None = None,
        info: KbInfo | None = None,
    ) -> AgentDeps:
        info = info or load_kb_info()
        if info is None:
            raise RuntimeError("no knowledge base built: run `make kb`")
        db = connect()
        kb = db.select_graph(info.release)
        return cls(
            db=db,
            kb=kb,
            kb_version=info.release,
            hpo_version=info.hpo_version,
            reasoner=Reasoner(kb),
            resolver=TermResolver(kb, embedder or FastEmbedder()),
            router=router or LLMRouter(),
            safety=SafetyEngine.from_file(),
            taus=tuned_taus(),
        )
