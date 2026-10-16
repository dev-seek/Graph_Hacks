"""Real agent in two processes: `start` shares a story, `finish` confirms it (run separately)."""

from __future__ import annotations

import json
import sys

from langchain_falkordb.checkpoint import FalkorDBSaver

from app.agents.deps import AgentDeps
from app.agents.service import FamilyService
from app.llm.router import LLMRouter
from tests.agents.helpers import NoEmbedder, scripted_llm

TIPTOE = {"walked on tiptoes for a few months": ("HP:0030051", "home")}


def service() -> FamilyService:
    router = LLMRouter(mode="fake", adapter=scripted_llm(TIPTOE))
    deps = AgentDeps.build(router=router, embedder=NoEmbedder())
    return FamilyService(deps, FalkorDBSaver(database="langgraph_checkpoints_test"))


if __name__ == "__main__":
    svc = service()
    if sys.argv[1] == "start":
        fid, token = svc.create_family()
        out = svc.submit_story(fid, "He walked on tiptoes for a few months.", 30, "male")
        print(
            json.dumps(
                {"fid": fid, "token": token, "ids": [i.id for i in out.extraction_to_confirm]}
            )
        )
    else:
        fid, token, ids = sys.argv[2], sys.argv[3], json.loads(sys.argv[4])
        assert svc.authenticate(fid, token)
        st = svc.confirm(fid, ids, [], [])
        findings = [f.term_id for f in svc.deps.repo(fid).findings()]
        print(json.dumps({"phase": st.phase, "findings": findings}))
