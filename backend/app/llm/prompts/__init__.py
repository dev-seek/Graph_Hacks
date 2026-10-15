"""Versioned prompt files `<task>.v<N>.md` (spec §10.4): a stable system block, no variable text."""

from __future__ import annotations

from pathlib import Path

DIR = Path(__file__).parent


def load_prompt(task: str) -> str:
    found = sorted(DIR.glob(f"{task}.v*.md"))
    if not found:
        raise FileNotFoundError(f"no prompt file for task {task}")
    return found[-1].read_text(encoding="utf-8").strip()
