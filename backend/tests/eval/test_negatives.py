from __future__ import annotations

from dataclasses import dataclass

from app.eval.negatives import load_negatives, resolve_negatives


@dataclass
class Hit:
    id: str
    name: str


class FakeResolver:
    def resolve(self, text: str, k: int = 3) -> list[Hit]:
        return [] if "zzz" in text else [Hit("HP:1", text.upper()), Hit("HP:2", "other")]


def test_real_negatives_file_has_40_cases_and_both_expectations() -> None:
    cases = load_negatives()
    assert len(cases) == 40
    assert {c.expected for c in cases} == {"no_escalation", "see_doctor_ok"}
    assert all(c.present for c in cases)


def test_resolve_takes_top_hit_and_keeps_alternatives() -> None:
    cases = load_negatives()[:1]
    out = resolve_negatives(cases, FakeResolver())
    s = out[0].present[0]
    assert s.term == "HP:1" and s.alternatives == ["HP:2 other"]


def test_unresolved_phrase_is_kept_with_none() -> None:
    case = load_negatives()[0].model_copy(update={"present": ["zzz"], "absent": []})
    out = resolve_negatives([case], FakeResolver())
    assert out[0].present[0].term is None


def test_curated_overrides_win_and_null_drops_the_phrase() -> None:
    case = load_negatives()[0].model_copy(update={"present": ["a", "b", "c"], "absent": []})
    curated = {"present": {"a": "HP:9", "b": None}, "absent": {}}
    out = resolve_negatives([case], FakeResolver(), curated, {"HP:9": "Nine"})
    a, b, c = out[0].present
    assert (a.term, a.name, a.via) == ("HP:9", "Nine", "curated")
    assert (b.term, b.via) == (None, "dropped")
    assert c.via == "auto" and c.term == "HP:1"


def test_curated_file_covers_every_phrase_in_the_negatives_file() -> None:
    from app.eval.negatives import load_curated

    cur = load_curated()
    for c in load_negatives():
        assert all(p in cur["present"] for p in c.present), c.id
        assert all(p in cur["absent"] for p in c.absent), c.id
