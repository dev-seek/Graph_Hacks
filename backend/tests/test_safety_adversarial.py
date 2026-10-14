"""Held-out recall/precision checks, written independently of the rule patterns."""

import pytest

from app.safety.rules import load_rule_file, match

RF = load_rule_file()

MUST_FLAG: list[tuple[str, str, int | None]] = [
    ("She had a fit for 10 minutes", "seizure_long_or_repeated", None),
    (
        "He was fitting in the night and it lasted ages, 15 minutes at least",
        "seizure_long_or_repeated",
        None,
    ),
    ("He had a seizure. It lasted 10 minutes.", "seizure_long_or_repeated", None),
    ("She was seizing and would not stop", "seizure_long_or_repeated", None),
    ("She's not sleeping and says she wants to die", "teen_self_harm", 190),
    ("He says he doesn’t want to be here any more, no reason to live", "teen_self_harm", 200),
    (
        "Vomiting and not keeping fluids down, hardly any wet nappies",
        "severe_dehydration_infant",
        10,
    ),
    (
        "Loose motions since yesterday and he has not passed urine all day",
        "severe_dehydration_infant",
        14,
    ),
    ("Hit her head and seemed fine, but now she's vomiting and drowsy", "severe_head_injury", None),
    ("Took all her daily tablets at once", "poisoning", None),
    ("His face went blue and he was gasping", "breathing_difficulty", None),
    ("Baby has a temperature of 38.5C", "fever_under_3_months", 1),
    ("Baby is 100.4F and fussy", "fever_under_3_months", 2),
    ("She won’t wake up, hard to rouse", "unresponsive", None),
    ("The rash doesn’t fade when pressed and she has a fever", "nonblanching_rash_fever", None),
]

MUST_NOT_FLAG: list[tuple[str, int | None]] = [
    ("She has had no seizures and no fits", None),
    ("He is fit for school and sport", None),
    ("The trousers don't fit him", None),
    ("She had a rash that fades when I press it", None),
    ("My 3 year old has a fever and a cough", 36),
    ("Medicine given as prescribed this morning", None),
    ("He is not suicidal, he just failed a test", 180),
    ("She has no bruises", None),
]


@pytest.mark.parametrize(("text", "rule_id", "age"), MUST_FLAG)
def test_must_flag(text: str, rule_id: str, age: int | None) -> None:
    assert rule_id in [h.rule_id for h in match(RF.rules, text, age)]


@pytest.mark.parametrize(("text", "age"), MUST_NOT_FLAG)
def test_must_not_flag(text: str, age: int | None) -> None:
    assert not match(RF.rules, text, age)


def test_no_unbounded_wildcards_in_negations() -> None:
    for rule in RF.rules:
        for n in rule.negations:
            assert ".*" not in n and ".+" not in n, (rule.id, n)
