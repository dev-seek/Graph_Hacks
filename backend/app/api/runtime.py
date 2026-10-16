"""API runtime: the lazily built `FamilyService`, auth dependencies, rate limits, query logs."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from langchain_falkordb.checkpoint import FalkorDBSaver

from app.agents.deps import AgentDeps
from app.agents.service import BadRequest, FamilyNotFound, FamilyService
from app.api.ratelimit import RateLimiter
from app.graph.client import QueryLog, set_query_log

FAMILY_LIMIT = RateLimiter(120, 60.0)  # per token per minute
CREATE_LIMIT = RateLimiter(int(os.environ.get("CREATE_LIMIT_PER_HOUR") or 10), 3600.0)  # per client
CLINICIAN_LIMIT = RateLimiter(60, 60.0)
_demo: dict[str, bool] = {}
_logs: dict[str, QueryLog] = {}


@lru_cache(maxsize=1)
def _service() -> FamilyService:
    host = os.environ.get("FALKORDB_HOST") or "localhost"
    port = int(os.environ.get("FALKORDB_PORT") or 6379)
    saver = FalkorDBSaver(host=host, port=port, database="langgraph_checkpoints")
    return FamilyService(AgentDeps.build(), saver)


def get_service() -> FamilyService:
    return _service()


Service = Annotated[FamilyService, Depends(get_service)]


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing family token")
    return authorization[7:].strip()


def family_auth(
    family_id: str,
    svc: Service,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    token = _bearer(authorization)
    if not FAMILY_LIMIT.allow(token[:16]):
        raise HTTPException(status_code=429, detail="too many requests")
    if not svc.authenticate(family_id, token):
        raise HTTPException(status_code=401, detail="invalid family token")  # same for unknown id
    _demo[family_id] = svc.deps.repo(family_id).auth_full()[2]  # valid token: graph exists
    return family_id


def clinician_auth(
    family_id: str,
    svc: Service,
    x_clinician_code: Annotated[str, Header(alias="X-Clinician-Code")],
) -> str:
    if not CLINICIAN_LIMIT.allow(family_id):
        raise HTTPException(status_code=429, detail="too many requests")
    if not svc.clinician_ok(family_id, x_clinician_code):
        raise HTTPException(status_code=401, detail="invalid clinician code")
    return family_id


def create_allowed(request: Request) -> None:
    host = request.client.host if request.client else "unknown"
    if not CREATE_LIMIT.allow(host):
        raise HTTPException(status_code=429, detail="too many new families from this address")


FamilyId = Annotated[str, Depends(family_auth)]
ClinicianFamilyId = Annotated[str, Depends(clinician_auth)]


@contextmanager
def logged(family_id: str) -> Generator[None]:
    """Record graph queries for demo families only (live inspector, spec §12)."""
    if _demo.get(family_id):
        set_query_log(_logs.setdefault(family_id, QueryLog()))
    try:
        yield
    finally:
        set_query_log(None)


def query_log(family_id: str) -> QueryLog:
    return _logs.setdefault(family_id, QueryLog())


def is_demo(family_id: str) -> bool:
    return _demo.get(family_id, False)


def to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, FamilyNotFound):
        return HTTPException(status_code=404, detail="not found")
    if isinstance(exc, BadRequest):
        return HTTPException(status_code=409, detail=str(exc))
    raise exc
