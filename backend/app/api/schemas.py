"""API contract (spec §12). FROZEN after Phase 2: changes need an ADR.

Two families of models:
- `Parent*` models reach the parent UI. They never carry disease names, probabilities, ranks or
  candidates (AGENTS.md rule 1). `tests/test_api_contract.py` rejects forbidden keys recursively.
- `Clinician*` / `Centre*` models are for the clinician and centre views (disclaimer included).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

SafetyLevel = Literal["none", "URGENT_SOON", "EMERGENCY"]
AnswerValue = Literal["yes", "no", "unsure"]
FindingStatus = Literal["present", "absent"]
FindingSource = Literal["parent_story", "parent_answer", "doctor_exam", "lab_or_test"]
Sex = Literal["female", "male", "other", "unknown"]
ParentPhase = Literal[
    "story",
    "confirm",
    "questions",
    "see_doctor",
    "doctor_findings",
    "specialist_step",
    "watching",
    "urgent",
]
MAX_STORY_CHARS = 4000
MAX_PDF_BYTES = 5 * 1024 * 1024
PARENT_DISCLAIMER = (
    "Constellation does not diagnose. It helps you gather information and decide when to see a "
    "doctor. Always follow your doctor's advice. In an emergency, call your local emergency number."
)
CLINICIAN_DISCLAIMER = (
    "Decision support only, not a diagnosis. Candidates are ranked by how well recorded findings "
    "match published phenotype annotations; confirm with clinical judgement and testing."
)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- shared -------------------------------------------------------------------------------------


class SafetyMessage(Strict):
    level: Literal["URGENT_SOON", "EMERGENCY"]
    plain: str


class SafetyOut(Strict):
    level: SafetyLevel = "none"
    messages: list[SafetyMessage] = Field(default_factory=list[SafetyMessage])
    crisis_lines: dict[str, str] = Field(default_factory=dict[str, str])
    emergency_numbers: dict[str, str] = Field(default_factory=dict[str, str])


# --- parent-safe models -------------------------------------------------------------------------


class ParentFamilyCreated(Strict):
    family_id: str
    family_token: str


class ParentStoryIn(Strict):
    text: str = Field(min_length=1, max_length=MAX_STORY_CHARS)
    child_age_months: int = Field(ge=0, le=240)
    sex: Sex | None = None


class ParentExtractedFinding(Strict):
    id: str
    plain_label: str
    status: FindingStatus
    quote: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    onset_months: float | None = None


class ParentExtractionOut(Strict):
    safety: SafetyOut
    extraction_to_confirm: list[ParentExtractedFinding]


class ParentFindingEdit(Strict):
    id: str
    plain_label: str | None = None
    status: FindingStatus | None = None
    onset_months: float | None = None


class ParentConfirmIn(Strict):
    accept: list[str] = Field(default_factory=list[str])
    reject: list[str] = Field(default_factory=list[str])
    edits: list[ParentFindingEdit] = Field(default_factory=list[ParentFindingEdit])


class ParentNextStep(Strict):
    kind: Literal["answer_questions", "see_doctor", "upload_letter", "wait", "emergency", "done"]
    label: str


class ParentState(Strict):
    phase: ParentPhase
    round_no: int = Field(ge=0)
    banner: str | None = None
    next_step: ParentNextStep
    disclaimer: str = PARENT_DISCLAIMER


class ParentQuestion(Strict):
    qid: str
    text: str
    why: str
    how_to_check: str
    ask_doctor: bool = False


class ParentRound(Strict):
    round_no: int = Field(ge=1)
    kind: Literal["home", "post_doctor"]
    questions: list[ParentQuestion]


class ParentAnswer(Strict):
    qid: str
    value: AnswerValue


class ParentAnswersIn(Strict):
    answers: list[ParentAnswer] = Field(min_length=1)


class ParentAnswersOut(Strict):
    safety: SafetyOut
    next: ParentState


class ParentFindingView(Strict):
    id: str
    plain_label: str
    status: FindingStatus
    source: FindingSource
    onset_months: float | None = None
    quote: str | None = None


class ParentPack(Strict):
    """One-page doctor pack data: what was observed, what to check, questions to ask."""

    clinician_code: str
    child_age_months: int
    summary: str
    findings: list[ParentFindingView]
    checks_to_ask_about: list[str]
    questions_for_doctor: list[str]
    generated_at: str
    disclaimer: str = PARENT_DISCLAIMER


class ParentDocumentIn(Strict):
    kind: Literal["text", "pdf"]
    text: str | None = Field(default=None, max_length=MAX_STORY_CHARS * 5)
    filename: str | None = None
    content_base64: str | None = None


class ParentEvent(Strict):
    at: str
    kind: Literal["story", "confirmed", "answers", "doctor_visit", "document", "gate", "flag"]
    label: str


class ParentTimeline(Strict):
    findings: list[ParentFindingView]
    events: list[ParentEvent]


class ParentStar(Strict):
    id: str
    label: str
    system: str | None = None


class ParentLine(Strict):
    source: str
    target: str


class ParentConstellation(Strict):
    """Findings only (never conditions): stars joined when they share a body system."""

    stars: list[ParentStar]
    lines: list[ParentLine]


# --- clinician models ---------------------------------------------------------------------------


class ClinicianFinding(Strict):
    term_id: str
    label: str
    status: FindingStatus
    source: FindingSource
    quote: str | None = None


class SupportingFinding(Strict):
    term_id: str
    label: str
    log_lr: float
    path: list[str] = Field(default_factory=list[str])


class ClinicianCandidate(Strict):
    disease_id: str
    name: str
    rank: int = Field(ge=1)
    posterior: float = Field(ge=0.0, le=1.0)
    supporting: list[SupportingFinding]
    opposing: list[SupportingFinding]


class GateOut(Strict):
    state: Literal["URGENT", "REFERRAL_READY", "SEE_DOCTOR", "WATCH", "CONTINUE"]
    fired: list[str]
    rule: str
    inputs: dict[str, float | int | bool]


class ClinicianView(Strict):
    family_ref: str
    child_age_months: int
    findings: list[ClinicianFinding]
    rare_mass: float = Field(ge=0.0, le=1.0)
    candidates: list[ClinicianCandidate]
    suggested_checks: list[str]
    gate: GateOut
    referral_draft: str | None = None
    kb_version: str
    disclaimer: str = CLINICIAN_DISCLAIMER


class PhenopacketOut(Strict):
    phenopacket: dict[str, Any]


# --- centre models ------------------------------------------------------------------------------


class CentreOverview(Strict):
    cases: int
    resolved: int
    clinicians: int
    protocols: int
    kb_version: str


class CentreLookalike(Strict):
    case_id: str
    diagnosis: str | None
    shared_terms: list[str]
    shared_ic: float
    clinician: str | None = None
    specialty: str | None = None
    protocol: str | None = None
    tests: list[str] = Field(default_factory=list[str])
    turnaround_days: int | None = None


class CentreRouting(Strict):
    case_id: str
    lookalikes: list[CentreLookalike]
    suggested_clinician: str | None = None  # ADR-0015 (additive)
    suggested_specialty: str | None = None
    suggested_protocol: str | None = None
    suggested_tests: list[str] = Field(default_factory=list[str])
    expected_days: int | None = None
    disclaimer: str = (
        "Illustrative clinic data (synthetic). Decision support for clinic staff only."
    )


class CentreBridge(Strict):
    term_id: str
    name: str
    score: float


class CentreCluster(Strict):
    cluster_id: int
    cases: list[str]
    size: int


class CentreCase(Strict):
    case_id: str
    status: Literal["open", "referred", "resolved"]
    age_band: str
    terms: list[str]
    diagnosis: str | None = None
    synthetic: bool = True


class CentreAskIn(Strict):
    question: str = Field(min_length=1, max_length=500)


class CentreAskOut(Strict):
    answer: str
    query_ids: list[str]


class CentreWhatIfIn(Strict):
    new_kb_version: str
    tau2: float | None = Field(default=None, ge=0.0, le=1.0)  # ADR-0015 (additive)


class CentreWhatIfDetail(Strict):
    case_id: str
    before: float
    after: float
    direction: Literal["crosses_up", "crosses_down"]


class CentreWhatIfOut(Strict):
    affected_cases: list[str]
    summary: str
    from_version: str | None = None  # ADR-0015 (additive)
    to_version: str | None = None
    tau2: float | None = None
    rescored: int = 0
    details: list[CentreWhatIfDetail] = Field(default_factory=list[CentreWhatIfDetail])
    ms: float = 0.0
    graph: str = "centre_whatif"


class CentreNoteIn(Strict):
    kind: Literal["case", "term", "protocol"]
    target: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=500)


class CentreNote(Strict):
    id: str
    text: str
    at: str
    role: str
    kind: str
    target: str


class CentreProtocolStat(Strict):
    protocol: str
    tests: list[str]
    cases: int
    avg_days: float


class CentreClinicianStat(Strict):
    clinician: str
    specialty: str
    cases: int
    resolved: int


class CentreCaseRow(Strict):
    case_id: str
    status: Literal["open", "referred", "resolved"]
    age_band: str
    diagnosis: str | None = None


# --- demo, debug, meta --------------------------------------------------------------------------


class DemoJourney(Strict):
    id: str
    title: str
    blurb: str


class DemoStep(Strict):
    n: int
    screen: str
    caption: str
    payload: dict[str, Any] = Field(default_factory=dict[str, Any])


class QueryLogEntry(Strict):
    name: str
    cypher: str
    params: dict[str, Any]
    rows: int
    ms: float


PARENT_MODELS: tuple[type[BaseModel], ...] = (
    ParentFamilyCreated,
    ParentStoryIn,
    ParentExtractionOut,
    ParentConfirmIn,
    ParentState,
    ParentRound,
    ParentAnswersIn,
    ParentAnswersOut,
    ParentPack,
    ParentDocumentIn,
    ParentTimeline,
    ParentConstellation,
)
CLINICIAN_MODELS: tuple[type[BaseModel], ...] = (ClinicianView, PhenopacketOut)
