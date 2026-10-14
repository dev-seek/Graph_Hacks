from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.kb.info import KbInfo, load_kb_info

router = APIRouter(prefix="/api")

APP_VERSION = "0.1.0"


class Health(BaseModel):
    status: str


class Version(BaseModel):
    app: str
    kb: KbInfo | None
    kb_label: str


@router.get("/health")
def health() -> Health:
    return Health(status="ok")


@router.get("/version")
def version() -> Version:
    info = load_kb_info()
    return Version(app=APP_VERSION, kb=info, kb_label=info.release if info else "no kb")
