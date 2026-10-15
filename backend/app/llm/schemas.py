"""LLM output schemas (spec §10.10). JSON Schema has no length bounds: limits are validators."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_ITEMS = 25
MAX_GUESSES = 3
MAX_LABEL_WORDS = 8
MAX_SENTENCE_WORDS = 20


def _words(text: str) -> int:
    return len(text.split())


class ExtractedItem(BaseModel):
    quote: str = Field(description="Exact substring of the input")
    plain_label: str = Field(description="At most 8 words, parent-friendly")
    status: Literal["present", "absent"]
    onset_text: str | None = None
    hpo_guess: list[str] = Field(default_factory=list, description="At most 3 HPO ids")

    @field_validator("plain_label")
    @classmethod
    def _label_short(cls, v: str) -> str:
        if not v.strip() or _words(v) > MAX_LABEL_WORDS:
            raise ValueError(f"plain_label must be 1-{MAX_LABEL_WORDS} words")
        return v.strip()

    @field_validator("hpo_guess")
    @classmethod
    def _few_guesses(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_GUESSES:
            raise ValueError(f"at most {MAX_GUESSES} hpo_guess ids")
        return v


class StoryExtraction(BaseModel):
    items: list[ExtractedItem]

    @field_validator("items")
    @classmethod
    def _cap(cls, v: list[ExtractedItem]) -> list[ExtractedItem]:
        if len(v) > MAX_ITEMS:
            raise ValueError(f"at most {MAX_ITEMS} items")
        return v


class DocItem(ExtractedItem):
    source: Literal["doctor_exam", "lab_or_test"]
    date_text: str | None = None


class DocExtraction(BaseModel):
    items: list[DocItem]

    @field_validator("items")
    @classmethod
    def _cap(cls, v: list[DocItem]) -> list[DocItem]:
        if len(v) > MAX_ITEMS:
            raise ValueError(f"at most {MAX_ITEMS} items")
        return v


class Rephrase(BaseModel):
    question: str
    why: str

    @field_validator("question", "why")
    @classmethod
    def _short(cls, v: str) -> str:
        if not v.strip() or _words(v) > MAX_SENTENCE_WORDS:
            raise ValueError(f"1-{MAX_SENTENCE_WORDS} words required")
        return v.strip()


class ReferralDraft(BaseModel):
    """Template-constrained letter: fixed sections, free text only inside them."""

    reason_for_referral: str
    history_summary: str
    findings_present: list[str]
    findings_absent: list[str]
    suggested_tests: list[str]
    closing: str


class SafetyConcern(BaseModel):
    quote: str
    level: Literal["URGENT_SOON", "EMERGENCY"]
    why: str


class SafetyConcerns(BaseModel):
    """Add-only: the safety engine accepts a concern only if its quote occurs in the text."""

    concerns: list[SafetyConcern] = Field(default_factory=list[SafetyConcern])


class TemplateChoice(BaseModel):
    template_id: str
    params: dict[str, str] = Field(default_factory=dict)


class TermLabelItem(BaseModel):
    id: str
    cx_plain_label: str
    cx_question: str
    cx_why: str
    cx_how_to_check: str


class TermLabels(BaseModel):
    labels: list[TermLabelItem]


TASK_SCHEMAS: dict[str, type[BaseModel]] = {
    "extract_story": StoryExtraction,
    "read_document": DocExtraction,
    "phrase_question": Rephrase,
    "draft_referral": ReferralDraft,
    "safety_extra": SafetyConcerns,
    "centre_template_pick": TemplateChoice,
    "label_terms": TermLabels,
}
