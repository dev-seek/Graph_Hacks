"""HPO obographs parser, run on the synthetic TEST fixture."""

from pathlib import Path

import pytest

from app.kb.parsers.hp import parse_hp_json

FIXTURE = Path(__file__).resolve().parents[3] / "data" / "fixtures" / "hp_mini.json"


@pytest.fixture(scope="module")
def onto():
    return parse_hp_json(FIXTURE, prefix="TEST")


def test_hp_version_is_read_from_version_info(onto) -> None:
    assert onto.version == "2000-01-01"


def test_hp_parser_keeps_only_nodes_with_requested_prefix_and_all_fixture_terms(onto) -> None:
    assert len(onto.terms) == 11
    assert all(t.startswith("TEST:") for t in onto.terms)


def test_hp_parser_with_other_prefix_finds_no_terms() -> None:
    assert parse_hp_json(FIXTURE, prefix="HP").terms == {}


def test_hp_term_has_name_definition_and_parent(onto) -> None:
    t = onto.terms["TEST:0011"]
    assert t.id == "TEST:0011"
    assert t.name == "Seizure"
    assert t.definition == "A synthetic seizure."
    assert t.parents == ["TEST:0010"]
    assert t.is_obsolete is False
    assert t.replaced_by is None


def test_hp_term_without_definition_has_none(onto) -> None:
    assert onto.terms["TEST:0012"].definition is None


def test_hp_layperson_synonyms_are_separated_from_ordinary_synonyms(onto) -> None:
    t = onto.terms["TEST:0011"]
    assert t.synonyms == ["Epileptic seizure"]
    assert sorted(t.lay_synonyms) == ["convulsion", "fit"]


def test_hp_root_term_has_no_parents_and_no_synonyms(onto) -> None:
    t = onto.terms["TEST:0001"]
    assert t.parents == []
    assert t.synonyms == []
    assert t.lay_synonyms == []
    assert t.alt_ids == []


def test_hp_alt_ids_are_recorded_on_the_live_term(onto) -> None:
    assert onto.terms["TEST:0011"].alt_ids == ["TEST:0013"]


def test_hp_obsolete_term_is_flagged_with_replacement(onto) -> None:
    t = onto.terms["TEST:0032"]
    assert t.is_obsolete is True
    assert t.replaced_by == "TEST:0031"


def test_resolve_returns_live_id_unchanged(onto) -> None:
    assert onto.resolve("TEST:0011") == "TEST:0011"


def test_resolve_maps_alt_id_to_live_term(onto) -> None:
    assert onto.resolve("TEST:0013") == "TEST:0011"


def test_resolve_maps_obsolete_term_to_its_replacement(onto) -> None:
    assert onto.resolve("TEST:0032") == "TEST:0031"


def test_resolve_returns_none_for_unknown_id(onto) -> None:
    assert onto.resolve("TEST:9999") is None
