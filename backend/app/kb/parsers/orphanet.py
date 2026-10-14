"""Orphanet product 9 (prevalence -> priors) and product 1 (ORPHA<->OMIM alignments)."""

# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
import re
import tarfile
import xml.etree.ElementTree as ET  # noqa: S405 - pinned, checksummed public file
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from app.kb.ids import norm_disease

PRIORS: dict[str, float] = {
    ">1 / 1000": 1.5e-3,
    "6-9 / 10000": 7.5e-4,
    "1-5 / 10000": 3e-4,
    "1-9 / 100000": 5e-5,
    "1-9 / 1000000": 5e-6,
    "<1 / 1000000": 5e-7,
    "Unknown": 1e-6,
}
_GEO_OK = {"Worldwide", "Europe"}


class Prevalence(BaseModel):
    prevalence_class: str
    prior: float


class Equivalence(BaseModel):
    orpha_id: str
    omim_id: str
    relation: str


class Product1(BaseModel):
    version: str
    orpha: dict[str, str]
    equivalences: list[Equivalence]


def _norm_class(raw: str) -> str:
    text = re.sub(r"(?<=\d)[\s ]+(?=\d)", "", raw.strip())  # '1 000 000' -> '1000000'
    return text if text in PRIORS else "Unknown"


def parse_prevalence(path: Path) -> dict[str, Prevalence]:
    out: dict[str, Prevalence] = {}
    for _, el in ET.iterparse(path):  # noqa: S314
        if el.tag != "Disorder":
            continue
        code = (el.findtext("OrphaCode") or "").strip()
        best: tuple[tuple[int, int, float], str] | None = None
        for p in el.findall("PrevalenceList/Prevalence"):
            if (p.findtext("PrevalenceType/Name") or "") != "Point prevalence":
                continue
            cls = _norm_class(p.findtext("PrevalenceClass/Name") or "")
            geo_ok = (p.findtext("PrevalenceGeographic/Name") or "") in _GEO_OK
            validated = (p.findtext("PrevalenceValidationStatus/Name") or "") == "Validated"
            key = (int(validated), int(geo_ok), PRIORS[cls])
            if best is None or key > best[0]:
                best = (key, cls)
        cls = best[1] if best else "Unknown"
        if code:
            out[norm_disease("ORPHA", code)] = Prevalence(prevalence_class=cls, prior=PRIORS[cls])
        el.clear()
    return out


def _first_label(node: Any) -> str:
    """Orphanet's JSON wraps every field in single-item lists: Name[0].label."""
    if isinstance(node, list) and node:
        node = node[0]
    if isinstance(node, dict):
        name = cast(dict[str, Any], node).get("Name", node)
        if isinstance(name, list) and name:
            name = name[0]
        if isinstance(name, dict):
            return str(cast(dict[str, Any], name).get("label", ""))
    return ""


def parse_product1(path: Path) -> Product1:
    with tarfile.open(path, "r:gz") as tar:
        member = next(m for m in tar.getmembers() if m.name.endswith(".json"))
        fh = tar.extractfile(member)
        assert fh is not None  # noqa: S101
        data = json.load(fh)
    root = data["JDBOR"][0]
    names: dict[str, str] = {}
    eq: list[Equivalence] = []
    for lst in root["DisorderList"]:
        for dis in lst["Disorder"]:
            oid = norm_disease("ORPHA", str(dis["OrphaCode"]))
            names[oid] = _first_label(dis.get("Name"))
            for ref_list in dis.get("ExternalReferenceList", []):
                for ref in ref_list.get("ExternalReference", []):
                    if ref.get("Source") != "OMIM":
                        continue
                    label = _first_label(ref.get("DisorderMappingRelation"))
                    relation = label.split(" ", 1)[0] if label else ""
                    eq.append(
                        Equivalence(
                            orpha_id=oid,
                            omim_id=norm_disease("OMIM", str(ref["Reference"])),
                            relation=relation,
                        )
                    )
    return Product1(version=str(root.get("date", "")), orpha=names, equivalences=eq)
