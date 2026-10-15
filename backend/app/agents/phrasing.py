"""Question text for a round: pre-written `cx_question`, optionally rephrased for the child's age.

The rephrase is accepted only if it passes the lexicon (no disease-flavoured words, spec §10.9).
"""

from __future__ import annotations

import json

from app.agents.deps import AgentDeps
from app.llm.lexicon import violations
from app.llm.schemas import Rephrase


def phrase(deps: AgentDeps, family_id: str, question: str, why: str, age_months: int) -> Rephrase:
    def check(out: Rephrase) -> None:
        bad = violations(out.question + " " + out.why)
        if bad:
            raise ValueError(f"wording not allowed for parents: {bad}")

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
