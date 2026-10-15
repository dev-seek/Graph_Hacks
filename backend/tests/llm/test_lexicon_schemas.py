import pytest
from pydantic import ValidationError

from app.llm.lexicon import is_clean, violations
from app.llm.schemas import ExtractedItem, Rephrase, StoryExtraction


@pytest.mark.parametrize(
    "text",
    [
        "Does he tire quickly when he plays?",
        "Has she had many chest infections?",
        "Is his head small?",
    ],
)
def test_plain_questions_are_clean(text: str) -> None:
    assert is_clean(text)


@pytest.mark.parametrize(
    "text",
    [
        "Could this be hypothyroidism?",
        "Does he have Down's syndrome?",
        "There is a 30% chance",
        "Has he been diagnosed with anything?",
        "Any sign of autism?",
        "Is he a carrier?",
    ],
)
def test_diagnostic_wording_is_flagged(text: str) -> None:
    assert violations(text)


def test_label_and_sentence_limits() -> None:
    with pytest.raises(ValidationError):
        ExtractedItem(
            quote="x", plain_label="one two three four five six seven eight nine", status="present"
        )
    with pytest.raises(ValidationError):
        Rephrase(question=" ".join(["w"] * 21), why="ok")
    with pytest.raises(ValidationError):
        StoryExtraction(items=[ExtractedItem(quote="x", plain_label="x", status="present")] * 26)
    with pytest.raises(ValidationError):
        ExtractedItem(quote="x", plain_label="x", status="present", hpo_guess=["a", "b", "c", "d"])
