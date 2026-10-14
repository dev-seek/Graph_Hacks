"""Phenopacket Store parser, on a zip built in the test (structure: docs/VERIFIED.md)."""

import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from app.kb.parsers.phenopackets import iso_duration_to_months, parse_phenopackets


def _packet(
    pid: str,
    *,
    pmid: str | None = "PMID:36996813",
    disease: str | None = "OMIM:620371",
    features: list[dict[str, Any]] | None = None,
    age: str | None = None,
    sex: str | None = "MALE",
) -> dict[str, Any]:
    subject: dict[str, Any] = {"id": pid}
    if sex:
        subject["sex"] = sex
    if age:
        subject["timeAtLastEncounter"] = {"age": {"iso8601duration": age}}
    doc: dict[str, Any] = {
        "id": pid,
        "subject": subject,
        "phenotypicFeatures": features or [],
        "metaData": {"externalReferences": [{"id": pmid}] if pmid else []},
    }
    if disease:
        doc["interpretations"] = [{"diagnosis": {"disease": {"id": disease, "label": "x"}}}]
    return doc


def _feat(tid: str, *, excluded: bool = False, onset: dict[str, Any] | None = None) -> dict:
    f: dict[str, Any] = {"type": {"id": tid, "label": tid}}
    if excluded:
        f["excluded"] = True
    if onset is not None:
        f["onset"] = onset
    return f


def _dur(s: str) -> dict[str, Any]:
    return {"age": {"iso8601duration": s}}


@pytest.fixture
def cases(tmp_path: Path):
    docs = {
        "0.1.27/GENE1/a.json": _packet(
            "PMID_36996813_A",
            age="P5Y",
            features=[
                _feat("HP:0001250", onset=_dur("P2Y3M")),
                _feat("HP:0000007", onset=_dur("P10D")),
                _feat("HP:0000008", onset=_dur("P1Y")),
                _feat("HP:0000009", onset={"ontologyClass": {"id": "HP:0003577", "label": "c"}}),
                _feat("HP:0000010"),
                _feat("HP:0001250"),  # duplicate term
                _feat("HP:0000011", excluded=True),
            ],
        ),
        "0.1.27/GENE1/b.json": _packet("PMID_36996813_B", disease=None),
        "0.1.27/GENE2/c.json": _packet(
            "PMID_111_C",
            pmid="PMID:111",
            disease="OMIM:100100",
            sex=None,
            features=[_feat("HP:0000020")],
        ),
    }
    z = tmp_path / "all.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("0.1.27/", "")
        zf.writestr("0.1.27/GENE1/", "")
        for name, d in docs.items():
            zf.writestr(name, json.dumps(d))
    return {c.case_id: c for c in parse_phenopackets(z)}


def test_cases_without_interpretations_are_skipped(cases) -> None:
    assert len(cases) == 2
    assert "PMID_36996813_B" not in cases


def test_case_carries_pmid_and_omim_disease_id(cases) -> None:
    c = cases["PMID_36996813_A"]
    assert c.pmid == "PMID:36996813"
    assert c.disease_id == "OMIM:620371"
    assert cases["PMID_111_C"].pmid == "PMID:111"
    assert cases["PMID_111_C"].disease_id == "OMIM:100100"


def test_present_features_exclude_excluded_and_deduplicate_term_ids(cases) -> None:
    c = cases["PMID_36996813_A"]
    ids = [f.term_id for f in c.present]
    assert sorted(ids) == sorted(set(ids))
    assert set(ids) == {"HP:0001250", "HP:0000007", "HP:0000008", "HP:0000009", "HP:0000010"}
    assert [f.term_id for f in c.excluded] == ["HP:0000011"]


def test_feature_onsets_are_converted_to_months(cases) -> None:
    on = {f.term_id: f.onset_months for f in cases["PMID_36996813_A"].present}
    assert on["HP:0001250"] == pytest.approx(27.0)
    assert on["HP:0000007"] == pytest.approx(0.33, abs=0.05)
    assert on["HP:0000008"] == pytest.approx(12.0)


def test_feature_onset_is_none_for_ontology_class_or_missing_onset(cases) -> None:
    on = {f.term_id: f.onset_months for f in cases["PMID_36996813_A"].present}
    assert on["HP:0000009"] is None
    assert on["HP:0000010"] is None


def test_age_comes_from_time_at_last_encounter(cases) -> None:
    assert cases["PMID_36996813_A"].age_months == pytest.approx(60.0)
    assert cases["PMID_111_C"].age_months is None


def test_sex_is_kept_when_present_and_none_when_absent(cases) -> None:
    assert str(cases["PMID_36996813_A"].sex).lower() == "male"
    assert cases["PMID_111_C"].sex is None


def test_zip_with_only_directories_gives_no_cases(tmp_path: Path) -> None:
    z = tmp_path / "e.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("0.1.27/", "")
    assert parse_phenopackets(z) == []


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("P2Y3M", 27.0), ("P1Y", 12.0), ("P6M", 6.0), ("P0D", 0.0), ("P1Y2M10D", 14.33)],
)
def test_iso_duration_to_months(raw: str, expected: float) -> None:
    assert iso_duration_to_months(raw) == pytest.approx(expected, abs=0.05)


def test_iso_duration_days_and_weeks_are_fractions_of_a_month() -> None:
    assert iso_duration_to_months("P10D") == pytest.approx(0.33, abs=0.05)
    assert iso_duration_to_months("P2W") == pytest.approx(0.46, abs=0.05)


@pytest.mark.parametrize("raw", ["", "garbage", "P", "2Y", "PXY", "P1X"])
def test_iso_duration_returns_none_for_bad_input(raw: str) -> None:
    assert iso_duration_to_months(raw) is None
