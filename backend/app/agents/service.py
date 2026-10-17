"""Family service: the one place the API (and tests) talk to the agent graph and read views.

Parent views are built here from the family graph and carry no disease names, scores or ranks
(AGENTS.md rule 1); clinician views carry the disclaimer. Resume validation happens BEFORE the
event is sent, so a bad request never reaches a graph node.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from langgraph.types import Command
from pypdf import PdfReader
from redis.exceptions import ResponseError

from app.agents.build_graph import build_agent_graph
from app.agents.deps import AgentDeps
from app.agents.reasoning import disease_names, reason, term_names
from app.api.schemas import (
    CLINICIAN_DISCLAIMER,
    MAX_PDF_BYTES,
    ClinicianCandidate,
    ClinicianFinding,
    ClinicianView,
    GateOut,
    ParentConstellation,
    ParentEvent,
    ParentExtractedFinding,
    ParentExtractionOut,
    ParentLine,
    ParentNextStep,
    ParentPack,
    ParentQuestion,
    ParentRound,
    ParentStar,
    ParentState,
    ParentTimeline,
    SafetyMessage,
    SafetyOut,
    SupportingFinding,
)
from app.graph.client import rows
from app.graph.family import FamilyRepo
from app.safety.rules import load_rule_file

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LEN = 8
PHASE_NEXT: dict[str, tuple[str, str]] = {
    "story": ("answer_questions", "Tell us what you've noticed, in your own words."),
    "confirm": ("answer_questions", "Check what we picked up, then confirm."),
    "questions": ("answer_questions", "A few questions to fill in the picture."),
    "see_doctor": (
        "see_doctor",
        "It's a good time to see a doctor. Here's a one-page summary to bring, and questions you "
        "can ask.",
    ),
    "doctor_findings": ("upload_letter", "Add what the doctor found, when you have it."),
    "specialist_step": (
        "see_doctor",
        "A specialist review is a good next step. Bring the summary and ask about a referral.",
    ),
    "watching": (
        "wait",
        "Nothing you've told us needs a special appointment right now. Mention it at your next "
        "routine visit. Here's what to keep an eye on.",
    ),
    "urgent": (
        "emergency",
        "This needs urgent medical help. Call your local emergency number now (112 in India and "
        "Europe, 911 in the US) or go to the nearest emergency department. Your answers are "
        "saved — come back when your child is safe.",
    ),
}
ROUND_INTRO = "A few questions to fill in the picture. Answer what you can — 'Not sure' is fine."
URGENT_SOON_BANNER = (
    "Please see a doctor in the next day or two about this: {plain}. If it gets worse, call your "
    "local emergency number."
)


class FamilyNotFound(LookupError):
    pass


class BadRequest(ValueError):
    pass


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def pdf_to_text(data: bytes) -> str:
    if len(data) > MAX_PDF_BYTES:
        raise BadRequest("PDF is larger than 5 MB")
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except Exception as exc:  # noqa: BLE001
        raise BadRequest("could not read this PDF") from exc


class FamilyService:
    def __init__(self, deps: AgentDeps, saver: Any) -> None:
        self.deps = deps
        self.agent: Any = build_agent_graph(deps, saver)
        rules = load_rule_file()
        self._plain = {r.id: r.plain for r in rules.rules}
        self.crisis_lines = rules.crisis_lines
        self.emergency_numbers = rules.emergency_numbers

    # --- auth ----------------------------------------------------------------------------------

    def _auth(self, family_id: str) -> tuple[str | None, str | None]:
        try:
            return self.deps.repo(family_id).auth()
        except ResponseError:  # no such family graph (never existed or erased)
            return (None, None)

    def authenticate(self, family_id: str, token: str) -> bool:
        stored, _ = self._auth(family_id)
        return bool(stored) and hmac.compare_digest(stored or "", hash_token(token))

    def clinician_ok(self, family_id: str, code: str) -> bool:
        _, stored = self._auth(family_id)
        return bool(stored) and hmac.compare_digest((stored or "").upper(), code.strip().upper())

    # --- lifecycle -----------------------------------------------------------------------------

    def _cfg(self, family_id: str) -> Any:
        return {"configurable": {"thread_id": f"family_{family_id}"}}

    def create_family(self, *, demo: bool = False) -> tuple[str, str]:
        fid = uuid.uuid4().hex[:16]
        token = secrets.token_urlsafe(32)
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
        repo = self.deps.repo(fid)
        repo.create(
            self.deps.kb_version, 0, None, token_hash=hash_token(token), clinician_code=code,
            demo=demo,
        )  # fmt: skip
        repo.set_state("story", 0)
        self.agent.invoke({"family_id": fid, "phase": "story"}, self._cfg(fid))
        return fid, token

    def delete_family(self, family_id: str) -> None:
        self.deps.repo(family_id).delete()

    def _repo(self, family_id: str) -> FamilyRepo:
        repo = self.deps.repo(family_id)
        if not repo.exists():
            raise FamilyNotFound(family_id)
        return repo

    def _resume(self, family_id: str, event: dict[str, Any]) -> dict[str, Any]:
        cfg = self._cfg(family_id)
        self.agent.invoke(Command(resume=event), cfg)
        return dict(self.agent.get_state(cfg).values.get("outbox", {}))

    def _safety(self, raw: dict[str, Any] | None) -> SafetyOut:
        raw = raw or {"level": "none", "messages": []}
        msgs = [SafetyMessage(level=m["level"], plain=m["plain"]) for m in raw["messages"]]
        if raw["level"] == "EMERGENCY":
            return SafetyOut(
                level="EMERGENCY",
                messages=msgs,
                crisis_lines=self.crisis_lines,
                emergency_numbers=self.emergency_numbers,
            )
        return SafetyOut(level=raw["level"], messages=msgs)

    # --- parent actions ------------------------------------------------------------------------

    def submit_story(
        self, family_id: str, text: str, age_months: int, sex: str | None
    ) -> ParentExtractionOut:
        repo = self._repo(family_id)
        phase, _ = repo.get_state()
        if phase not in ("story", "confirm"):
            raise BadRequest("the story has already been shared")
        out = self._resume(
            family_id, {"type": "story", "text": text, "age": age_months, "sex": sex}
        )
        return ParentExtractionOut(
            safety=self._safety(out.get("safety")),
            extraction_to_confirm=[self._extracted(i) for i in out.get("extraction", [])],
        )

    def _extracted(self, i: dict[str, Any]) -> ParentExtractedFinding:
        return ParentExtractedFinding(
            id=i["id"], plain_label=i["plain_label"], status=i["status"], quote=i["quote"],
            start=i["start"], end=i["end"], onset_months=i.get("onset_months"),
        )  # fmt: skip

    def confirm(
        self, family_id: str, accept: list[str], reject: list[str], edits: list[dict[str, Any]]
    ) -> ParentState:
        repo = self._repo(family_id)
        if repo.get_state()[0] != "confirm":
            raise BadRequest("nothing is waiting to be confirmed")
        self._resume(
            family_id, {"type": "confirm", "accept": accept, "reject": reject, "edits": edits}
        )
        return self.state(family_id)

    def answers(
        self, family_id: str, round_no: int, answers: list[dict[str, str]]
    ) -> dict[str, Any]:
        repo = self._repo(family_id)
        phase, current = repo.get_state()
        if phase != "questions" or round_no != current:
            raise BadRequest("these questions are not open")
        valid = {r["qid"] for r in repo.round(round_no)}
        if any(a["qid"] not in valid for a in answers):
            raise BadRequest("unknown question")
        out = self._resume(family_id, {"type": "answers", "round_no": round_no, "answers": answers})
        return {"safety": self._safety(out.get("safety")), "next": self.state(family_id)}

    def add_document(
        self, family_id: str, kind: str, text: str | None, b64: str | None
    ) -> ParentExtractionOut:
        repo = self._repo(family_id)
        phase, _ = repo.get_state()
        if phase in ("urgent", "confirm"):
            raise BadRequest("finish the current step first")
        if kind == "pdf":
            if not b64:
                raise BadRequest("missing PDF content")
            try:
                data = base64.b64decode(b64, validate=True)
            except ValueError as exc:
                raise BadRequest("PDF content is not valid base64") from exc
            body = pdf_to_text(data)
        else:
            body = (text or "").strip()
        if not body:
            raise BadRequest("no text found in the document")
        out = self._resume(family_id, {"type": "document", "kind": kind, "text": body})
        return ParentExtractionOut(
            safety=self._safety(out.get("safety")),
            extraction_to_confirm=[self._extracted(i) for i in out.get("extraction", [])],
        )

    def advance(self, family_id: str, months: int = 6) -> ParentState:
        repo = self._repo(family_id)
        if repo.get_state()[0] in ("urgent", "story", "confirm"):
            raise BadRequest("not available right now")
        self._resume(family_id, {"type": "advance", "months": months})
        return self.state(family_id)

    def purge_expired(self, max_age_days: int = 7, *, now: datetime | None = None) -> int:
        """Public-demo retention (spec §17): erase family graphs older than `max_age_days`.

        Touches `family_*` graphs only (never kb, centre or the checkpoint graph). A graph whose
        creation time cannot be read is left alone. Returns how many families were erased.
        """
        cutoff = (now or datetime.now(UTC)) - timedelta(days=max_age_days)
        erased = 0
        for name in self.deps.db.list_graphs():
            if not name.startswith("family_"):
                continue
            fid = name.removeprefix("family_")
            try:
                info = self.deps.repo(fid).info()
                if info is None or datetime.fromisoformat(info.created_at) >= cutoff:
                    continue
                self.deps.repo(fid).delete()
            except Exception:  # noqa: BLE001, S112 (one broken family must not stop the sweep)
                continue
            erased += 1
        return erased

    def watch_all(self) -> int:
        """Daily watcher: re-score every active family; notify when a gate newly fires.

        Does not change ages (only the "advance" action does); it catches knowledge updates and
        findings added since the last gate. Returns how many families were notified.
        """
        notified = 0
        for name in self.deps.db.list_graphs():
            if not name.startswith("family_"):
                continue
            fid = name.removeprefix("family_")
            repo = self.deps.repo(fid)
            try:
                phase, _ = repo.get_state()
                if phase in ("urgent", "story", "confirm"):
                    continue
                before = repo.latest_gate()
                rs = reason(self.deps, repo, persist=True)
            except Exception:  # noqa: BLE001, S112 (one broken family must not stop the loop)
                continue
            if rs.gate.state in ("SEE_DOCTOR", "REFERRAL_READY") and (
                before is None or before["kind"] != rs.gate.state
            ):
                self.deps.notifier.notify(
                    fid, "gate", "New information suggests it is a good time to see a doctor."
                )
                repo.add_event(
                    "gate", "A check-in suggests seeing a doctor", f"watch_{rs.snapshot_at}"
                )
                notified += 1
        return notified

    # --- parent views --------------------------------------------------------------------------

    def state(self, family_id: str) -> ParentState:
        repo = self._repo(family_id)
        phase, n = repo.get_state()
        kind, label = PHASE_NEXT.get(phase, PHASE_NEXT["story"])
        banner: str | None = None
        flags = repo.flags()
        if phase == "urgent":
            banner = label
        elif any(f["level"] == "URGENT_SOON" for f in flags):
            f = next(f for f in flags if f["level"] == "URGENT_SOON")
            plain = self._plain.get(f["rule_id"], "something that a doctor should look at")
            banner = URGENT_SOON_BANNER.format(plain=plain.rstrip("."))
        return ParentState(
            phase=phase,  # type: ignore[arg-type]
            round_no=n,
            banner=banner,
            next_step=ParentNextStep(kind=kind, label=label),  # type: ignore[arg-type]
        )

    def round(self, family_id: str) -> ParentRound:
        repo = self._repo(family_id)
        phase, n = repo.get_state()
        if phase != "questions" or n < 1:
            raise BadRequest("no questions are open")
        qs = repo.round(n)
        return ParentRound(
            round_no=n,
            kind=qs[0]["kind"],
            questions=[
                ParentQuestion(
                    qid=q["qid"], text=q["text"], why=q["why"] or "", how_to_check=q["how"] or "",
                    ask_doctor=bool(q["ask_doctor"]),
                )
                for q in qs
            ],
        )  # fmt: skip

    def pack(self, family_id: str) -> ParentPack:
        repo = self._repo(family_id)
        art = repo.latest_artifact("doctor_pack")
        if art is None:
            raise BadRequest("no summary yet")
        return ParentPack.model_validate(art["payload"])

    def timeline(self, family_id: str) -> ParentTimeline:
        from app.agents.packs import finding_view

        repo = self._repo(family_id)
        return ParentTimeline(
            findings=[finding_view(f) for f in repo.findings()],
            events=[
                ParentEvent(at=e["at"], kind=e["kind"], label=e["label"]) for e in repo.events()
            ],
        )

    def constellation(self, family_id: str) -> ParentConstellation:
        repo = self._repo(family_id)
        fs = [f for f in repo.findings() if f.status == "present"]
        meta = {
            str(r["id"]): r["system"]
            for r in (
                rows(self.deps.kb, "q2f_term_meta", {"ids": [f.term_id for f in fs]}) if fs else []
            )
        }
        sys_names = term_names(self.deps, sorted({s for s in meta.values() if s}))
        stars = [
            ParentStar(id=f.id, label=f.label, system=sys_names.get(meta.get(f.term_id) or ""))
            for f in fs
        ]
        lines = [
            ParentLine(source=a.id, target=b.id)
            for i, a in enumerate(stars)
            for b in stars[i + 1 :]
            if a.system and a.system == b.system
        ]
        return ParentConstellation(stars=stars, lines=lines)

    # --- clinician views -----------------------------------------------------------------------

    def clinician(self, family_id: str) -> ClinicianView:
        repo = self._repo(family_id)
        info = repo.info()
        assert info is not None  # noqa: S101
        rs = reason(self.deps, repo, persist=False)
        names = disease_names(self.deps, [c.disease for c in rs.result.candidates[:5]])
        cands: list[ClinicianCandidate] = []
        for i, c in enumerate(rs.result.candidates[:5]):
            sup, opp = self._explain(c.disease, c.support)
            cands.append(
                ClinicianCandidate(
                    disease_id=c.disease, name=names.get(c.disease, c.disease), rank=i + 1,
                    posterior=min(1.0, max(0.0, c.posterior)), supporting=sup, opposing=opp,
                )
            )  # fmt: skip
        tests = rs.plan.suggested_tests
        copy = (
            {
                str(r["id"]): r
                for r in rows(self.deps.kb, "q7_question_copy", {"ids": [q.term for q in tests]})
            }
            if tests
            else {}
        )
        gate = repo.latest_gate() or {
            "kind": rs.gate.state,
            "inputs": rs.gate.inputs,
            "rule": rs.gate.rule,
        }
        letter = repo.latest_artifact("referral_letter")
        return ClinicianView(
            family_ref=family_id,
            child_age_months=info.age_months,
            findings=[
                ClinicianFinding(term_id=f.term_id, label=f.label, status=f.status, source=f.source,  # type: ignore[arg-type]
                                 quote=f.quote)
                for f in rs.findings
            ],
            rare_mass=min(1.0, max(0.0, rs.result.rare_mass)),
            candidates=cands,
            suggested_checks=[str(copy.get(q.term, {}).get("plain") or q.text) for q in tests],
            gate=GateOut(
                state=gate["kind"],
                fired=list(rs.gate.fired),
                rule=gate["rule"],
                inputs=gate["inputs"],
            ),
            referral_draft=letter["payload"]["text"] if letter else None,
            kb_version=info.kb_version,
            disclaimer=CLINICIAN_DISCLAIMER,
        )  # fmt: skip

    def _explain(
        self, disease: str, support: list[tuple[str, float]]
    ) -> tuple[list[SupportingFinding], list[SupportingFinding]]:
        ordered = sorted(support, key=lambda s: -abs(s[1]))[:6]
        ids = [t for t, _ in ordered]
        labels = term_names(self.deps, ids)
        sup: list[SupportingFinding] = []
        opp: list[SupportingFinding] = []
        for term, lr in ordered:
            path: list[str] = []
            if lr > 0:
                r = rows(self.deps.kb, "q4_explain_path", {"finding": term, "disease": disease})
                if r:
                    ids_on_path = [str(p) for p in r[0]["path"]]
                    pn = term_names(self.deps, ids_on_path)
                    path = [pn.get(p, p) for p in ids_on_path]
            item = SupportingFinding(
                term_id=term, label=labels.get(term, term), log_lr=lr, path=path
            )
            (sup if lr > 0 else opp).append(item)
        return sup, opp

    def phenopacket(self, family_id: str) -> dict[str, Any]:
        repo = self._repo(family_id)
        art = repo.latest_artifact("phenopacket")
        if art is None:
            raise BadRequest("not ready: the referral gate has not been reached")
        return dict(art["payload"])
