"""Tuned engine values from config/engine.yaml (ADRs 0003-0006)."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.engine.gates import Taus
from app.engine.scoring import Params

PATH = Path(__file__).resolve().parents[3] / "config" / "engine.yaml"


def _load(path: Path = PATH) -> dict[str, dict[str, object]]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def tuned_params(path: Path = PATH) -> Params:
    return Params(**_load(path)["scoring"])  # type: ignore[arg-type]


def tuned_taus(path: Path = PATH) -> Taus:
    return Taus(**_load(path)["taus"])  # type: ignore[arg-type]
