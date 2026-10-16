from __future__ import annotations

import pytest

from app.agents.phrasing import lower_first, tidy_question

_NOTICED = "Have you noticed "
_DOCTOR = "Has a doctor or nurse told you about "


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (_NOTICED + "Farsightedness in your child?", _NOTICED + "farsightedness in your child?"),
        ("Has a test shown Hypotonia?", "Has a test shown hypotonia?"),
        (_DOCTOR + "Heart murmur in your child?", _DOCTOR + "heart murmur in your child?"),
        (_NOTICED + "ADHD in your child?", _NOTICED + "ADHD in your child?"),
        (_NOTICED + "a squint in your child?", _NOTICED + "a squint in your child?"),
        ("Does he sleep well?", "Does he sleep well?"),
    ],
)
def test_tidy_question(raw: str, expected: str) -> None:
    assert tidy_question(raw) == expected


def test_lower_first_keeps_acronyms() -> None:
    assert lower_first("Muscle strength") == "muscle strength"
    assert lower_first("EEG changes") == "EEG changes"
    assert lower_first("") == ""
