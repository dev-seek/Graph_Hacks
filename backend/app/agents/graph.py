# pyright: basic, reportTypedDictNotRequiredAccess=false
"""The family agent: one LangGraph per family thread (`thread_id = family_<id>`), spec §9.

Control flow is an event loop: `await_event` is the ONLY node that calls `interrupt()` and does
nothing else, so a resume (even in a new process) re-runs nothing that matters. Every handler node
is a plain function of (state, graph) and writes to the family graph with MERGE on stable ids.
Findings, snapshots, gates and artifacts live in the family graph, not in agent state.
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt

from app.agents import packs
from app.agents.deps import AgentDeps
from app.agents.intake import (
    extract_document,
    extract_story,
    resolve_items,
)
from app.agents.phrasing import phrase
from app.agents.reasoning import DOCTOR_SOURCES, Reasoning, reason, term_names
from app.agents.safety_step import screen
from app.engine.planner import plan_round
from app.graph.client import rows
from app.graph.family import FamilyRepo, sha

MAX_HOME_QUESTIONS = 5


class AgentState(TypedDict, total=False):
    family_id: str
    event: dict[str, Any]
    phase: str
    round_no: int
    pending: dict[str, Any]
    outbox: dict[str, Any]
    gate: str


def _ancestor_closure(
    deps: AgentDeps, term_ids: list[str]
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    anc = deps.reasoner.cache.ancestors
    all_ids = sorted({a for t in term_ids for a in anc.get(t, {t})})
    names = term_names(deps, all_ids)
    edges: list[tuple[str, str]] = []
    if all_ids:
        edges = [
            (str(r["child"]), str(r["parent"]))
            for r in rows(deps.kb, "q6_termref_edges", {"ids": all_ids})
        ]
    return names, edges


def build_agent(deps: AgentDeps, saver: Any) -> CompiledStateGraph[Any, Any, Any, Any]:
    cache: dict[str, Reasoning] = {}

    def repo_of(state: AgentState) -> FamilyRepo:
        return deps.repo(state["family_id"])

    def rs_of(state: AgentState, repo: FamilyRepo, kind: str = "home") -> Reasoning:
        rs = cache.get(state["family_id"])
        if rs is None:
            rs = reason(deps, repo, persist=False, round_kind=kind)
            cache[state["family_id"]] = rs
        return rs

    def safety_out(flags: list[Any]) -> dict[str, Any]:
        return {
            "level": "EMERGENCY"
            if any(f.level == "EMERGENCY" for f in flags)
            else ("URGENT_SOON" if flags else "none"),
            "messages": [{"level": f.level, "plain": f.plain} for f in flags],
        }

    # --- the one interrupting node -------------------------------------------------------------

    def await_event(state: AgentState) -> AgentState:
        ev = interrupt({"phase": state.get("phase", "story")})
        return {"event": ev, "outbox": {}}

    def route_event(state: AgentState) -> str:
        if state.get("phase") == "urgent":
            return "urgent_idle"
        t = state["event"].get("type", "")
        return {
            "story": "story",
            "confirm": "confirm",
            "answers": "answers",
            "document": "document",
            "advance": "advance",
        }.get(t, "ignore")

    def ignore(state: AgentState) -> AgentState:
        return {"outbox": {"error": "unknown event"}}

    def urgent_idle(state: AgentState) -> AgentState:
        return {"outbox": {"safety": {"level": "EMERGENCY", "messages": []}}}

    # --- intake --------------------------------------------------------------------------------

    def _stage_confirm(
        repo: FamilyRepo, kind: str, items: list[Any], extra: dict[str, Any], safety: dict[str, Any]
    ) -> AgentState:
        repo.set_state("confirm", repo.get_state()[1])
        pending = {"kind": kind, "items": [i.as_dict() for i in items], **extra}
        return {
            "phase": "confirm",
            "pending": pending,
            "outbox": {"safety": safety, "extraction": pending["items"]},
        }

    def story(state: AgentState) -> AgentState:
        ev = state["event"]
        repo = repo_of(state)
        text: str = ev["text"]
        age = int(ev["age"])
        repo.set_age(age, ev.get("sex"))
        h = repo.add_story(text)
        res = screen(deps, repo, text, age)
        repo.add_event("story", "You shared your story", f"story_{h[:12]}")
        if res.emergency:
            repo.set_state("urgent", repo.get_state()[1])
            return {"phase": "urgent", "outbox": {"safety": safety_out(res.flags)}}
        ex = extract_story(deps, text, repo.family_id)
        items = resolve_items(deps, text, ex.value.items, "s")
        present = [i.term_id for i in items if i.status == "present"]
        if present:  # HPO-linked rules (e.g. a resolved seizure term) can also fire
            res = screen(deps, repo, "", age, present_terms=present, llm=False)
            if res.emergency:
                repo.set_state("urgent", repo.get_state()[1])
                return {"phase": "urgent", "outbox": {"safety": safety_out(res.flags)}}
        flags = res.flags or []
        return _stage_confirm(
            repo, "story", items, {"story_hash": h, "text_len": len(text)}, safety_out(flags)
        )

    def document(state: AgentState) -> AgentState:
        ev = state["event"]
        repo = repo_of(state)
        text: str = ev["text"]
        info = repo.info()
        assert info is not None  # noqa: S101
        res = screen(deps, repo, text, info.age_months)
        if res.emergency:
            repo.set_state("urgent", repo.get_state()[1])
            return {"phase": "urgent", "outbox": {"safety": safety_out(res.flags)}}
        doc_id = f"doc_{sha(text)[:16]}"
        repo.add_document(ev.get("kind", "text"), text, doc_id)
        ex = extract_document(deps, text, repo.family_id)
        items = resolve_items(deps, text, ex.value.items, "d")
        repo.add_event("document", "A doctor's letter was added", f"doc_{doc_id}")
        return _stage_confirm(repo, "document", items, {"doc_id": doc_id}, safety_out(res.flags))

    def confirm(state: AgentState) -> AgentState:
        ev = state["event"]
        pending = state.get("pending") or {}
        repo = repo_of(state)
        items = {i["id"]: i for i in pending.get("items", [])}
        edits = {e["id"]: e for e in ev.get("edits", [])}
        keep = (set(ev.get("accept", [])) | set(edits)) - set(ev.get("reject", []))
        chosen = [items[i] for i in sorted(keep) if i in items]
        names, edges = _ancestor_closure(deps, [i["term_id"] for i in chosen])
        repo.copy_termrefs(names, edges)
        kind = pending.get("kind", "story")
        origin = str(pending.get("story_hash") or pending.get("doc_id") or "")
        for it in chosen:
            e = edits.get(it["id"], {})
            repo.add_finding(
                term_id=it["term_id"],
                label=e.get("plain_label") or it["plain_label"],
                status=e.get("status") or it["status"],
                source=it["source"],
                onset_months=e.get("onset_months", it.get("onset_months")),
                quote=it["quote"],
                start=it["start"],
                end=it["end"],
                ev_kind="story" if kind == "story" else "document",
                story_hash=pending.get("story_hash"),
                doc_id=pending.get("doc_id"),
                finding_id=f"fd_{origin[:12]}_{it['id']}",
            )
        repo.add_event(
            "confirmed",
            f"You confirmed {len(chosen)} items",
            f"conf_{pending.get('story_hash') or pending.get('doc_id')}",
        )
        cache.pop(state["family_id"], None)
        return {"pending": {}, "outbox": {"confirmed": len(chosen)}}

    # --- answers -------------------------------------------------------------------------------

    def answers(state: AgentState) -> AgentState:
        ev = state["event"]
        repo = repo_of(state)
        info = repo.info()
        assert info is not None  # noqa: S101
        n = int(ev["round_no"])
        by_q = {r["qid"]: r for r in repo.round(n)}
        plain = {
            str(r["id"]): str(r["plain"] or r["name"])
            for r in rows(
                deps.kb, "q7_question_copy", {"ids": [q["term_id"] for q in by_q.values()]}
            )
        }
        yes_terms: list[str] = []
        for a in ev["answers"]:
            q = by_q.get(a["qid"])
            if q is None:
                continue
            fid: str | None = None
            if a["value"] in ("yes", "no"):
                status = "present" if a["value"] == "yes" else "absent"
                names, edges = _ancestor_closure(deps, [q["term_id"]])
                repo.copy_termrefs(names, edges)
                fid = repo.add_finding(
                    term_id=q["term_id"],
                    label=str(plain.get(q["term_id"]) or q["term_id"]),
                    status=status,
                    source="parent_answer",
                    ev_kind="answer",
                    finding_id=f"fa_{a['qid']}",
                )
                if status == "present":
                    yes_terms.append(q["term_id"])
            repo.record_answer(a["qid"], a["value"], fid)
        repo.add_event("answers", f"You answered round {n}", f"ans_round_{n}")
        res = screen(deps, repo, "", info.age_months, present_terms=yes_terms, llm=False)
        cache.pop(state["family_id"], None)
        if res.emergency:
            repo.set_state("urgent", n)
            return {"phase": "urgent", "outbox": {"safety": safety_out(res.flags)}}
        return {"outbox": {"safety": safety_out(res.flags)}}

    def advance(state: AgentState) -> AgentState:
        repo = repo_of(state)
        info = repo.info()
        assert info is not None  # noqa: S101
        months = int(state["event"].get("months", 6))
        before = repo.latest_gate()
        repo.set_age(info.age_months + months)
        repo.add_event("watch", f"{months} months later", f"adv_{info.age_months + months}")
        cache.pop(state["family_id"], None)
        return {"outbox": {"advanced": months, "previous_gate": before["kind"] if before else None}}

    # --- reason + gate -------------------------------------------------------------------------

    def reason_node(state: AgentState) -> AgentState:
        repo = repo_of(state)
        if state.get("phase") == "urgent":
            return {"gate": "URGENT"}
        rs = reason(deps, repo)
        cache[state["family_id"]] = rs
        out = dict(state.get("outbox", {}))
        out["gate"] = {"state": rs.gate.state, "fired": rs.gate.fired, "rule": rs.gate.rule}
        prev = out.get("previous_gate")
        if (
            prev is not None
            and prev != rs.gate.state
            and rs.gate.state in ("SEE_DOCTOR", "REFERRAL_READY")
        ):
            deps.notifier.notify(
                state["family_id"],
                "gate",
                "New information suggests it is a good time to see a doctor.",
            )
            repo.add_event(
                "gate", "A new check-in suggests seeing a doctor", f"gate_{rs.snapshot_at}"
            )
        return {"gate": rs.gate.state, "outbox": out}

    def route_gate(state: AgentState) -> str:
        g = state.get("gate", "CONTINUE")
        if g == "URGENT":
            return "to_await"
        if g == "REFERRAL_READY":
            return "referral"
        if g == "SEE_DOCTOR":
            return "doctor_pack"
        if g == "WATCH":
            return "watch"
        return "planner_home"

    def watch(state: AgentState) -> AgentState:
        repo = repo_of(state)
        _, n = repo.get_state()
        repo.set_state("watching", n)
        return {"phase": "watching", "round_no": n}

    def _plan_round(state: AgentState, kind: str) -> AgentState:
        repo = repo_of(state)
        info = repo.info()
        assert info is not None  # noqa: S101
        rs = rs_of(state, repo)
        inp = (
            rs.plan_in
            if kind == "home"
            else deps.reasoner.plan_input(
                rs.pruned, rs.result, repo.asked_terms(), info.age_months, "post_doctor"
            )
        )
        plan = rs.plan if kind == "home" else plan_round(inp)
        qs = plan.questions[:MAX_HOME_QUESTIONS]
        _, current = repo.get_state()
        if not qs:
            repo.set_state("watching", current)
            return {"phase": "watching", "round_no": current}
        n = (repo.latest_round() or (0, ""))[0] + 1
        copy = {
            str(r["id"]): r
            for r in rows(deps.kb, "q7_question_copy", {"ids": [q.term for q in qs]})
        }
        qdocs: list[dict[str, Any]] = []
        for i, q in enumerate(qs):
            c = copy.get(q.term, {})
            ph = phrase(deps, repo.family_id, q.text, str(c.get("why") or ""), info.age_months)
            qdocs.append(
                {
                    "qid": f"q{n}_{i}",
                    "term_id": q.term,
                    "text": ph.question,
                    "why": ph.why,
                    "how": c.get("how") or "",
                    "obs": q.obs,
                    "ig": q.ig,
                    "ask_doctor": q.ask_doctor,
                }
            )
        repo.add_round(n, kind, qdocs)
        repo.set_state("questions", n)
        return {"phase": "questions", "round_no": n}

    def planner_home(state: AgentState) -> AgentState:
        return _plan_round(state, "home")

    def planner_post(state: AgentState) -> AgentState:
        return _plan_round(state, "post_doctor")

    def doctor_pack_node(state: AgentState) -> AgentState:
        repo = repo_of(state)
        rs = rs_of(state, repo)
        _, code = repo.auth()
        pack = packs.doctor_pack(deps, repo, rs, code or "")
        repo.add_artifact("doctor_pack", pack.model_dump(), [f.id for f in rs.findings])
        _, n = repo.get_state()
        repo.add_event("gate", "Time to see a doctor", f"pack_{n}_{len(rs.findings)}")
        has_doctor = any(f.source in DOCTOR_SOURCES for f in rs.findings)
        if has_doctor:
            return {"gate": "SEE_DOCTOR_POST"}
        repo.set_state("see_doctor", n)
        return {"phase": "see_doctor", "round_no": n, "gate": "SEE_DOCTOR_PRE"}

    def route_after_pack(state: AgentState) -> str:
        return "planner_post" if state.get("gate") == "SEE_DOCTOR_POST" else "to_await"

    def referral_node(state: AgentState) -> AgentState:
        repo = repo_of(state)
        info = repo.info()
        assert info is not None  # noqa: S101
        rs = rs_of(state, repo)
        tests = []
        copy = (
            {
                str(r["id"]): r
                for r in rows(
                    deps.kb, "q7_question_copy", {"ids": [q.term for q in rs.plan.suggested_tests]}
                )
            }
            if rs.plan.suggested_tests
            else {}
        )
        for q in rs.plan.suggested_tests:
            tests.append(str(copy.get(q.term, {}).get("plain") or q.text))
        inp = packs.referral_input(rs, info.age_months, tests)
        letter = packs.draft_referral(deps, repo.family_id, inp)
        present_ids = [f.id for f in rs.findings if f.status == "present"]
        repo.add_artifact("referral_letter", {"text": letter, "input": inp}, present_ids)
        return {}

    def exporter_node(state: AgentState) -> AgentState:
        repo = repo_of(state)
        info = repo.info()
        assert info is not None  # noqa: S101
        rs = rs_of(state, repo)
        labels = term_names(deps, sorted({f.term_id for f in rs.findings}))
        doc = packs.build_phenopacket(
            repo.family_id, info.age_months, info.sex, rs.findings, labels, deps.hpo_version
        )
        repo.add_artifact("phenopacket", doc, [f.id for f in rs.findings])
        _, n = repo.get_state()
        repo.set_state("specialist_step", n)
        repo.add_event("gate", "Your child's notes are ready for a specialist", f"ref_{n}")
        return {"phase": "specialist_step", "round_no": n}

    g = StateGraph(AgentState)
    for name, fn in {
        "await_event": await_event, "ignore": ignore, "urgent_idle": urgent_idle,
        "story": story, "confirm": confirm, "answers": answers, "document": document,
        "advance": advance, "reason": reason_node, "watch": watch,
        "planner_home": planner_home, "planner_post": planner_post,
        "doctor_pack": doctor_pack_node, "referral": referral_node, "exporter": exporter_node,
    }.items():  # fmt: skip
        g.add_node(name, fn)
    g.add_edge(START, "await_event")
    g.add_conditional_edges(
        "await_event",
        route_event,
        ["story", "confirm", "answers", "document", "advance", "urgent_idle", "ignore"],
    )
    g.add_edge("story", "await_event")
    g.add_edge("document", "await_event")
    for name in ("confirm", "answers", "advance"):
        g.add_edge(name, "reason")
    g.add_edge("ignore", "await_event")
    g.add_edge("urgent_idle", "await_event")
    g.add_conditional_edges(
        "reason",
        route_gate,
        {"to_await": "await_event", "referral": "referral", "doctor_pack": "doctor_pack",
         "watch": "watch", "planner_home": "planner_home"},
    )  # fmt: skip
    g.add_edge("referral", "exporter")
    g.add_edge("exporter", "await_event")
    g.add_edge("watch", "await_event")
    g.add_edge("planner_home", "await_event")
    g.add_edge("planner_post", "await_event")
    g.add_conditional_edges(
        "doctor_pack", route_after_pack, {"planner_post": "planner_post", "to_await": "await_event"}
    )
    return g.compile(checkpointer=saver)
