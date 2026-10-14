"""Route stubs that fix the public contract (spec §12) before Phase 3 implements the handlers.

Every endpoint is declared with its request and response models so OpenAPI (and the generated
TypeScript types) are complete. Handlers answer 501 until Phase 3 wires the agents.
"""

from __future__ import annotations

from typing import Annotated, NoReturn

from fastapi import APIRouter, Header, HTTPException

from app.api import schemas as s

router = APIRouter(prefix="/api")
Bearer = Annotated[str | None, Header(alias="Authorization")]
ClinicianCode = Annotated[str, Header(alias="X-Clinician-Code")]


def _todo() -> NoReturn:
    raise HTTPException(status_code=501, detail="not implemented until Phase 3")


@router.post("/families", tags=["parent"])
def create_family() -> s.ParentFamilyCreated:
    _todo()


@router.post("/families/{family_id}/story", tags=["parent"])
def post_story(
    family_id: str, body: s.ParentStoryIn, authorization: Bearer = None
) -> s.ParentExtractionOut:
    _todo()


@router.post("/families/{family_id}/confirm", tags=["parent"])
def post_confirm(
    family_id: str, body: s.ParentConfirmIn, authorization: Bearer = None
) -> s.ParentState:
    _todo()


@router.get("/families/{family_id}/state", tags=["parent"])
def get_state(family_id: str, authorization: Bearer = None) -> s.ParentState:
    _todo()


@router.get("/families/{family_id}/round", tags=["parent"])
def get_round(family_id: str, authorization: Bearer = None) -> s.ParentRound:
    _todo()


@router.post("/families/{family_id}/round/{n}/answers", tags=["parent"])
def post_answers(
    family_id: str, n: int, body: s.ParentAnswersIn, authorization: Bearer = None
) -> s.ParentAnswersOut:
    _todo()


@router.get("/families/{family_id}/pack", tags=["parent"])
def get_pack(family_id: str, authorization: Bearer = None) -> s.ParentPack:
    _todo()


@router.post("/families/{family_id}/documents", tags=["parent"])
def post_document(
    family_id: str, body: s.ParentDocumentIn, authorization: Bearer = None
) -> s.ParentExtractionOut:
    _todo()


@router.get("/families/{family_id}/timeline", tags=["parent"])
def get_timeline(family_id: str, authorization: Bearer = None) -> s.ParentTimeline:
    _todo()


@router.get("/families/{family_id}/constellation", tags=["parent"])
def get_constellation(family_id: str, authorization: Bearer = None) -> s.ParentConstellation:
    _todo()


@router.delete("/families/{family_id}", status_code=204, tags=["parent"])
def delete_family(family_id: str, authorization: Bearer = None) -> None:
    _todo()


@router.get("/clinician/{family_id}", tags=["clinician"])
def get_clinician(family_id: str, x_clinician_code: ClinicianCode) -> s.ClinicianView:
    _todo()


@router.get("/clinician/{family_id}/phenopacket", tags=["clinician"])
def get_phenopacket(family_id: str, x_clinician_code: ClinicianCode) -> s.PhenopacketOut:
    _todo()


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
    _todo()


@router.get("/demo/{journey}/steps", tags=["demo"])
def demo_steps(journey: str) -> list[s.DemoStep]:
    _todo()


@router.get("/debug/queries", tags=["debug"])
def debug_queries(family_id: str) -> list[s.QueryLogEntry]:
    _todo()
