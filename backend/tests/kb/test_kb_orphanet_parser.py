"""Orphanet product 9 (prevalence) and product 1 (cross references) parsers."""

from pathlib import Path

import pytest

from app.kb.parsers.orphanet import parse_prevalence, parse_product1

FIX = Path(__file__).resolve().parents[3] / "data" / "fixtures"
P9 = FIX / "product9_mini.xml"
P1 = FIX / "product1_mini.json.tar.gz"


@pytest.fixture(scope="module")
def prev():
    return parse_prevalence(P9)


@pytest.fixture(scope="module")
def p1():
    return parse_product1(P1)


def test_prevalence_is_keyed_by_orpha_id_for_every_disorder(prev) -> None:
    assert set(prev) == {"ORPHA:900100", "ORPHA:900101", "ORPHA:900102", "ORPHA:900103"}


def test_prevalence_prefers_validated_worldwide_point_row_over_europe_unvalidated(prev) -> None:
    p = prev["ORPHA:900100"]
    assert p.prevalence_class == "1-9 / 100000"
    assert p.prior == pytest.approx(5e-5)


def test_prevalence_ignores_non_point_rows(prev) -> None:
    # the annual-incidence ">1 / 1000" row of 900100 must not win
    assert prev["ORPHA:900100"].prevalence_class != ">1 / 1000"


def test_prevalence_accepts_europe_row_without_validation_status(prev) -> None:
    p = prev["ORPHA:900101"]
    assert p.prevalence_class == "1-5 / 10000"
    assert p.prior == pytest.approx(3e-4)


def test_prevalence_unknown_class_and_empty_class_give_unknown_prior(prev) -> None:
    p = prev["ORPHA:900102"]
    assert p.prevalence_class == "Unknown"
    assert p.prior == pytest.approx(1e-6)


def test_prevalence_picks_higher_prior_among_two_validated_worldwide_rows(prev) -> None:
    p = prev["ORPHA:900103"]
    assert p.prevalence_class == ">1 / 1000"
    assert p.prior == pytest.approx(1.5e-3)


def test_prevalence_disorder_without_point_row_is_unknown(tmp_path: Path) -> None:
    xml = (
        '<?xml version="1.0"?><JDBOR date="2000-01-01 00:00:00"><DisorderList count="1">'
        '<Disorder id="1"><OrphaCode>1</OrphaCode><Name lang="en">d</Name>'
        '<PrevalenceList count="1"><Prevalence id="1"><PrevalenceType id="1">'
        '<Name lang="en">Annual incidence</Name></PrevalenceType>'
        '<PrevalenceClass id="1"><Name lang="en">&gt;1 / 1000</Name></PrevalenceClass>'
        "</Prevalence></PrevalenceList></Disorder></DisorderList></JDBOR>"
    )
    p = tmp_path / "p9.xml"
    p.write_text(xml)
    r = parse_prevalence(p)["ORPHA:1"]
    assert r.prevalence_class == "Unknown"
    assert r.prior == pytest.approx(1e-6)


@pytest.mark.parametrize(
    ("raw", "cls", "prior"),
    [
        ("&gt;1 / 1000", ">1 / 1000", 1.5e-3),
        ("6-9 / 10 000", "6-9 / 10000", 7.5e-4),
        ("1-5 / 10 000", "1-5 / 10000", 3e-4),
        ("1-9 / 100 000", "1-9 / 100000", 5e-5),
        ("1-9 / 1 000 000", "1-9 / 1000000", 5e-6),
        ("&lt;1 / 1 000 000", "<1 / 1000000", 5e-7),
    ],
)
def test_prevalence_class_strings_are_normalised_and_mapped_to_priors(
    tmp_path: Path, raw: str, cls: str, prior: float
) -> None:
    xml = (
        '<?xml version="1.0"?><JDBOR date="2000-01-01 00:00:00"><DisorderList count="1">'
        '<Disorder id="7"><OrphaCode>7</OrphaCode><Name lang="en">d</Name>'
        '<PrevalenceList count="1"><Prevalence id="1"><PrevalenceType id="1">'
        '<Name lang="en">Point prevalence</Name></PrevalenceType>'
        f'<PrevalenceClass id="1"><Name lang="en">{raw}</Name></PrevalenceClass>'
        '<PrevalenceGeographic id="1"><Name lang="en">Worldwide</Name></PrevalenceGeographic>'
        "</Prevalence></PrevalenceList></Disorder></DisorderList></JDBOR>"
    )
    p = tmp_path / "p9.xml"
    p.write_text(xml)
    r = parse_prevalence(p)["ORPHA:7"]
    assert r.prevalence_class == cls
    assert r.prior == pytest.approx(prior)


def test_product1_reads_version_date_string(p1) -> None:
    assert p1.version == "2000-01-01 00:00:00"


def test_product1_collects_names_for_all_disorders_including_those_without_references(p1) -> None:
    assert p1.orpha == {
        "ORPHA:900100": "Fixture orpha disease",
        "ORPHA:900101": "Fixture orpha two",
        "ORPHA:900102": "Fixture orpha three",
    }


def test_product1_equivalences_keep_only_omim_references_with_bare_relation_code(p1) -> None:
    got = sorted((e.orpha_id, e.omim_id, e.relation) for e in p1.equivalences)
    assert got == [
        ("ORPHA:900100", "OMIM:900001", "E"),
        ("ORPHA:900100", "OMIM:900002", "BTNT"),
        ("ORPHA:900101", "OMIM:900003", "NTBT"),
    ]
