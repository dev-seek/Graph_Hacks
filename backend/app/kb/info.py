"""KbInfo: the record of which knowledge-base release is loaded (written by `make kb`, P1)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

KB_INFO_PATH = Path(__file__).resolve().parents[3] / "data" / "derived" / "kb_info.json"


class KbInfo(BaseModel):
    release: str
    hpo_version: str
    hpoa_version: str
    embedding_model: str | None = None


def load_kb_info(path: Path = KB_INFO_PATH) -> KbInfo | None:
    """Return the KbInfo written by the kb build, or None when no kb has been built."""
    if not path.exists():
        return None
    return KbInfo.model_validate(json.loads(path.read_text(encoding="utf-8")))
