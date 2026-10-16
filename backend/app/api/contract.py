"""API routes (spec §12). Request/response models are the frozen contract in `schemas.py`.

Parent routes sit behind the family bearer token, clinician routes behind the clinician code. The
centre and demo routes stay 501 until their phases wire them (P3 task 10, P5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from redis.exceptions import ResponseError

from app.agents.service import BadRequest, FamilyNotFound
from app.api import schemas as s
from app.api.runtime import (
    WHATIF_LIMIT,
    Centre,
    ClinicianFamilyId,
    FamilyId,
    Service,
    create_allowed,
    is_demo,
    logged,
    query_log,
    to_http,
)
from app.centre.service import BadInput, NotFound

router = APIRouter(prefix="/api")
Bearer = Annotated[str | None, Header(alias="Authorization")]


def _guard[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except (FamilyNotFound, BadRequest) as exc:
        raise to_http(exc) from exc


@router.post("/families", tags=["parent"], dependencies=[Depends(create_allowed)])
def create_family(svc: Service, request: Request) -> s.ParentFamilyCreated:
    fid, token = svc.create_family()
    return s.ParentFamilyCreated(family_id=fid, family_token=token)


@router.post("/families/{family_id}/story", tags=["parent"])
def post_story(
    family_id: str, body: s.ParentStoryIn, svc: Service, _: FamilyId
) -> s.ParentExtractionOut:
    with logged(family_id):
        return _guard(
            lambda: svc.submit_story(family_id, body.text, body.child_age_months, body.sex)
        )


@router.post("/families/{family_id}/confirm", tags=["parent"])
def post_confirm(
    family_id: str, body: s.ParentConfirmIn, svc: Service, _: FamilyId
) -> s.ParentState:
    with logged(family_id):
        return _guard(
            lambda: svc.confirm(
                family_id, body.accept, body.reject, [e.model_dump() for e in body.edits]
            )
        )


@router.get("/families/{family_id}/state", tags=["parent"])
def get_state(family_id: str, svc: Service, _: FamilyId) -> s.ParentState:
    with logged(family_id):
        return _guard(lambda: svc.state(family_id))


@router.get("/families/{family_id}/round", tags=["parent"])
def get_round(family_id: str, svc: Service, _: FamilyId) -> s.ParentRound:
    with logged(family_id):
        return _guard(lambda: svc.round(family_id))


@router.post("/families/{family_id}/round/{n}/answers", tags=["parent"])
def post_answers(
    family_id: str, n: int, body: s.ParentAnswersIn, svc: Service, _: FamilyId
) -> s.ParentAnswersOut:
    with logged(family_id):
        out = _guard(lambda: svc.answers(family_id, n, [a.model_dump() for a in body.answers]))
    return s.ParentAnswersOut(safety=out["safety"], next=out["next"])


@router.get("/families/{family_id}/pack", tags=["parent"])
def get_pack(family_id: str, svc: Service, _: FamilyId) -> s.ParentPack:
    with logged(family_id):
        return _guard(lambda: svc.pack(family_id))


@router.post("/families/{family_id}/documents", tags=["parent"])
def post_document(
    family_id: str, body: s.ParentDocumentIn, svc: Service, _: FamilyId
) -> s.ParentExtractionOut:
    with logged(family_id):
        return _guard(
            lambda: svc.add_document(family_id, body.kind, body.text, body.content_base64)
        )


@router.post("/families/{family_id}/advance", tags=["parent"])
def post_advance(family_id: str, svc: Service, _: FamilyId) -> s.ParentState:
    """Demo button: "6 months later" (the watcher also runs on a daily schedule)."""
    with logged(family_id):
        return _guard(lambda: svc.advance(family_id, 6))


@router.get("/families/{family_id}/timeline", tags=["parent"])
def get_timeline(family_id: str, svc: Service, _: FamilyId) -> s.ParentTimeline:
    with logged(family_id):
        return _guard(lambda: svc.timeline(family_id))


@router.get("/families/{family_id}/constellation", tags=["parent"])
def get_constellation(family_id: str, svc: Service, _: FamilyId) -> s.ParentConstellation:
    with logged(family_id):
        return _guard(lambda: svc.constellation(family_id))


@router.delete("/families/{family_id}", status_code=204, tags=["parent"])
def delete_family(family_id: str, svc: Service, _: FamilyId) -> None:
    svc.delete_family(family_id)


@router.get("/clinician/{family_id}", tags=["clinician"])
def get_clinician(family_id: str, svc: Service, _: ClinicianFamilyId) -> s.ClinicianView:
    return _guard(lambda: svc.clinician(family_id))


@router.get("/clinician/{family_id}/phenopacket", tags=["clinician"])
def get_phenopacket(family_id: str, svc: Service, _: ClinicianFamilyId) -> s.PhenopacketOut:
    return s.PhenopacketOut(phenopacket=_guard(lambda: svc.phenopacket(family_id)))


def _centre_guard[T](fn: Callable[[], T]) -> T:
    try:
        return fn()
    except NotFound as exc:
        raise HTTPException(status_code=404, detail="not found") from exc
    except BadInput as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ResponseError as exc:  # centre graph not built yet
        raise HTTPException(
            status_code=503, detail="centre graph not loaded: run make centre"
        ) from exc


@router.get("/centre/overview", tags=["centre"])
def centre_overview(c: Centre) -> s.CentreOverview:
    return _centre_guard(c.overview)


@router.get("/centre/cases", tags=["centre"])
def centre_cases(c: Centre, status: str = "", limit: int = 50) -> list[s.CentreCaseRow]:
    return _centre_guard(lambda: [s.CentreCaseRow(**x) for x in c.cases(status, limit)])


@router.get("/centre/lookalikes", tags=["centre"])
def centre_lookalikes(c: Centre, case_id: str = "", terms: str = "") -> list[s.CentreLookalike]:
    """Look-alikes for a centre case (`case_id`) or for HPO ids (`terms`, comma separated)."""
    if case_id:
        return _centre_guard(lambda: c.routing(case_id).lookalikes)
    ids = [t.strip() for t in terms.split(",") if t.strip()]
    return _centre_guard(lambda: c.lookalikes_for(ids))


@router.get("/centre/routing/{case_id}", tags=["centre"])
def centre_routing(case_id: str, c: Centre) -> s.CentreRouting:
    return _centre_guard(lambda: c.routing(case_id))


@router.get("/centre/bridges", tags=["centre"])
def centre_bridges(c: Centre) -> list[s.CentreBridge]:
    return _centre_guard(c.bridges)


@router.get("/centre/clusters", tags=["centre"])
def centre_clusters(c: Centre, method: str = "lp") -> list[s.CentreCluster]:
    return _centre_guard(lambda: c.clusters(method))


@router.get("/centre/cases/{case_id}", tags=["centre"])
def centre_case(case_id: str, c: Centre) -> s.CentreCase:
    return _centre_guard(lambda: c.case(case_id))


@router.get("/centre/protocols", tags=["centre"])
def centre_protocols(c: Centre) -> list[s.CentreProtocolStat]:
    return _centre_guard(lambda: [s.CentreProtocolStat(**x) for x in c.protocols()])


@router.get("/centre/workload", tags=["centre"])
def centre_workload(c: Centre) -> list[s.CentreClinicianStat]:
    return _centre_guard(lambda: [s.CentreClinicianStat(**x) for x in c.workload()])


@router.get("/centre/notes", tags=["centre"])
def centre_notes(c: Centre, target: str = "") -> list[s.CentreNote]:
    return _centre_guard(lambda: [s.CentreNote(**n.model_dump()) for n in c.notes(target)])


@router.post("/centre/notes", tags=["centre"])
def centre_add_note(body: s.CentreNoteIn, c: Centre) -> s.CentreNote:
    return _centre_guard(
        lambda: s.CentreNote(**c.add_note(body.kind, body.target, body.text).model_dump())
    )


@router.get("/centre/inspector", tags=["centre"])
def centre_inspector(c: Centre) -> list[s.QueryLogEntry]:
    """The centre's recent graph queries (name, Cypher, params, rows, ms): no free text."""
    return c.inspector()


