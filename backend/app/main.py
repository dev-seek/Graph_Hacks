from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.contract import router as contract_router
from app.api.routes import router
from app.api.runtime import get_service
from app.engine.reasoner import GraphUnavailable

log = structlog.get_logger("api")
WATCHER_INTERVAL_S = int(os.environ.get("WATCHER_INTERVAL_S") or 0)  # 0 = off (86400 = daily)


async def _watch_loop() -> None:
    while True:
        await asyncio.sleep(WATCHER_INTERVAL_S)
        try:
            await asyncio.to_thread(get_service().watch_all)
        except Exception:  # noqa: BLE001 (the watcher must never take the API down)
            log.exception("watcher_failed")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    task = asyncio.create_task(_watch_loop()) if WATCHER_INTERVAL_S > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Constellation API", version="0.1.0", lifespan=lifespan)
app.include_router(router)
app.include_router(contract_router)


@app.exception_handler(GraphUnavailable)
def graph_unavailable(_request: Request, exc: GraphUnavailable) -> JSONResponse:
    """Fail closed (spec §7): without FalkorDB there is no fallback path."""
    return JSONResponse(status_code=503, content={"detail": "knowledge graph unavailable"})
