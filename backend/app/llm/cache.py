"""Record/replay cache (spec §10.7): key = (task, prompt version, schema hash, input hash)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel

from app.llm.settings import CACHE_DIR

_WS = re.compile(r"\s+")
PROMPTS_DIR = Path(__file__).parent / "prompts"


def prompt_version(task: str) -> str:
    """`<task>.v<N>.md` with the highest N present; 'v0' if the task has no prompt file."""
    found = sorted(PROMPTS_DIR.glob(f"{task}.v*.md"))
    return found[-1].name.split(".")[1] if found else "v0"


def schema_hash(schema: type[BaseModel]) -> str:
    blob = json.dumps(schema.model_json_schema(), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:12]


def normalise(text: str) -> str:
    return _WS.sub(" ", text).strip().lower()


def cache_key(task: str, schema: type[BaseModel], input_text: str) -> str:
    blob = f"{task}|{prompt_version(task)}|{schema_hash(schema)}|{normalise(input_text)}"
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


class LLMCache:
    def __init__(self, root: Path = CACHE_DIR) -> None:
        self.root = root

    def _path(self, task: str, key: str) -> Path:
        return self.root / task / f"{key}.json"

    def get(self, task: str, key: str) -> dict[str, object] | None:
        p = self._path(task, key)
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))["output"]

    def put(self, task: str, key: str, output: BaseModel) -> None:
        p = self._path(task, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        doc = {"task": task, "key": key, "output": output.model_dump(mode="json")}
        p.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
