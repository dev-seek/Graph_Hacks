from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.kb import info as kb_info
from app.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_without_kb(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(kb_info, "KB_INFO_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(
        "app.api.routes.load_kb_info", lambda: kb_info.load_kb_info(tmp_path / "missing.json")
    )
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json()["kb_label"] == "no kb"
    assert r.json()["kb"] is None


def test_version_with_kb(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "kb_info.json"
    p.write_text('{"release":"2026-01","hpo_version":"v1","hpoa_version":"v2"}')
    monkeypatch.setattr("app.api.routes.load_kb_info", lambda: kb_info.load_kb_info(p))
    assert client.get("/api/version").json()["kb_label"] == "2026-01"


def test_version_reports_all_data_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    p = tmp_path / "kb_info.json"
    p.write_text(
        '{"release":"kb_20260901","hpo_version":"2026-09-01","hpoa_version":"2026-09-02",'
        '"orpha_version":"2026-06-29","phenopacket_store_version":"0.1.27",'
        '"embedding_model":"BAAI/bge-small-en-v1.5"}'
    )
    monkeypatch.setattr("app.api.routes.load_kb_info", lambda: kb_info.load_kb_info(p))
    kb = client.get("/api/version").json()["kb"]
    assert kb["hpo_version"] == "2026-09-01" and kb["orpha_version"] == "2026-06-29"
    assert kb["phenopacket_store_version"] == "0.1.27"
    assert kb["embedding_model"] == "BAAI/bge-small-en-v1.5"
