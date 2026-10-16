"""Question text for a round: pre-written `cx_question`, optionally rephrased for the child's age.

The rephrase is accepted only if it passes the lexicon (no disease-flavoured words, spec §10.9).
"""

from __future__ import annotations

import json
import re

from app.agents.deps import AgentDeps
from app.llm.lexicon import violations
from app.llm.schemas import Rephrase

_LEAD = re.compile(
    r"^(Have you noticed |Has a doctor or nurse told you about |Has a test shown )([A-Z])([a-z])"
)


def lower_first(text: str) -> str:
    """Lower-case the first letter of a label unless it starts an acronym ("ADHD")."""
    return text[:1].lower() + text[1:] if text[1:2].islower() else text


def tidy_question(question: str) -> str:
    """Lower-case a capitalised term label inside a template ("noticed Farsightedness" -> "noticed
    farsightedness"). Acronyms (second letter upper case) are left alone."""
    return _LEAD.sub(lambda m: m.group(1) + m.group(2).lower() + m.group(3), question)


def phrase(deps: AgentDeps, family_id: str, question: str, why: str, age_months: int) -> Rephrase:
    def check(out: Rephrase) -> None:
        bad = violations(out.question + " " + out.why)
        if bad:
            raise ValueError(f"wording not allowed for parents: {bad}")

    question = tidy_question(question)
    payload = json.dumps({"question": question, "why": why, "age_months": age_months})
    res = deps.router.run(
        "phrase_question",
        payload,
        Rephrase,
        lambda: Rephrase.model_construct(question=question, why=why),
        validate=check,
        family_id=family_id,
    )
    return res.value
