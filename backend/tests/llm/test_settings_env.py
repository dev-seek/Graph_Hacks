"""`LLM_MODE=off` must load: YAML 1.1 reads an unquoted `off` as False (found in P4 e2e)."""

from __future__ import annotations

import pytest

from app.llm.settings import load_settings


@pytest.mark.parametrize("mode", ["off", "fake", "replay", "record", "live"])
def test_every_mode_loads_from_env(mode: str) -> None:
    assert load_settings(env={"LLM_MODE": mode}).mode == mode


def test_default_mode_is_replay() -> None:
    assert load_settings(env={}).mode == "replay"
