"""Load `config/llm.yaml` (spec §10.3): `${VAR:-default}` substitution, typed profiles."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PATH = ROOT / "config" / "llm.yaml"
CACHE_DIR = ROOT / "data" / "llm_cache"
Mode = Literal["off", "fake", "replay", "record", "live"]
_VAR = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}")


class AdvisorCfg(BaseModel):
    model: str
    max_uses: int = 1
    max_tokens: int = 2048


class Profile(BaseModel):
    model: str
    max_output_tokens: int
    advisor: AdvisorCfg | None = None
    batch: bool = False


class Budget(BaseModel):
    per_family_tokens: int = 60000
    daily_usd: float = 5.0


class LLMSettings(BaseModel):
    mode: Mode = "replay"
    profiles: dict[str, Profile]
    candidates: dict[str, list[str]] = Field(default_factory=dict)
    chosen: dict[str, str] = Field(default_factory=dict)  # written by `make llm-contract`
    prompt_cache: bool = True
    embeddings: dict[str, str] = Field(default_factory=dict)
    budget: Budget = Budget()
    timeout_s: float = 30.0
    prices_usd_per_mtok: dict[str, tuple[float, float]] = Field(default_factory=dict)

    def profile_for(self, task: str) -> Profile:
        name = self.chosen.get(task) or (self.candidates.get(task) or ["fast"])[0]
        return self.profiles[name]

    def profile_name_for(self, task: str) -> str:
        return self.chosen.get(task) or (self.candidates.get(task) or ["fast"])[0]


def substitute(raw: str, env: dict[str, str] | None = None) -> str:
    e = os.environ if env is None else env

    def repl(m: re.Match[str]) -> str:
        return e.get(m.group(1)) or (m.group(2) or "")

    return _VAR.sub(repl, raw)


def load_settings(path: Path = DEFAULT_PATH, env: dict[str, str] | None = None) -> LLMSettings:
    data = yaml.safe_load(substitute(path.read_text(encoding="utf-8"), env))
    return LLMSettings.model_validate(data)
