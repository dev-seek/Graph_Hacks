from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.contract import router as contract_router
from app.api.routes import router
from app.engine.reasoner import GraphUnavailable

app = FastAPI(title="Constellation API", version="0.1.0")
app.include_router(router)
app.include_router(contract_router)


@app.exception_handler(GraphUnavailable)
def graph_unavailable(_request: Request, exc: GraphUnavailable) -> JSONResponse:
    """Fail closed (spec §7): without FalkorDB there is no fallback path."""
    return JSONResponse(status_code=503, content={"detail": "knowledge graph unavailable"})
