"""`make demo-record` / `make demo-replay`."""

from __future__ import annotations

import os
import sys

from langchain_falkordb.checkpoint import FalkorDBSaver

from app.agents.demo import (
    JOURNEYS,
    CachedEmbedder,
    fingerprint,
    load_demo,
    run_all,
    save,
)
from app.agents.deps import AgentDeps
from app.agents.service import FamilyService
from app.llm.adapters.embedding import FastEmbedder
from app.llm.router import LLMRouter


def _service(mode: str, record: bool) -> tuple[FamilyService, CachedEmbedder]:
    inner = None
    if record:
        try:
            inner = FastEmbedder()
        except Exception:  # noqa: BLE001
            inner = None
    emb = CachedEmbedder(inner)
    deps = AgentDeps.build(router=LLMRouter(mode=mode), embedder=emb)  # type: ignore[arg-type]
    return FamilyService(deps, FalkorDBSaver(database="langgraph_checkpoints")), emb


def record() -> int:
    mode = os.environ.get("LLM_MODE") or (
        "record" if os.environ.get("ANTHROPIC_API_KEY") else "off"
    )
    svc, emb = _service(mode, record=True)
    docs, picks = run_all(svc, mode)
    emb.save()
    save(docs)
    print(f"demo-record: llm_mode={mode} kb={svc.deps.kb_version}")  # noqa: T201
    for jid, p in picks.items():
        ok = "ok" if p.reached == JOURNEYS[jid]["expected"] else "UNEXPECTED"
        line = f"  {jid}: case={p.case_id} similarity={p.similarity} present={p.n_present}"
        print(f"{line} -> {p.reached} [{ok}]")  # noqa: T201
    return 0 if all(p.reached == JOURNEYS[j]["expected"] for j, p in picks.items()) else 1


def replay() -> int:
    """Re-run every journey offline (replay mode, recorded embeddings) and compare to the files."""
    svc, _ = _service("replay", record=False)
    docs, _ = run_all(svc, "replay")
    bad = 0
    for jid, doc in docs.items():
        want = fingerprint(load_demo(jid))
        got = fingerprint(doc)
        same = want == got
        bad += 0 if same else 1
        verdict = "reproduced" if same else "DIFFERS"
        print(f"demo-replay {jid}: {verdict} ({len(got)} steps, final {doc['final_phase']})")  # noqa: T201
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(record() if (sys.argv[1:] or ["record"])[0] == "record" else replay())
