"""phenotype.hpoa -> annotations. Frequencies follow spec §5; filters follow AGENTS.md rule 7."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from pydantic import BaseModel, Field

# HPO frequency terms -> value used (spec §5 table). HP:0040285 (excluded) is handled as NOT.
FREQ_TERMS: dict[str, float] = {
    "HP:0040280": 1.0,
    "HP:0040281": 0.90,
    "HP:0040282": 0.545,
    "HP:0040283": 0.17,
    "HP:0040284": 0.025,
}
EXCLUDED_TERM = "HP:0040285"
MISSING_FREQ = 0.5  # ADR-0003

_FRAC = re.compile(r"^(\d+)/(\d+)$")
_PCT = re.compile(r"^(\d+(?:\.\d+)?)%$")


class Annotation(BaseModel):
    disease_id: str
    hpo_id: str
    negated: bool
    freq: float
    freq_raw: str
    onset: str
    sex: str
    evidence: str
    reference: str
    aspect: str


class DiseaseRec(BaseModel):
    id: str
    name: str
    source: str
    inheritance: list[str] = Field(default_factory=list)
    onset_terms: list[str] = Field(default_factory=list)


class HpoaParse(BaseModel):
    version: str
    hpo_version: str
    annotations: list[Annotation]
    diseases: dict[str, DiseaseRec]
    stats: dict[str, int]


def parse_frequency(raw: str) -> tuple[float, bool]:
    """-> (value, excluded). Excluded means 0%: the annotation says the sign is NOT present."""
    raw = raw.strip()
    if not raw:
        return MISSING_FREQ, False
    if raw == EXCLUDED_TERM:
        return 0.0, True
    if raw in FREQ_TERMS:
        return FREQ_TERMS[raw], False
    if m := _FRAC.match(raw):
        num, den = int(m.group(1)), int(m.group(2))
        if den == 0:
            return MISSING_FREQ, False
        return (0.0, True) if num == 0 else (min(num / den, 1.0), False)
    if m := _PCT.match(raw):
        pct = float(m.group(1))
        return (0.0, True) if pct == 0 else (min(pct / 100.0, 1.0), False)
    return MISSING_FREQ, False


def parse_hpoa(path: Path, include_omim_iea: bool = False) -> HpoaParse:
    version = hpo_version = ""
    annotations: list[Annotation] = []
    diseases: dict[str, DiseaseRec] = {}
    stats: Counter[str] = Counter()
    header_seen = False
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            if line.startswith("#"):
                if line.startswith("#version:"):
                    version = line.split(":", 1)[1].strip()
                elif line.startswith("#hpo-version:"):
                    url = line.split(":", 1)[1].strip()
                    hpo_version = url.split("/releases/")[-1].split("/")[0]
                continue
            if not header_seen:
                header_seen = True
                if not line.startswith("database_id\t"):
                    raise ValueError("unexpected phenotype.hpoa header")
                continue
            c = line.split("\t")
            c += [""] * (12 - len(c))
            did, name, qual, hpo, ref, ev, onset, freq, sex, _mod, aspect = c[:11]
            stats["rows"] += 1
            source = did.split(":", 1)[0]
            rec = diseases.setdefault(did, DiseaseRec(id=did, name=name, source=source))
            if aspect == "I":
                rec.inheritance.append(hpo)
                continue
            if aspect == "C":
                rec.onset_terms.append(hpo)
                continue
            if aspect != "P":
                continue
            if source == "OMIM" and ev == "IEA" and not include_omim_iea:
                stats["dropped_omim_iea"] += 1
                continue
            value, excluded = parse_frequency(freq)
            negated = qual == "NOT" or excluded
            if negated:
                stats["negated"] += 1
            if excluded:
                stats["freq_zero_as_negated"] += 1
            annotations.append(
                Annotation(
                    disease_id=did,
                    hpo_id=hpo,
                    negated=negated,
                    freq=value,
                    freq_raw=freq,
                    onset=onset,
                    sex=sex,
                    evidence=ev,
                    reference=ref,
                    aspect=aspect,
                )
            )
    stats.setdefault("dropped_omim_iea", 0)
    stats.setdefault("negated", 0)
    stats.setdefault("freq_zero_as_negated", 0)
    return HpoaParse(
        version=version,
        hpo_version=hpo_version,
        annotations=annotations,
        diseases=diseases,
        stats=dict(stats),
    )
