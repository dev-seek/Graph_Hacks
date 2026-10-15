"""Family graph repository (spec §11.2): one `family_<id>` graph per family, registry queries only.

Findings are the source of truth; corrections never delete (`REPLACED_BY`); every write is a MERGE
on a stable id so a re-run (for example after a LangGraph resume) cannot duplicate anything.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from falkordb import FalkorDB, Graph
from redis.exceptions import ResponseError

from app.graph.client import connect, rows, write

CHECKPOINT_GRAPH = "langgraph_checkpoints"


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def new_id() -> str:
    return uuid.uuid4().hex


def graph_name(family_id: str) -> str:
    return f"family_{family_id}"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FindingRow:
    id: str
    term_id: str
    label: str
    status: str
    source: str
    onset: float | None
    at: str
    active: bool
    quote: str | None
    start: int | None
    end: int | None


@dataclass(frozen=True)
class FamilyInfo:
    id: str
    kb_version: str
    consent: bool
    age_months: int
    sex: str | None
    created_at: str


class FamilyRepo:
    def __init__(self, family_id: str, db: FalkorDB | None = None) -> None:
        self.family_id = family_id
        self.db = db or connect()
        self.graph: Graph = self.db.select_graph(graph_name(family_id))

    # --- lifecycle ----------------------------------------------------------------------------

    def create(
        self,
        kb_version: str,
        age_months: int,
        sex: str | None,
        consent: bool = False,
        *,
        token_hash: str | None = None,
        clinician_code: str | None = None,
        demo: bool = False,
    ) -> None:
        write(
            self.graph,
            "f_create_family",
            {
                "id": self.family_id,
                "at": now(),
                "kb": kb_version,
                "consent": consent,
                "age": age_months,
                "sex": sex,
                "token_hash": token_hash,
                "code": clinician_code,
                "demo": demo,
            },
        )

    def auth(self) -> tuple[str | None, str | None]:
        """(token_hash, clinician_code) or (None, None) when the family does not exist."""
        r = rows(self.graph, "f_get_auth", {"id": self.family_id})
        return (r[0]["token_hash"], r[0]["clinician_code"]) if r else (None, None)

    def round_count(self, kind: str) -> int:
        return int(rows(self.graph, "f_round_count", {"kind": kind})[0]["n"])

    def info(self) -> FamilyInfo | None:
        r = rows(self.graph, "f_get_family", {"id": self.family_id})
        if not r:
            return None
        x = r[0]
        return FamilyInfo(
            x["id"],
            x["kb_version"],
            bool(x["consent"]),
            int(x["age_months"]),
            x["sex"],
            x["created_at"],
        )

    def set_age(self, age_months: int, sex: str | None = None) -> None:
        write(self.graph, "f_set_age", {"id": self.family_id, "age": age_months, "sex": sex})

    def set_kb_version(self, kb_version: str) -> None:
        write(self.graph, "f_set_kb_version", {"id": self.family_id, "kb": kb_version})

    def exists(self) -> bool:
        try:
            return self.info() is not None
        except ResponseError:
            return False

    def delete(self) -> None:
        """Erasure: drop the family graph and its LangGraph checkpoints (registry Cypher)."""
        try:
            self.graph.delete()
        except ResponseError:
            pass  # graph never existed
        cp = self.db.select_graph(CHECKPOINT_GRAPH)
        try:
            write(cp, "f_delete_checkpoints", {"thread_id": f"family_{self.family_id}"})
        except ResponseError:
            pass  # no checkpoint graph yet

    # --- state --------------------------------------------------------------------------------

    def set_state(self, phase: str, round_no: int) -> None:
        write(
            self.graph,
            "f_set_state",
            {"id": self.family_id, "phase": phase, "round_no": round_no, "at": now()},
        )

    def get_state(self) -> tuple[str, int]:
        r = rows(self.graph, "f_get_state", {"id": self.family_id})
        if not r or r[0]["phase"] is None:
            return ("story", 0)
        return (str(r[0]["phase"]), int(r[0]["round_no"] or 0))

    def add_event(self, kind: str, label: str, event_id: str | None = None) -> None:
        write(
            self.graph,
            "f_add_event",
            {"id": event_id or new_id(), "kind": kind, "label": label, "at": now()},
        )

    def events(self) -> list[dict[str, Any]]:
        return rows(self.graph, "f_events", {})

    # --- terms, stories, documents --------------------------------------------------------------

    def add_story(self, text: str) -> str:
        h = sha(text)
        write(self.graph, "f_add_story", {"hash": h, "at": now()})
        return h

    def add_document(self, kind: str, content: str, doc_id: str | None = None) -> str:
        did = doc_id or new_id()
        write(
            self.graph,
            "f_add_document",
            {"id": did, "kind": kind, "sha": sha(content), "at": now()},
        )
        return did

    def copy_termrefs(self, names: dict[str, str], edges: Iterable[tuple[str, str]]) -> None:
        """Local copy of used terms + ancestors so the family graph explains itself."""
        terms = [{"id": i, "name": n} for i, n in sorted(names.items())]
        if terms:
            write(self.graph, "f_upsert_termrefs", {"terms": terms})
        es = [{"child": c, "parent": p} for c, p in sorted(set(edges))]
        if es:
            write(self.graph, "f_link_termref_edges", {"edges": es})

    # --- findings -----------------------------------------------------------------------------

    def add_finding(
        self,
        *,
        term_id: str,
        label: str,
        status: str,
        source: str,
        onset_months: float | None = None,
        quote: str | None = None,
        start: int | None = None,
        end: int | None = None,
        ev_kind: str = "story",
        story_hash: str | None = None,
        doc_id: str | None = None,
        finding_id: str | None = None,
    ) -> str:
        fid = finding_id or new_id()
        ev_id = f"ev_{fid}"
        write(
            self.graph,
            "f_add_finding",
            {
                "id": fid,
                "term_id": term_id,
                "label": label,
                "status": status,
                "source": source,
                "onset": onset_months,
                "at": now(),
                "ev_id": ev_id,
                "ev_kind": ev_kind,
                "quote": quote,
                "start": start,
                "end": end,
            },
        )
        if story_hash:
            write(self.graph, "f_link_evidence_story", {"ev_id": ev_id, "hash": story_hash})
        if doc_id:
            write(self.graph, "f_link_evidence_document", {"ev_id": ev_id, "doc_id": doc_id})
        return fid

    def correct_finding(self, old_id: str, **new: Any) -> str:
        """History is kept: old -[:REPLACED_BY]-> new, old becomes inactive."""
        new_id_ = self.add_finding(**new)
        write(self.graph, "f_replace_finding", {"old_id": old_id, "new_id": new_id_})
        return new_id_

    def deactivate_finding(self, finding_id: str) -> None:
        write(self.graph, "f_deactivate_finding", {"id": finding_id})

    def findings(self, include_inactive: bool = False) -> list[FindingRow]:
        out: dict[str, FindingRow] = {}
        for r in rows(self.graph, "f_list_findings", {"include_inactive": include_inactive}):
            out.setdefault(
                r["id"],
                FindingRow(
                    r["id"],
                    r["term_id"],
                    r["label"],
                    r["status"],
                    r["source"],
                    r["onset"],
                    r["at"],
                    bool(r["active"]),
                    r["quote"],
                    r["start"],
                    r["end"],
                ),
            )
        return list(out.values())

    # --- rounds -------------------------------------------------------------------------------

    def add_round(self, n: int, kind: str, questions: Sequence[dict[str, Any]]) -> None:
        write(self.graph, "f_add_round", {"n": n, "kind": kind, "at": now()})
        for pos, q in enumerate(questions):
            write(
                self.graph,
                "f_add_question",
                {
                    "n": n,
                    "qid": q["qid"],
                    "term_id": q["term_id"],
                    "text": q["text"],
                    "obs": q.get("obs", "home"),
                    "ig": q.get("ig", 0.0),
                    "why": q.get("why", ""),
                    "how": q.get("how", ""),
                    "ask_doctor": bool(q.get("ask_doctor", False)),
                    "pos": pos,
                },
            )

    def round(self, n: int) -> list[dict[str, Any]]:
        return rows(self.graph, "f_list_round", {"n": n})

    def latest_round(self) -> tuple[int, str] | None:
        r = rows(self.graph, "f_latest_round", {})
        return (int(r[0]["n"]), str(r[0]["kind"])) if r else None

    def asked_terms(self) -> set[str]:
        return {str(r["term_id"]) for r in rows(self.graph, "f_asked_terms", {})}

    def record_answer(self, qid: str, value: str, finding_id: str | None) -> None:
        aid = f"ans_{qid}"
        write(self.graph, "f_record_answer", {"qid": qid, "aid": aid, "value": value, "at": now()})
        if finding_id:
            write(self.graph, "f_link_answer_finding", {"aid": aid, "fid": finding_id})

    # --- snapshots, gates, flags, artifacts ---------------------------------------------------

    def add_snapshot(
        self,
        round_no: int,
        kb_version: str,
        rare_mass: float,
        n_findings: int,
        candidates: Sequence[dict[str, Any]],
    ) -> str:
        at = now()
        write(
            self.graph,
            "f_add_snapshot",
            {
                "round": round_no,
                "at": at,
                "kb": kb_version,
                "rare_mass": rare_mass,
                "n_findings": n_findings,
            },
        )
        if candidates:
            write(
                self.graph,
                "f_add_candidates",
                {"round": round_no, "at": at, "cands": list(candidates)},
            )
        return at

    def latest_snapshot(self) -> dict[str, Any] | None:
        r = rows(self.graph, "f_latest_snapshot", {})
        if not r:
            return None
        head = r[0]
        return {
            "round": head["round"],
            "at": head["at"],
            "kb_version": head["kb_version"],
            "rare_mass": head["rare_mass"],
            "n_findings": head["n_findings"],
            "candidates": [
                {"id": x["disease"], "name": x["name"], "rank": x["rank"], "post": x["post"]}
                for x in r
                if x["disease"]
            ],
        }

    def add_gate(
        self, round_no: int, snapshot_at: str, kind: str, inputs: dict[str, Any], rule: str
    ) -> None:
        write(
            self.graph,
            "f_add_gate",
            {
                "id": new_id(),
                "round": round_no,
                "snap_at": snapshot_at,
                "kind": kind,
                "at": now(),
                "inputs": json.dumps(inputs, sort_keys=True),
                "rule": rule,
            },
        )

    def latest_gate(self) -> dict[str, Any] | None:
        r = rows(self.graph, "f_latest_gate", {})
        if not r:
            return None
        return {**r[0], "inputs": json.loads(r[0]["inputs"])}

    def add_flag(self, rule_id: str, level: str, quote: str | None) -> None:
        write(
            self.graph,
            "f_add_flag",
            {
                "rule_id": rule_id,
                "qhash": sha(quote or ""),
                "level": level,
                "at": now(),
                "quote": quote,
            },
        )

    def flags(self) -> list[dict[str, Any]]:
        return rows(self.graph, "f_list_flags", {})

    def add_artifact(self, kind: str, payload: dict[str, Any], cites: Sequence[str]) -> str:
        prev = rows(self.graph, "f_latest_artifact", {"kind": kind})
        version = (int(prev[0]["version"]) + 1) if prev else 1
        aid = new_id()
        write(
            self.graph,
            "f_add_artifact",
            {
                "id": aid,
                "kind": kind,
                "version": version,
                "at": now(),
                "payload": json.dumps(payload, sort_keys=True),
            },
        )
        if cites:
            write(self.graph, "f_cite_findings", {"id": aid, "cites": list(cites)})
        return aid

    def latest_artifact(self, kind: str) -> dict[str, Any] | None:
        r = rows(self.graph, "f_latest_artifact", {"kind": kind})
        return {**r[0], "payload": json.loads(r[0]["payload"])} if r else None
