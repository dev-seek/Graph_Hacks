"""Intake: free text -> confirm list (spec §9 `intake` / `doc_reader`).

The LLM proposes quoted observations; FalkorDB (Q0 full-text + vector) decides the HPO term. Every
quote must occur verbatim in the input (prompt-injection defence, spec §10.9). Without an LLM the
clause-split fallback proposes the same shape and the parent confirms or edits.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from app.agents.deps import AgentDeps
from app.agents.reasoning import term_names
from app.llm.fallbacks import clause_items
from app.llm.router import LLMResult
from app.llm.schemas import DocExtraction, DocItem, ExtractedItem, StoryExtraction

MAX_PENDING = 25
_NUM = re.compile(r"(\d+(?:\.\d+)?)\s*(month|mo|year|yr|week|wk|/12)", re.IGNORECASE)
_BIRTH = re.compile(r"\b(birth|born|newborn|as a baby|infan)", re.IGNORECASE)


@dataclass
class PendingItem:
    id: str
    term_id: str
    term_name: str
    plain_label: str
    status: str
    quote: str
    start: int
    end: int
    onset_months: float | None = None
    source: str = "parent_story"
    via: list[str] = field(default_factory=list[str])

    def as_dict(self) -> dict[str, object]:
        return self.__dict__.copy()


def parse_onset(text: str | None) -> float | None:
    """'at about 14 months' -> 14.0; '2 years' -> 24.0; 'as a baby' -> 0.0; else None."""
    if not text:
        return None
    m = _NUM.search(text)
    if m:
        n, unit = float(m.group(1)), m.group(2).lower()
        if unit in ("month", "mo", "/12"):
            return n
        if unit in ("year", "yr"):
            return n * 12
        return n / 4.345
    return 0.0 if _BIRTH.search(text) else None


def _check_quotes(items: list[ExtractedItem] | list[DocItem], text: str) -> None:
    for it in items:
        if it.quote not in text:
            raise ValueError(f"quote is not an exact substring of the input: {it.quote!r}")


def validate_story(out: StoryExtraction, text: str) -> None:
    _check_quotes(out.items, text)


def validate_doc(out: DocExtraction, text: str) -> None:
    _check_quotes(out.items, text)


def fallback_story(text: str) -> StoryExtraction:
    items = [
        ExtractedItem(quote=i["quote"], plain_label=i["plain_label"], status=i["status"])
        for i in clause_items(text)
    ]
    return StoryExtraction(items=items)


def fallback_doc(text: str) -> DocExtraction:
    items = [
        DocItem(
            quote=i["quote"], plain_label=i["plain_label"], status=i["status"], source="doctor_exam"
        )
        for i in clause_items(text)
    ]
    return DocExtraction(items=items)


def extract_story(deps: AgentDeps, text: str, family_id: str) -> LLMResult[StoryExtraction]:
    return deps.router.run(
        "extract_story",
        text,
        StoryExtraction,
        lambda: fallback_story(text),
        validate=lambda o: validate_story(o, text),
        family_id=family_id,
    )


def extract_document(deps: AgentDeps, text: str, family_id: str) -> LLMResult[DocExtraction]:
    return deps.router.run(
        "read_document",
        text,
        DocExtraction,
        lambda: fallback_doc(text),
        validate=lambda o: validate_doc(o, text),
        family_id=family_id,
    )


def resolve_items(
    deps: AgentDeps,
    text: str,
    items: list[ExtractedItem] | list[DocItem],
    id_prefix: str,
) -> list[PendingItem]:
    """Resolve each quote to an HPO term through the graph; keep one entry per (term, status)."""
    guess_ids = sorted({g for it in items for g in it.hpo_guess})
    known: set[str] = set(term_names(deps, guess_ids)) if guess_ids else set()
    out: list[PendingItem] = []
    seen: set[tuple[str, str]] = set()
    for idx, it in enumerate(items[:MAX_PENDING]):
        hits = deps.resolver.resolve(it.quote, k=3)
        term = hits[0] if hits else None
        guess = next((g for g in it.hpo_guess if g in known), None)
        if term is None and guess is None:
            continue  # nothing in the graph matches: the parent can add it by hand later
        term_id = guess if (guess and (term is None or guess in {h.id for h in hits})) else None
        if term_id is None:
            assert term is not None  # noqa: S101
            term_id = term.id
        key = (term_id, it.status)
        if key in seen:
            continue
        seen.add(key)
        name = (
            term.name
            if term is not None and term.id == term_id
            else term_names(deps, [term_id]).get(term_id, term_id)
        )
        start = text.find(it.quote)
        out.append(
            PendingItem(
                id=f"{id_prefix}{idx}",
                term_id=term_id,
                term_name=name,
                plain_label=it.plain_label,
                status=it.status,
                quote=it.quote,
                start=max(start, 0),
                end=max(start, 0) + len(it.quote),
                onset_months=parse_onset(it.onset_text),
                source=getattr(it, "source", "parent_story"),
                via=term.via if term is not None else ["llm_guess"],
            )
        )
    return out


def pending_json(items: list[PendingItem]) -> str:
    return json.dumps([i.as_dict() for i in items])
