"""Scripted family journeys: drive the real service like a parent would (tests and demo recording).

A script supplies the story text, which extracted items the parent accepts, and how each question
is answered. The result is the list of screens a person would have seen (parent-safe payloads) plus
the clinician view at the end, so `make demo-record` can store them for zero-cost replay.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from app.agents.service import FamilyService
from app.api.schemas import ParentExtractedFinding
from app.graph.client import QueryLog, set_query_log
from app.graph.family import FamilyRepo

Answer = Literal["yes", "no", "unsure"]
MAX_ROUNDS = 6


@dataclass
class JourneyScript:
    story: str
    age_months: int
    sex: str | None = None
    accept: Callable[[list[ParentExtractedFinding]], list[str]] = lambda items: [
        i.id for i in items
    ]
    answer: Callable[[str, str], Answer] = lambda term_id, text: "unsure"
    letter: Callable[[FamilyService, str], str | None] = lambda svc, fid: None
    advance_months: int | None = None
    max_rounds: int = MAX_ROUNDS


@dataclass
class JourneyResult:
    family_id: str
    token: str
    steps: list[dict[str, Any]] = field(default_factory=list[dict[str, Any]])
    final_phase: str = ""
    rounds: int = 0
    log: QueryLog | None = None
    seen: int = 0


def _step(
    res: JourneyResult,
    screen: str,
    caption: str,
    payload: dict[str, Any],
    repo: FamilyRepo | None = None,
) -> None:
    """Append a step with the graph queries that ran since the previous step (live inspector)."""
    queries: list[dict[str, Any]] = []
    if res.log is not None:
        queries = [
            {
                "name": e.name,
                "cypher": e.cypher,
                "params": e.params,
                "rows": e.rows,
                "ms": round(e.ms, 2),
            }
            for e in res.log.entries[res.seen :]
        ]
        res.seen = len(res.log.entries)
    body = dict(payload)
    body["queries"] = queries
    gate = repo.latest_gate() if repo is not None else None
    if gate:
        body["gate"] = {"state": gate["kind"], "rule": gate["rule"], "inputs": gate["inputs"]}
    res.steps.append(
        {"n": len(res.steps) + 1, "screen": screen, "caption": caption, "payload": body}
    )


def run_journey(svc: FamilyService, script: JourneyScript, *, demo: bool = True) -> JourneyResult:
    fid, token = svc.create_family(demo=demo)
    res = JourneyResult(fid, token, log=QueryLog())
    set_query_log(res.log)
    try:
        return _run(svc, script, res, fid)
    finally:
        set_query_log(None)


def _run(svc: FamilyService, script: JourneyScript, res: JourneyResult, fid: str) -> JourneyResult:
    repo = svc.deps.repo(fid)
    ex = svc.submit_story(fid, script.story, script.age_months, script.sex)
    _step(res, "story", "The parent tells their story.", {"safety": ex.safety.model_dump()})
    if ex.safety.level == "EMERGENCY":
        st = svc.state(fid)
        _step(res, "urgent", "A safety rule fires first; nothing else happens.", st.model_dump())
        res.final_phase = st.phase
        return res
    _step(res, "confirm", "They check what we picked up.", ex.model_dump())
    accepted = script.accept(ex.extraction_to_confirm)
    rejected = [i.id for i in ex.extraction_to_confirm if i.id not in accepted]
    st = svc.confirm(fid, accepted, rejected, [])
    while st.phase == "questions" and res.rounds < script.max_rounds:
        rnd = svc.round(fid)
        res.rounds += 1
        _step(res, "round", f"A few short questions (round {rnd.round_no}).", rnd.model_dump())
        terms = {r["qid"]: r["term_id"] for r in repo.round(rnd.round_no)}
        answers = [
            {"qid": q.qid, "value": script.answer(terms[q.qid], q.text)} for q in rnd.questions
        ]
        out = svc.answers(fid, rnd.round_no, answers)
        st = out["next"]
        _step(
            res,
            "answers",
            "They answer; the next step follows.",
            {"answers": answers, "next": st.model_dump()},
        )
        if out["safety"].level == "EMERGENCY":
            break
    if st.phase == "see_doctor":
        _step(
            res,
            "see_doctor",
            "It is a good time to see a doctor.",
            {"pack": svc.pack(fid).model_dump(), "state": st.model_dump()},
        )
        letter = script.letter(svc, fid)
        if letter:
            doc = svc.add_document(fid, "text", letter, None)
            _step(res, "letter", "They add the doctor's letter and confirm it.", doc.model_dump())
            ids = [i.id for i in doc.extraction_to_confirm]
            st = svc.confirm(fid, ids, [], [])
            _step(
                res,
                "after_letter",
                "The doctor's findings join the picture.",
                st.model_dump(),
                repo,
            )
            while st.phase == "questions" and res.rounds < script.max_rounds:
                rnd = svc.round(fid)
                res.rounds += 1
                terms = {r["qid"]: r["term_id"] for r in repo.round(rnd.round_no)}
                answers = [
                    {"qid": q.qid, "value": script.answer(terms[q.qid], q.text)}
                    for q in rnd.questions
                ]
                st = svc.answers(fid, rnd.round_no, answers)["next"]
    if script.advance_months:
        st = svc.advance(fid, script.advance_months)
        _step(
            res,
            "watch",
            f"{script.advance_months} months later the picture is refreshed.",
            st.model_dump(),
        )
    final = svc.state(fid)
    res.final_phase = final.phase
    if final.phase == "specialist_step":
        _step(
            res,
            "referral_ready",
            "Notes for a specialist are ready.",
            {"state": final.model_dump()},
        )
    elif final.phase == "watching":
        _step(
            res,
            "no_escalation",
            "Nothing needs a special appointment right now.",
            final.model_dump(),
        )
    return res
