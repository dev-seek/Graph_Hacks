"""HPOA parser: frequency mapping, negation, OMIM IEA exclusion (AGENTS.md rule 7)."""

from pathlib import Path

import pytest

from app.kb.parsers.hpoa import parse_hpoa

FIXTURE = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "mini.hpoa"
HEADER = (
    "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\t"
    "frequency\tsex\tmodifier\taspect\tbiocuration\n"
)


def _hpoa(tmp_path: Path, rows: list[tuple[str, ...]]) -> Path:
    """Rows: (disease, qualifier, hpo, evidence, frequency, aspect)."""
    lines = ["#version: 2000-01-02\n", "#hpo-version: http://x/hp/releases/2000-01-01/hp.json\n"]
    lines.append(HEADER)
    for d, q, h, ev, fr, asp in rows:
        lines.append(f"{d}\tname\t{q}\t{h}\tPMID:1\t{ev}\t\t{fr}\t\t\t{asp}\tx\n")
    p = tmp_path / "t.hpoa"
    p.write_text("".join(lines))
    return p


def _freq(tmp_path: Path, raw: str):
    p = _hpoa(tmp_path, [("OMIM:1", "", "TEST:0011", "TAS", raw, "P")])
    (a,) = parse_hpoa(p).annotations
    return a


@pytest.fixture(scope="module")
def parsed():
    return parse_hpoa(FIXTURE)


def _find(parsed, disease: str, hpo: str):
    (a,) = [x for x in parsed.annotations if x.disease_id == disease and x.hpo_id == hpo]
    return a


def test_hpoa_versions_are_read_from_header_comments(parsed) -> None:
    assert parsed.version == "2000-01-02"
    assert parsed.hpo_version == "2000-01-01"


def test_hpoa_drops_omim_iea_rows_by_default_and_counts_them(parsed) -> None:
    assert parsed.stats["rows"] == 13
    assert parsed.stats["dropped_omim_iea"] == 2
    assert len(parsed.annotations) == 9
    assert not [a for a in parsed.annotations if a.disease_id == "OMIM:900002"]
    assert not [
        a for a in parsed.annotations if a.disease_id == "OMIM:900001" and a.hpo_id == "TEST:0040"
    ]


def test_hpoa_keeps_omim_iea_rows_when_flag_true() -> None:
    p = parse_hpoa(FIXTURE, include_omim_iea=True)
    assert p.stats["dropped_omim_iea"] == 0
    assert len(p.annotations) == 11
    a = [x for x in p.annotations if x.disease_id == "OMIM:900002"]
    assert len(a) == 1
    assert a[0].freq == pytest.approx(0.5)
    assert a[0].freq_raw == "50%"


def test_hpoa_keeps_non_omim_iea_rows(tmp_path: Path) -> None:
    p = parse_hpoa(
        _hpoa(
            tmp_path,
            [
                ("ORPHA:5", "", "TEST:0011", "IEA", "", "P"),
                ("DECIPHER:5", "", "TEST:0011", "IEA", "", "P"),
                ("OMIM:5", "", "TEST:0011", "IEA", "", "P"),
                ("OMIM:5", "", "TEST:0012", "PCS", "", "P"),
            ],
        )
    )
    got = sorted((a.disease_id, a.hpo_id) for a in p.annotations)
    assert got == [("DECIPHER:5", "TEST:0011"), ("OMIM:5", "TEST:0012"), ("ORPHA:5", "TEST:0011")]
    assert p.stats["dropped_omim_iea"] == 1


def test_hpoa_annotation_fields_for_fully_specified_row(parsed) -> None:
    a = _find(parsed, "OMIM:900001", "TEST:0021")
    assert a.negated is False
    assert a.freq == pytest.approx(0.75)
    assert a.freq_raw == "3/4"
    assert a.onset == "HP:0003577"
    assert a.evidence == "TAS"
    assert a.reference == "PMID:1001;PMID:1002"
    assert a.aspect == "P"
    assert a.sex == ""


def test_hpoa_not_qualifier_marks_annotation_negated(parsed) -> None:
    assert _find(parsed, "OMIM:900001", "TEST:0031").negated is True


def test_hpoa_frequency_term_maps_to_value_and_keeps_raw(parsed) -> None:
    a = _find(parsed, "OMIM:900001", "TEST:0011")
    assert a.freq == pytest.approx(0.90)
    assert a.freq_raw == "HP:0040281"


def test_hpoa_zero_over_n_is_negated_and_counted(parsed) -> None:
    a = _find(parsed, "ORPHA:900100", "TEST:0031")
    assert a.negated is True
    assert a.freq_raw == "0/3"
    assert parsed.stats["freq_zero_as_negated"] >= 1


def test_hpoa_excluded_frequency_term_is_negated(parsed) -> None:
    assert _find(parsed, "ORPHA:900100", "TEST:0021").negated is True


def test_hpoa_zero_denominator_is_treated_as_missing(parsed) -> None:
    a = _find(parsed, "ORPHA:900100", "TEST:0011")
    assert a.negated is False
    assert a.freq == pytest.approx(0.5)
    assert a.freq_raw == "5/0"


def test_hpoa_negated_stat_counts_all_negated_kept_rows(parsed) -> None:
    assert parsed.stats["negated"] == 3
    assert sum(a.negated for a in parsed.annotations) == 3


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HP:0040280", 1.0),
        ("HP:0040281", 0.90),
        ("HP:0040282", 0.545),
        ("HP:0040283", 0.17),
        ("HP:0040284", 0.025),
        ("1/2", 0.5),
        ("7/10", 0.7),
        ("12%", 0.12),
        ("100%", 1.0),
        ("", 0.5),
    ],
)
def test_hpoa_frequency_values(tmp_path: Path, raw: str, expected: float) -> None:
    a = _freq(tmp_path, raw)
    assert a.freq == pytest.approx(expected)
    assert a.negated is False
    assert a.freq_raw == raw


@pytest.mark.parametrize("raw", ["HP:0040285", "0/5", "0%"])
def test_hpoa_zero_like_frequencies_are_negated(tmp_path: Path, raw: str) -> None:
    assert _freq(tmp_path, raw).negated is True


def test_hpoa_only_phenotype_aspect_rows_become_annotations(parsed) -> None:
    assert {a.aspect for a in parsed.annotations} == {"P"}
    assert not [a for a in parsed.annotations if a.hpo_id in ("HP:0000006", "HP:0003577")]


def test_hpoa_diseases_include_every_id_seen_even_if_all_rows_dropped(parsed) -> None:
    assert set(parsed.diseases) == {
        "OMIM:900001",
        "OMIM:900002",
        "ORPHA:900100",
        "DECIPHER:900",
    }


def test_hpoa_disease_record_has_name_source_inheritance_and_onset(parsed) -> None:
    d = parsed.diseases["OMIM:900001"]
    assert d.id == "OMIM:900001"
    assert d.name == "Fixture disease one"
    assert d.source == "OMIM"
    assert d.inheritance == ["HP:0000006"]
    assert d.onset_terms == ["HP:0003577"]


def test_hpoa_disease_without_i_or_c_rows_has_empty_lists(parsed) -> None:
    d = parsed.diseases["ORPHA:900100"]
    assert d.source == "ORPHA"
    assert d.inheritance == []
    assert d.onset_terms == []
    assert parsed.diseases["DECIPHER:900"].source == "DECIPHER"
