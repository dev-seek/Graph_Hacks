"""prepare(): fixture files -> graph rows (pure, no FalkorDB)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.kb.build import KbData, prepare
from app.kb.parsers.hp import parse_hp_json
from app.kb.parsers.hpoa import parse_hpoa
from app.kb.parsers.orphanet import parse_prevalence, parse_product1

FIX = Path(__file__).resolve().parents[3] / "data" / "fixtures"
ROOT = "TEST:0002"


def build(**kw: object) -> KbData:
    return prepare(
        parse_hp_json(FIX / "hp_mini.json", "TEST"),
        parse_hpoa(FIX / "mini.hpoa"),
        parse_prevalence(FIX / "product9_mini.xml"),
        parse_product1(FIX / "product1_mini.json.tar.gz"),
        pheno_root=ROOT,
        **kw,  # type: ignore[arg-type]
    )


@pytest.fixture(scope="module")
def data() -> KbData:
    return build()


def test_obsolete_terms_are_not_written(data: KbData) -> None:
    ids = {t["id"] for t in data.terms}
    assert "TEST:0032" not in ids and "TEST:0011" in ids
    assert data.stats["terms_obsolete_skipped"] == 1


def test_depth_system_and_labels_on_phenotype_terms(data: KbData) -> None:
    seizure = next(t for t in data.terms if t["id"] == "TEST:0012")
    assert seizure["depth"] == 3 and seizure["cx_system"] == "TEST:0010"
    assert seizure["cx_obs"] in {"home", "exam", "test"} and seizure["cx_label_source"] == "rules"
    root = next(t for t in data.terms if t["id"] == "TEST:0001")
    assert root["depth"] == -1 and "cx_system" not in root


def test_bg_ic_present_and_bounded(data: KbData) -> None:
    for t in data.terms:
        if "bg" in t:
            assert 1e-4 <= t["bg"] <= 1.0 and t["ic"] >= 0.0


def test_priors_from_prevalence_and_bridge(data: KbData) -> None:
    d = {r["id"]: r for r in data.diseases}
    assert d["ORPHA:900100"]["prior"] == 5e-5
    assert d["OMIM:900001"]["prior"] == 5e-5  # exact ORPHA equivalent supplies the prior
    assert d["OMIM:900002"]["prior"] == 1e-6  # BTNT is not exact -> unknown
    assert d["ORPHA:900100"]["omim_ids"] == ["OMIM:900001"]
    assert d["OMIM:900001"]["inheritance"] == ["HP:0000006"]  # id kept when not in ontology


def test_equivalent_to_keeps_relation_and_both_ends(data: KbData) -> None:
    rel = {(e["a"], e["b"]): e["relation"] for e in data.equivalent_to}
    assert rel[("ORPHA:900100", "OMIM:900001")] == "E"
    assert rel[("ORPHA:900100", "OMIM:900002")] == "BTNT"
    assert rel[("ORPHA:900101", "OMIM:900003")] == "NTBT"


def test_negated_annotations_become_lacks_edges(data: KbData) -> None:
    lacks = {(r["d"], r["t"]) for r in data.lacks_phenotype}
    assert ("OMIM:900001", "TEST:0031") in lacks
    assert not any((r["d"], r["t"]) == ("OMIM:900001", "TEST:0031") for r in data.has_phenotype)


def test_omim_iea_rows_dropped_so_disease_two_is_unscored(data: KbData) -> None:
    assert "OMIM:900002" in {d["id"] for d in data.diseases}
    assert "OMIM:900002" not in {r["d"] for r in data.has_phenotype}


def test_lpo_drops_rows_citing_excluded_pmids() -> None:
    lpo = build(exclude_pmids=frozenset({"PMID:1002"}))
    assert lpo.stats["annotations_lpo_dropped"] == 1  # token match inside 'PMID:1001;PMID:1002'
    assert len(lpo.has_phenotype) == len(build().has_phenotype) - 1
