"""Phenopacket Store zip -> evaluation cases (diagnosis, present/excluded features, onset, age)."""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_DUR = re.compile(
    r"^P(?:(\d+(?:\.\d+)?)Y)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)W)?"
    r"(?:(\d+(?:\.\d+)?)D)?(?:T.*)?$"
)
_DAYS_PER_MONTH = 30.4375


def iso_duration_to_months(value: str | None) -> float | None:
    if not value or value == "P":
        return None
    m = _DUR.match(value)
    if not m:
        return None
    y, mo, w, d = (float(g) if g else 0.0 for g in m.groups())
    return y * 12 + mo + (w * 7 + d) / _DAYS_PER_MONTH


class Feature(BaseModel):
    term_id: str
    onset_months: float | None = None


class EvalCase(BaseModel):
    case_id: str
    pmid: str
    disease_id: str
    present: list[Feature] = Field(default_factory=list)
    excluded: list[Feature] = Field(default_factory=list)
    age_months: float | None = None
    sex: str | None = None


def _onset(feature: dict[str, Any]) -> float | None:
    onset = feature.get("onset")
    if not isinstance(onset, dict):
        return None
    age = onset.get("age")
    if isinstance(age, dict):
        return iso_duration_to_months(age.get("iso8601duration"))
    return None


def _case(doc: dict[str, Any]) -> EvalCase | None:
    interps = doc.get("interpretations") or []
    if not interps:
        return None
    disease = interps[0].get("diagnosis", {}).get("disease", {}).get("id")
    if not disease:
        return None
    pmid = next(
        (
            r["id"]
            for r in doc.get("metaData", {}).get("externalReferences", [])
            if str(r.get("id", "")).startswith("PMID:")
        ),
        "",
    )
    present: dict[str, Feature] = {}
    excluded: dict[str, Feature] = {}
    for f in doc.get("phenotypicFeatures", []):
        tid = f.get("type", {}).get("id")
        if not tid:
            continue
        target = excluded if f.get("excluded") else present
        target.setdefault(tid, Feature(term_id=tid, onset_months=_onset(f)))
    subject = doc.get("subject", {})
    age = subject.get("timeAtLastEncounter", {}).get("age", {})
    return EvalCase(
        case_id=str(doc.get("id", "")),
        pmid=pmid,
        disease_id=disease,
        present=list(present.values()),
        excluded=list(excluded.values()),
        age_months=iso_duration_to_months(age.get("iso8601duration")) if age else None,
        sex=subject.get("sex"),
    )


def parse_phenopackets(zip_path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    with zipfile.ZipFile(zip_path) as zf:
        for name in sorted(zf.namelist()):
            if not name.endswith(".json"):
                continue
            case = _case(json.loads(zf.read(name)))
            if case is not None:
                cases.append(case)
    return cases
