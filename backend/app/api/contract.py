"""API routes (spec §12). Request/response models are the frozen contract in `schemas.py`.

Parent routes sit behind the family bearer token, clinician routes behind the clinician code. The
centre and demo routes stay 501 until their phases wire them (P3 task 10, P5).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.agents.service import BadRequest, FamilyNotFound
from app.api import schemas as s
from app.api.runtime import (
    ClinicianFamilyId,
    FamilyId,
    Service,
    create_allowed,
    is_demo,
    logged,
    query_log,
    to_http,
)

router = APIRouter(prefix="/api")
Bearer = Annotated[str | None, Header(alias="Authorization")]


def _todo() -> NoReturn:
    raise HTTPException(status_code=501, detail="not implemented yet")


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


@router.get("/centre/overview", tags=["centre"])
def centre_overview() -> s.CentreOverview:
    _todo()


@router.get("/centre/lookalikes", tags=["centre"])
def centre_lookalikes() -> list[s.CentreLookalike]:
    _todo()


@router.get("/centre/routing/{case_id}", tags=["centre"])
def centre_routing(case_id: str) -> s.CentreRouting:
    _todo()


@router.get("/centre/bridges", tags=["centre"])
def centre_bridges() -> list[s.CentreBridge]:
    _todo()


@router.get("/centre/clusters", tags=["centre"])
def centre_clusters() -> list[s.CentreCluster]:
    _todo()


@router.get("/centre/cases/{case_id}", tags=["centre"])
def centre_case(case_id: str) -> s.CentreCase:
    _todo()


@router.post("/centre/ask", tags=["centre"])
def centre_ask(body: s.CentreAskIn) -> s.CentreAskOut:
    _todo()


@router.post("/centre/whatif", tags=["centre"])
def centre_whatif(body: s.CentreWhatIfIn) -> s.CentreWhatIfOut:
    _todo()


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
