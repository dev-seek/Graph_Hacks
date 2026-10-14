"""API contract tests (spec §12): parent responses never carry condition language."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.api import schemas as s
from app.api.schemas import CLINICIAN_MODELS, PARENT_MODELS

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = (
    "disease",
    "diagnosis",
    "candidate",
    "probability",
    "rank",
    "posterior",
    "ranking",
    "score",
    "likelihood",
    "rare_mass",
    "omim",
    "orpha",
)


def forbidden_keys(obj: Any, path: str = "") -> list[str]:
    """Recursively find any dict key (or schema property name) containing a forbidden word."""
    bad: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():  # pyright: ignore[reportUnknownVariableType]
            key = str(k).lower()  # pyright: ignore[reportUnknownArgumentType]
            if any(word in key for word in FORBIDDEN):
                bad.append(f"{path}/{k}")
            bad += forbidden_keys(v, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]
            bad += forbidden_keys(v, f"{path}[{i}]")
    return bad


def _property_names(model: type[BaseModel]) -> list[str]:
    schema = model.model_json_schema()
    names: list[str] = []
    for definition in [schema, *schema.get("$defs", {}).values()]:
        names += list(definition.get("properties", {}))
    return names


def test_parent_schemas_have_no_condition_language() -> None:
    for model in PARENT_MODELS:
        bad = [n for n in _property_names(model) if any(w in n.lower() for w in FORBIDDEN)]
        assert not bad, f"{model.__name__}: {bad}"


def test_clinician_models_do_carry_candidates_and_disclaimer() -> None:
    assert "candidates" in _property_names(s.ClinicianView)
    assert s.ClinicianView.model_fields["disclaimer"].default == s.CLINICIAN_DISCLAIMER
    assert CLINICIAN_MODELS


def test_recursive_check_catches_nested_forbidden_keys() -> None:
    assert forbidden_keys({"a": [{"b": {"Disease_name": 1}}]}) == ["/a[0]/b/Disease_name"]
    assert forbidden_keys({"findings": [{"plain_label": "x"}]}) == []


def test_parent_example_payloads_are_clean() -> None:
    state = s.ParentState(
        phase="questions",
        round_no=1,
        next_step=s.ParentNextStep(kind="answer_questions", label="Answer 4 short questions"),
    )
    pack = s.ParentPack(
        clinician_code="ABCD-1234",
        child_age_months=30,
        summary="Delayed walking; frequent falls.",
        findings=[
            s.ParentFindingView(
                id="f1", plain_label="Falls often", status="present", source="parent_story"
            )
        ],
        checks_to_ask_about=["Muscle strength"],
        questions_for_doctor=["Could a specialist look at this?"],
        generated_at="2026-10-15T00:00:00Z",
    )
    for model in (state, pack):
        assert forbidden_keys(json.loads(model.model_dump_json())) == []
    assert s.PARENT_DISCLAIMER.startswith("Constellation does not diagnose")


def test_story_limits() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        s.ParentStoryIn(text="x" * 4001, child_age_months=12)
    with pytest.raises(ValidationError):
        s.ParentStoryIn(text="ok", child_age_months=241)


def test_openapi_is_complete_and_exported_file_is_current() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from export_openapi import OUT, render

    spec = json.loads(render())
    paths = spec["paths"]
    for p in (
        "/api/families",
        "/api/families/{family_id}/story",
        "/api/families/{family_id}/round/{n}/answers",
        "/api/clinician/{family_id}/phenopacket",
        "/api/centre/whatif",
        "/api/debug/queries",
        "/api/health",
    ):
        assert p in paths, p
    assert OUT.exists() and OUT.read_text() == render(), (
        "run: uv run python scripts/export_openapi.py"
    )


def test_parent_routes_responses_have_no_forbidden_keys_in_openapi() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from export_openapi import render

    spec = json.loads(render())
    parent_schemas = {m.__name__ for m in PARENT_MODELS}
    defs = spec["components"]["schemas"]
    for name in parent_schemas:
        props = json.dumps(defs[name].get("properties", {})).lower()
        assert not any(f'"{w}' in props for w in ("disease", "candidate", "posterior")), name
