"""Artifacts: doctor pack (templated), referral letter (LLM + template fallback), Phenopacket v2."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from google.protobuf import json_format
from phenopackets import Phenopacket

from app.agents.deps import AgentDeps
from app.agents.phrasing import lower_first
from app.agents.reasoning import DOCTOR_SOURCES, Reasoning
from app.api.schemas import ParentFindingView, ParentPack
from app.graph.client import rows
from app.graph.family import FamilyRepo, FindingRow
from app.llm.lexicon import violations
from app.llm.schemas import ReferralDraft

MAX_CHECKS = 8
MAX_QUESTIONS = 5
SEX = {"female": "FEMALE", "male": "MALE", "other": "OTHER_SEX", "unknown": "UNKNOWN_SEX"}


def _iso_age(months: float) -> str:
    total = max(0, round(months))
    years, rem = divmod(total, 12)
    return f"P{years}Y{rem}M" if years else f"P{rem}M"


def finding_view(f: FindingRow) -> ParentFindingView:
    return ParentFindingView(
        id=f.id,
        plain_label=f.label,
        status=f.status,  # type: ignore[arg-type]
        source=f.source,  # type: ignore[arg-type]
        onset_months=f.onset,
        quote=f.quote,
    )


def _lay_texts(deps: AgentDeps, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    return {str(r["id"]): r for r in rows(deps.kb, "q7_question_copy", {"ids": ids})}


def doctor_pack(deps: AgentDeps, repo: FamilyRepo, rs: Reasoning, code: str) -> ParentPack:
    info = repo.info()
    assert info is not None  # noqa: S101
    present = [f for f in rs.findings if f.status == "present"]
    absent = [f for f in rs.findings if f.status == "absent"]
    exams = sorted((q for q in rs.plan.pool if q.obs == "exam"), key=lambda q: (-q.ig, q.term))
    tests = rs.plan.suggested_tests
    copy = _lay_texts(deps, [q.term for q in exams[:MAX_CHECKS]] + [q.term for q in tests])
    checks = list(
        dict.fromkeys(
            f"Whether a doctor can look for: {lower_first(str(copy[q.term]['plain'] or q.text))}"
            for q in exams[:MAX_CHECKS]
            if q.term in copy
        )
    )
    asks = [
        f"Would a check for “{copy[q.term]['plain'] or q.text}” be useful?"
        for q in tests[:MAX_QUESTIONS]
        if q.term in copy
    ]
    checks = [c for c in checks if not violations(c)]
    asks = [a for a in asks if not violations(a)]
    summary = (
        f"{len(present)} things noticed and {len(absent)} things checked and not present, "
        f"gathered over {repo.round_count('home')} rounds of questions."
    )
    return ParentPack(
        clinician_code=code,
        child_age_months=info.age_months,
        summary=summary,
        findings=[finding_view(f) for f in rs.findings],
        checks_to_ask_about=checks,
        questions_for_doctor=asks,
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


# --- referral letter ------------------------------------------------------------------------


def referral_input(rs: Reasoning, age_months: int, tests: list[str]) -> dict[str, Any]:
    return {
        "age_months": age_months,
        "findings_present": sorted({f.label for f in rs.findings if f.status == "present"}),
        "findings_absent": sorted({f.label for f in rs.findings if f.status == "absent"}),
        "doctor_findings": sorted(
            {f.label for f in rs.findings if f.source in DOCTOR_SOURCES and f.status == "present"}
        ),
        "candidates_for_clinician_consideration": [
            rs.names.get(c.disease, c.disease) for c in rs.result.candidates[:5]
        ],
        "suggested_tests": tests,
    }


def fallback_referral(inp: dict[str, Any]) -> ReferralDraft:
    n = len(inp["findings_present"])
    return ReferralDraft(
        reason_for_referral=(
            f"Specialist review requested for a {inp['age_months']}-month-old child with "
            f"{n} recorded findings across several body systems and no unifying explanation yet."
        ),
        history_summary=(
            "Findings were gathered by the family through structured questions and confirmed by "
            "a doctor's examination; see the lists below. Decision support only."
        ),
        findings_present=list(inp["findings_present"]),
        findings_absent=list(inp["findings_absent"]),
        suggested_tests=list(inp["suggested_tests"]),
        closing="Candidates for clinician consideration: "
        + ("; ".join(inp["candidates_for_clinician_consideration"]) or "none listed")
        + ". Not a diagnosis.",
    )


def validate_referral(out: ReferralDraft, inp: dict[str, Any]) -> None:
    """The letter may only restate supplied findings and tests (no invented facts)."""
    for field_name, allowed in (
        ("findings_present", inp["findings_present"]),
        ("findings_absent", inp["findings_absent"]),
        ("suggested_tests", inp["suggested_tests"]),
    ):
        extra = set(getattr(out, field_name)) - set(allowed)
        if extra:
            raise ValueError(f"{field_name} contains items not in the input: {sorted(extra)}")


def draft_referral(deps: AgentDeps, family_id: str, inp: dict[str, Any]) -> str:
    res = deps.router.run(
        "draft_referral",
        json.dumps(inp, sort_keys=True),
        ReferralDraft,
        lambda: fallback_referral(inp),
        validate=lambda o: validate_referral(o, inp),
        family_id=family_id,
    )
    return render_letter(res.value)


def render_letter(d: ReferralDraft) -> str:
    def bullets(xs: list[str]) -> str:
        return "\n".join(f"- {x}" for x in xs) or "- none recorded"

    return (
        f"Reason for referral\n{d.reason_for_referral}\n\nHistory\n{d.history_summary}\n\n"
        f"Findings present\n{bullets(d.findings_present)}\n\n"
        f"Checked and not present\n{bullets(d.findings_absent)}\n\n"
        f"Suggested tests\n{bullets(d.suggested_tests)}\n\n{d.closing}"
    )


# --- Phenopacket v2 -------------------------------------------------------------------------


def build_phenopacket(
    family_id: str,
    age_months: int,
    sex: str | None,
    findings: list[FindingRow],
    labels: dict[str, str],
    hpo_version: str,
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for f in findings:
        feat: dict[str, Any] = {"type": {"id": f.term_id, "label": labels.get(f.term_id, f.label)}}
        if f.status == "absent":
            feat["excluded"] = True
        if f.onset is not None:
            feat["onset"] = {"age": {"iso8601duration": _iso_age(f.onset)}}
        features.append(feat)
    subject_id = f"cx-{family_id}"
    doc: dict[str, Any] = {
        "id": f"{subject_id}-pp",
        "subject": {
            "id": subject_id,
            "timeAtLastEncounter": {"age": {"iso8601duration": _iso_age(age_months)}},
            "sex": SEX.get(sex or "unknown", "UNKNOWN_SEX"),
        },
        "phenotypicFeatures": features,
        "metaData": {
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "createdBy": "Constellation (decision support; synthetic or family-entered data)",
            "resources": [
                {
                    "id": "hp",
                    "name": "human phenotype ontology",
                    "url": "http://purl.obolibrary.org/obo/hp.owl",
                    "version": hpo_version,
                    "namespacePrefix": "HP",
                    "iriPrefix": "http://purl.obolibrary.org/obo/HP_",
                }
            ],
            "phenopacketSchemaVersion": "2.0",
        },
    }
    validate_phenopacket(doc)
    return doc


def validate_phenopacket(doc: dict[str, Any]) -> None:
    """Parse with the official GA4GH protobuf schema; unknown or mistyped fields raise."""
    json_format.ParseDict(doc, Phenopacket(), ignore_unknown_fields=False)
