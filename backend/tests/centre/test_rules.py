"""Assignment rules for the illustrative clinic data (ADR-0014)."""

from __future__ import annotations

import random

from app.centre import rules


def test_clinician_follows_majority_system() -> None:
    systems = ["HP:0000707", "HP:0000707", "HP:0000478", None]
    assert rules.pick_clinician(systems) == "CL-A"


def test_clinician_tie_is_deterministic_and_default_when_unknown() -> None:
    assert rules.pick_clinician(["HP:0000707", "HP:0000478"]) == "CL-A"
    assert rules.pick_clinician(["HP:0000152", None]) == rules.DEFAULT_CLINICIAN
    assert rules.pick_clinician([]) == rules.DEFAULT_CLINICIAN


def test_protocol_keywords_and_fallbacks() -> None:
    assert rules.pick_protocol("Angelman syndrome", "CL-A").id == "PR-2"
    assert rules.pick_protocol("22q11.2 deletion syndrome", "CL-C").id == "PR-1"
    assert rules.pick_protocol("Leigh syndrome", "CL-A").id == "PR-7"
    assert rules.pick_protocol("Fragile X syndrome", "CL-A").id == "PR-6"
    assert rules.pick_protocol("Gaucher disease", "CL-B").id == "PR-5"
    assert rules.pick_protocol("Marfan syndrome", "CL-D").id == "PR-3"
    assert rules.pick_protocol("Rett syndrome", "CL-A").id == "PR-4"


def test_counts_match_spec() -> None:
    assert 6 <= len(rules.CLINICIANS) <= 8
    assert 5 <= len(rules.PROTOCOLS) <= 8


def test_turnaround_is_seeded_and_bounded() -> None:
    p = rules.PROTOCOLS[0]
    a = rules.turnaround_days(p, random.Random(1))  # noqa: S311
    assert a == rules.turnaround_days(p, random.Random(1))  # noqa: S311
    assert round(p.base_days * 0.7) <= a <= round(p.base_days * 1.3)


def test_age_band() -> None:
    assert rules.age_band(12) == "0-2y"
    assert rules.age_band(100) == "6-11y"
    assert rules.age_band(None) == "unknown"
