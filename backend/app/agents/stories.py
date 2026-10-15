"""Parse `review/demo_stories.md` (REVIEWED input, read-only) into story records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

PATH = Path(__file__).resolve().parents[3] / "review" / "demo_stories.md"


@dataclass(frozen=True)
class DemoStory:
    name: str
    age_months: int
    story: str
    negatives_case: str | None


def load_stories(path: Path = PATH) -> dict[str, DemoStory]:
    text = path.read_text(encoding="utf-8")
    out: dict[str, DemoStory] = {}
    for block in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        name = block.splitlines()[0].strip()
        age = re.search(r"- age_months:\s*(\d+)", block)
        neg = re.search(r"- negatives_case:\s*(\w+)", block)
        story = re.search(r"- story: \|\n((?:  .*\n?)+)", block)
        if not (age and story):
            continue
        body = " ".join(line.strip() for line in story.group(1).splitlines())
        out[name] = DemoStory(name, int(age.group(1)), body, neg.group(1) if neg else None)
    return out


LETTERS = Path(__file__).resolve().parents[3] / "review" / "doctor_letters.md"


def load_letters(path: Path = LETTERS) -> dict[int, str]:
    """Letter number -> body text (from `## Letter N` sections of the REVIEWED file)."""
    text = path.read_text(encoding="utf-8")
    out: dict[int, str] = {}
    for m in re.finditer(
        r"^## Letter (\d+)[^\n]*\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL
    ):
        out[int(m.group(1))] = m.group(2).strip()
    return out
