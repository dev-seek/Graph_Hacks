"""'Ask the centre': the model only picks a whitelisted template; keywords are the fallback."""

from __future__ import annotations

from typing import Any, cast

import pytest

from app.centre.service import CentreService, keyword_pick, validate_choice
from app.llm.adapters.fake import FakeAdapter
from app.llm.router import LLMRouter
from app.llm.schemas import TemplateChoice


def _service(handler: Any = None) -> CentreService:
    adapter = FakeAdapter({"centre_template_pick": handler} if handler else {})
    router = LLMRouter(mode="fake", adapter=adapter)
    return CentreService(cast(Any, None), lambda _n: cast(Any, None), router)


@pytest.mark.parametrize(
    ("question", "template", "params"),
    [
        ("Who should take C-042 and which test?", "route_case", {"case_id": "C-042"}),
        ("which signs connect different groups?", "bridges", {}),
        ("show the clusters", "clusters", {}),
        ("what is the fastest protocol", "protocols", {}),
        ("who manages the most cases", "workload", {}),
        ("hello", "overview", {}),
    ],
)
def test_keyword_fallback(question: str, template: str, params: dict[str, str]) -> None:
    c = keyword_pick(question)
    assert (c.template_id, c.params) == (template, params)
    validate_choice(c)


@pytest.mark.parametrize(
    "choice",
    [
        TemplateChoice(template_id="MATCH (n) DETACH DELETE n"),
        TemplateChoice(template_id="route_case", params={}),
        TemplateChoice(template_id="route_case", params={"case_id": "C-1; DROP"}),
        TemplateChoice(template_id="overview", params={"x": "y"}),
    ],
)
def test_validate_rejects_non_whitelisted(choice: TemplateChoice) -> None:
    with pytest.raises(ValueError):  # noqa: PT011
        validate_choice(choice)


def test_valid_model_choice_is_used() -> None:
    svc = _service(lambda _t: TemplateChoice(template_id="bridges"))
    choice, source = svc.pick("anything")
    assert (choice.template_id, source) == ("bridges", "llm")


def test_invalid_model_choice_falls_back_to_keywords() -> None:
    svc = _service(lambda _t: TemplateChoice(template_id="route_case", params={"case_id": "x"}))
    choice, source = svc.pick("show the clusters")
    assert (choice.template_id, source) == ("clusters", "fallback")


def test_no_model_uses_keywords() -> None:
    svc = _service()  # fake adapter has no default for this task -> fallback
    choice, source = svc.pick("fastest protocol?")
    assert (choice.template_id, source) == ("protocols", "fallback")
