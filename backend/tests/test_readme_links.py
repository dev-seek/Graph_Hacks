"""README hygiene: every relative link points at a file that exists; no stray email address."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def _targets() -> list[str]:
    links = re.findall(r"\]\(([^)\s]+)\)", README)
    return [x for x in links if not x.startswith(("http://", "https://", "#", "mailto:"))]


def test_relative_links_exist() -> None:
    glob_ok = {"backend/app/graph/queries"}  # directory links
    missing = [
        t
        for t in _targets()
        if not (ROOT / t.split("#")[0]).exists() and t.split("#")[0] not in glob_ok
    ]
    assert missing == [], missing


def test_readme_names_no_email_and_keeps_honest_lines() -> None:
    assert not re.search(r"[\w.]+@[\w.]+\.\w+", README)
    assert "do not beat" in README.lower()
    assert "not measured" in README.lower()
