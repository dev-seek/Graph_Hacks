"""hp.json (obographs) -> ontology records. HPO content is read, never altered."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field, PrivateAttr

from app.kb.ids import norm_hpo

_LAY = "http://purl.obolibrary.org/obo/hp#layperson"
_ALT = "http://www.geneontology.org/formats/oboInOwl#hasAlternativeId"
_REPLACED_BY = "http://purl.obolibrary.org/obo/IAO_0100001"
_VERSION = "http://www.w3.org/2002/07/owl#versionInfo"


class TermRec(BaseModel):
    id: str
    name: str
    definition: str | None = None
    synonyms: list[str] = Field(default_factory=list)
    lay_synonyms: list[str] = Field(default_factory=list)
    is_obsolete: bool = False
    replaced_by: str | None = None
    alt_ids: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)


class Ontology(BaseModel):
    version: str
    terms: dict[str, TermRec]
    _alt: dict[str, str] | None = PrivateAttr(default=None)

    def resolve(self, term_id: str) -> str | None:
        """Map an alt id or an obsolete id to the live term id (None if unknown/dead end)."""
        for _ in range(5):
            rec = self.terms.get(term_id)
            if rec is None:
                alt = self._alt_index().get(term_id)
                if alt is None:
                    return None
                term_id = alt
                continue
            if not rec.is_obsolete:
                return rec.id
            if rec.replaced_by is None:
                return None
            term_id = rec.replaced_by
        return None

    def _alt_index(self) -> dict[str, str]:
        if self._alt is None:
            self._alt = {
                a: r.id for r in self.terms.values() if not r.is_obsolete for a in r.alt_ids
            }
        return self._alt


def parse_hp_json(path: Path, prefix: str = "HP") -> Ontology:
    graph = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8"))["graphs"][0])
    meta = cast(dict[str, Any], graph.get("meta", {}))
    version = ""
    for bpv in meta.get("basicPropertyValues", []):
        if bpv.get("pred") == _VERSION:
            version = str(bpv["val"])
    terms: dict[str, TermRec] = {}
    for node in graph["nodes"]:
        if node.get("type") != "CLASS" or f"{prefix}_" not in node["id"]:
            continue
        try:
            tid = norm_hpo(node["id"])
        except ValueError:
            continue
        if not tid.startswith(f"{prefix}:"):
            continue
        nmeta = node.get("meta", {})
        syn: list[str] = []
        lay: list[str] = []
        for s in nmeta.get("synonyms", []):
            (lay if s.get("synonymType") == _LAY else syn).append(s["val"])
        alts: list[str] = []
        replaced: str | None = None
        for bpv in nmeta.get("basicPropertyValues", []):
            if bpv["pred"] == _ALT:
                alts.append(bpv["val"])
            elif bpv["pred"] == _REPLACED_BY:
                replaced = bpv["val"]
        terms[tid] = TermRec(
            id=tid,
            name=node.get("lbl", ""),
            definition=nmeta.get("definition", {}).get("val"),
            synonyms=syn,
            lay_synonyms=lay,
            is_obsolete=bool(nmeta.get("deprecated", False)),
            replaced_by=replaced,
            alt_ids=alts,
        )
    for edge in graph["edges"]:
        if edge.get("pred") != "is_a":
            continue
        try:
            child, parent = norm_hpo(edge["sub"]), norm_hpo(edge["obj"])
        except ValueError:
            continue
        if child in terms and parent in terms:
            terms[child].parents.append(parent)
    if not version:
        version = str(meta.get("version", "")).split("/releases/")[-1].split("/")[0]
    return Ontology(version=version, terms=terms)
