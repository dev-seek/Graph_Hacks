"""Rules-only `cx_*` labels for HPO terms (spec §8.2). HPO content itself is never altered:
these are our own separate properties. An optional LLM pass (`label_terms`) may override them."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel

TEST_WORDS = (
    "level", "concentration", "serum", "plasma", "urine", "mri", "eeg", "emg", "ecg", "biopsy",
    "histolog", "imaging", "radiograph", "x-ray", "ultrasound", "karyotype", "enzyme activity",
)  # fmt: skip
TEST_ANCESTORS = (
    "Abnormality of blood and blood-forming tissues",
    "Abnormality of metabolism/homeostasis",
)
HOME_WORDS = ("fatigue", "pallor", "bruising", "jaundice", "bleeding")
EXAM_WORDS = (
    "head circumference", "stature", "height", "weight", "blood pressure", "murmur", "reflex",
    "muscle tone", "hypotonia", "hypertonia", "hepatomegaly", "splenomegaly", "scoliosis",
    "palate", "dysmorphi", "macrocephaly", "microcephaly",
)  # fmt: skip
AGE_RULES: tuple[tuple[int, tuple[str, ...]], ...] = (
    (108, ("puberty", "pubertal", "menarche", "breast development")),
    (60, ("reading", "school", "learning", "academic")),
    (12, ("walking", "gait", "running", "jump")),
)
_LEADING = re.compile(r"^(abnormality of the |abnormality of |abnormal )", re.IGNORECASE)
MAX_LABEL_WORDS = 8


class TermLabel(BaseModel):
    cx_obs: Literal["home", "exam", "test"]
    cx_min_age_months: int
    cx_plain_label: str
    cx_question: str
    cx_why: str
    cx_how_to_check: str
    cx_lay_text: str
    cx_label_source: Literal["rules"] = "rules"


def _obs(lowered: str, ancestor_names: set[str]) -> Literal["home", "exam", "test"]:
    if any(w in lowered for w in TEST_WORDS):
        return "test"
    if any(a in ancestor_names for a in TEST_ANCESTORS) and not any(
        w in lowered for w in HOME_WORDS
    ):
        return "test"
    if any(w in lowered for w in EXAM_WORDS):
        return "exam"
    return "home"


def _min_age(lowered: str) -> int:
    for months, words in AGE_RULES:
        if any(w in lowered for w in words):
            return months
    return 0


def _plain_label(name: str, lay: list[str]) -> str:
    usable = [s.strip() for s in lay if s.strip() and len(s.split()) <= MAX_LABEL_WORDS]
    if usable:
        return min(usable, key=lambda s: (len(s.split()), len(s), s.lower()))
    base = _LEADING.sub("", name.strip()).lower() or name.strip().lower()
    return " ".join(base.split()[:MAX_LABEL_WORDS])


def _lay_text(lay: list[str], plain: str) -> str:
    seen: set[str] = set()
    parts: list[str] = []
    for s in [*lay, plain]:
        s = s.strip()
        if s and s.lower() not in seen:
            seen.add(s.lower())
            parts.append(s)
    return " | ".join(parts)


def rule_label(name: str, lay_synonyms: list[str], ancestor_names: set[str]) -> TermLabel:
    lowered = name.lower()
    obs = _obs(lowered, ancestor_names)
    plain = _plain_label(name, lay_synonyms)
    if obs == "test":
        question = f"Has a test shown {plain}?"
        why = "A past test or scan result can help point to the right specialist."
        how = "Look in test letters or results, or ask the clinic that did the test."
    elif obs == "exam":
        question = f"Has a doctor or nurse told you about {plain} in your child?"
        why = "Something a doctor can see or measure can help narrow down the cause."
        how = "A doctor or nurse can check this at an appointment; it may be in clinic letters."
    else:
        question = f"Have you noticed {plain} in your child?"
        why = "This is a sign that doctors ask about when looking for a cause."
        how = "Think about the last few weeks; if unsure, say so and watch for it."
    return TermLabel(
        cx_obs=obs,
        cx_min_age_months=_min_age(lowered),
        cx_plain_label=plain,
        cx_question=question,
        cx_why=why,
        cx_how_to_check=how,
        cx_lay_text=_lay_text(lay_synonyms, plain),
    )
