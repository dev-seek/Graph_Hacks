"""Safety node (spec §9): deterministic rules first; the LLM may only add a flag."""

from __future__ import annotations

from collections.abc import Sequence

from app.agents.deps import AgentDeps
from app.graph.family import FamilyRepo
from app.llm.schemas import SafetyConcerns
from app.safety.engine import ExtraConcern, ScreenResult


def screen(
    deps: AgentDeps,
    repo: FamilyRepo,
    text: str,
    age_months: int | None,
    *,
    present_terms: Sequence[str] = (),
    llm: bool = True,
) -> ScreenResult:
    """Rules run first. An EMERGENCY returns at once: no model call can delay or soften it."""

    def run(extra: Sequence[ExtraConcern] = ()) -> ScreenResult:
        return deps.safety.screen(
            text,
            age_months=age_months,
            present_terms=present_terms,
            ancestors=deps.reasoner.cache.ancestors,
            extra=extra,
        )

    out = run()
    if not out.emergency and llm and text.strip():
        res = deps.router.run(
            "safety_extra",
            text,
            SafetyConcerns,
            lambda: SafetyConcerns(concerns=[]),
            family_id=repo.family_id,
        )
        extra = [ExtraConcern(quote=c.quote, level=c.level, why=c.why) for c in res.value.concerns]
        if extra:
            out = run(extra)
    for f in out.flags:
        repo.add_flag(f.rule_id, f.level, f.quote)
    return out