@router.post("/centre/ask", tags=["centre"])
def centre_ask(body: s.CentreAskIn, c: Centre) -> s.CentreAskOut:
    return _centre_guard(lambda: c.ask(body.question))


@router.post("/centre/whatif", tags=["centre"])
def centre_whatif(body: s.CentreWhatIfIn, c: Centre, request: Request) -> s.CentreWhatIfOut:
    host = request.client.host if request.client else "unknown"
    if not WHATIF_LIMIT.allow(host):
        raise HTTPException(status_code=429, detail="too many what-if runs")
    r = _centre_guard(lambda: c.whatif(body.new_kb_version, body.tau2))
    return s.CentreWhatIfOut(
        affected_cases=r.cases,
        summary=r.summary,
        from_version=r.from_version,
        to_version=r.to_version,
        tau2=r.tau2,
        rescored=r.rescored,
        details=[s.CentreWhatIfDetail(**d.model_dump()) for d in r.details],
        ms=r.ms,
        graph=r.graph,
    )


@router.get("/demo/journeys", tags=["demo"])
def demo_journeys() -> list[s.DemoJourney]:
    from app.agents.demo import JOURNEYS

    return [
        s.DemoJourney(id=jid, title=m["title"], blurb=m["blurb"]) for jid, m in JOURNEYS.items()
    ]


@router.get("/demo/{journey}/steps", tags=["demo"])
def demo_steps(journey: str) -> list[s.DemoStep]:
    """Recorded steps (no model, no key needed); each step carries its graph queries."""
    from app.agents.demo import JOURNEYS, load_demo

    if journey not in JOURNEYS:
        raise HTTPException(status_code=404, detail="no such example family")
    try:
        doc = load_demo(journey)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="demo not recorded yet") from exc
    return [s.DemoStep.model_validate(x) for x in doc["steps"]]


@router.get("/debug/queries", tags=["debug"])
def debug_queries(family_id: str, svc: Service, _: FamilyId) -> list[s.QueryLogEntry]:
    """Live inspector (demo families only): query name, Cypher, params without free text, ms."""
    if not is_demo(family_id):
        raise HTTPException(status_code=403, detail="inspector is for demo families only")
    return [
        s.QueryLogEntry(name=e.name, cypher=e.cypher, params=e.params, rows=e.rows, ms=e.ms)
        for e in query_log(family_id).entries
    ]
