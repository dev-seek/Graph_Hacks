"""Identifier normalisation (spec §5)."""

import pytest

from app.kb.ids import norm_disease, norm_hpo


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HP:0001250", "HP:0001250"),
        ("HP_0001250", "HP:0001250"),
        ("http://purl.obolibrary.org/obo/HP_0001250", "HP:0001250"),
        ("TEST:0001", "TEST:0001"),
        ("TEST_0001", "TEST:0001"),
        ("http://purl.obolibrary.org/obo/TEST_0001", "TEST:0001"),
    ],
)
def test_norm_hpo_accepts_curie_underscore_and_iri_forms(raw: str, expected: str) -> None:
    assert norm_hpo(raw) == expected


@pytest.mark.parametrize(
    ("source", "code", "expected"),
    [
        ("ORPHA", "123", "ORPHA:123"),
        ("Orphanet", "123", "ORPHA:123"),
        ("ORPHANET", "123", "ORPHA:123"),
        ("orpha", "ORPHA:123", "ORPHA:123"),
        ("ORPHA", "orphanet:123", "ORPHA:123"),
        ("OMIM", "123456", "OMIM:123456"),
        ("omim", "OMIM:123456", "OMIM:123456"),
    ],
)
def test_norm_disease_maps_sources_and_prefixed_codes(
    source: str, code: str, expected: str
) -> None:
    assert norm_disease(source, code) == expected


def test_norm_disease_raises_value_error_on_unknown_source() -> None:
    with pytest.raises(ValueError):
        norm_disease("MONDO", "0000001")
