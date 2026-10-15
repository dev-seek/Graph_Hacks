"""Spike worker: run as `python spike_restart.py start|resume <thread>` (two separate processes)."""

from __future__ import annotations

import os
import sys
from typing import Any, TypedDict

from langchain_falkordb.checkpoint import FalkorDBSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


class S(TypedDict, total=False):
    pending: str
    answer: str


def build() -> Any:
    def make(s: S) -> S:
        return {"pending": "question-1"}

    def ask(s: S) -> S:
        return {"answer": interrupt(s["pending"])}

    g = StateGraph(S)
    g.add_node("make", make)
    g.add_node("ask", ask)
    g.add_edge(START, "make")
    g.add_edge("make", "ask")
    g.add_edge("ask", END)
    saver = FalkorDBSaver(
        host=os.environ.get("FALKORDB_HOST") or "localhost",
        port=int(os.environ.get("FALKORDB_PORT") or 6379),
        database="langgraph_checkpoints_spike",
    )
    return g.compile(checkpointer=saver)


if __name__ == "__main__":
    mode, thread = sys.argv[1], sys.argv[2]
    cfg: Any = {"configurable": {"thread_id": thread}}
    app = build()
    if mode == "start":
        app.invoke({}, cfg)
        st = app.get_state(cfg)
        print("PENDING", st.next, st.tasks[0].interrupts[0].value)
    else:
        st = app.get_state(cfg)
        print("FOUND", st.next, st.tasks[0].interrupts[0].value)
        out = app.invoke(Command(resume="yes"), cfg)
        print("DONE", out.get("answer"), len(list(app.checkpointer.list(cfg, limit=5))))  # type: ignore[union-attr]
