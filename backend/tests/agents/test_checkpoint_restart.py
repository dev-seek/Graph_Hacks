"""Integration: LangGraph interrupt + Command(resume) survive a real process restart (task 1)."""

from __future__ import annotations

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

WORKER = Path(__file__).parent / "restart_worker.py"


def _run(mode: str, thread: str) -> str:
    out = subprocess.run(  # noqa: S603 (fixed argv, our own worker script)
        [sys.executable, str(WORKER), mode, thread],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return out.stdout


def test_interrupt_resumes_in_a_fresh_process() -> None:
    thread = f"family_{uuid.uuid4().hex[:8]}"
    assert "PENDING ('ask',) question-1" in _run("start", thread)
    resumed = _run("resume", thread)
    assert "FOUND ('ask',) question-1" in resumed
    assert "DONE yes" in resumed


def test_real_agent_resumes_in_a_second_process() -> None:
    import json

    from tests.conftest import _kb_ready

    if not _kb_ready():
        pytest.skip("needs the built kb")
    worker = Path(__file__).parent / "restart_family_worker.py"

    def run(*args: str) -> dict[str, object]:
        out = subprocess.run(  # noqa: S603 (fixed argv, our own worker script)
            [sys.executable, str(worker), *args],
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
            env={**__import__("os").environ, "PYTHONPATH": f"backend:{Path.cwd()}/backend"},
        )
        return json.loads(out.stdout.strip().splitlines()[-1])

    a = run("start")
    b = run("finish", str(a["fid"]), str(a["token"]), json.dumps(a["ids"]))
    assert b["findings"] == ["HP:0030051"] and b["phase"] in ("questions", "watching")
