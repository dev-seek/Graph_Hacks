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
    out = subprocess.run(
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
