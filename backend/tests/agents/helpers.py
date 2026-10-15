"""Shared helpers for agent tests: a scripted 'good LLM' and a simulated parent from a dev case."""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.adapters.fake import FakeAdapter
from app.llm.schemas import DocExtraction, DocItem, ExtractedItem, StoryExtraction


class NoEmbedder:
    """Forces full-text-only resolution (and proves the offline path works)."""

    dim = 384
    model_id = "none"

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("no embedding model in tests")


def scripted_llm(names: dict[str, tuple[str, str]]) -> FakeAdapter:
    """`names`: phrase -> (HPO id, source). The 'model' finds phrases and guesses their ids."""

    def extract(text: str) -> StoryExtraction:
        items: list[ExtractedItem] = []
        for phrase, (hid, _) in names.items():
            if f"No {phrase}" in text:
                items.append(
                    ExtractedItem(
                        quote=f"No {phrase}",
                        plain_label=phrase[:40],
                        status="absent",
                        hpo_guess=[hid],
                    )
                )
            elif phrase in text:
                items.append(
                    ExtractedItem(
                        quote=phrase, plain_label=phrase[:40], status="present", hpo_guess=[hid]
                    )
                )
        return StoryExtraction(items=items)

    def read(text: str) -> DocExtraction:
        items: list[DocItem] = []
        for phrase, (hid, source) in names.items():
            src = "lab_or_test" if source == "test" else "doctor_exam"
            if f"No {phrase}" in text:
                items.append(
                    DocItem(
                        quote=f"No {phrase}",
                        plain_label=phrase[:40],
                        status="absent",
                        hpo_guess=[hid],
                        source=src,
                    )
                )
            elif phrase in text:
                items.append(
                    DocItem(
                        quote=phrase,
                        plain_label=phrase[:40],
                        status="present",
                        hpo_guess=[hid],
                        source=src,
                    )
                )
        return DocExtraction(items=items)

    handlers: dict[str, object] = {"extract_story": extract, "read_document": read}
    return FakeAdapter(handlers)  # type: ignore[arg-type]


_ = BaseModel
