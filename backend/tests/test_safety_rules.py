from app.safety.rules import Rule, load_rule_file, match

R = Rule(
    id="x",
    level="EMERGENCY",
    patterns=[r"\bseizure\b"],
    negations=[r"\bno seizure"],
    plain="p",
    source="s",
    max_age_months=3,
)


def test_fires_and_negation_cancels_in_same_sentence() -> None:
    assert match([R], "She had a seizure.")
    assert not match([R], "She had no seizure.")


def test_negation_in_other_sentence_does_not_cancel() -> None:
    assert match([R], "No seizure earlier. She had a seizure just now.")


def test_age_gate_and_unknown_age_stays_active() -> None:
    assert match([R], "seizure", age_months=2)
    assert not match([R], "seizure", age_months=30)
    assert match([R], "seizure", age_months=None)


def test_draft_file_corpus_is_self_consistent() -> None:
    rf = load_rule_file()
    for c in rf.corpus.should_flag:
        assert c.expect_id in [h.rule_id for h in match(rf.rules, c.text, c.age_months)], c.text
    for n in rf.corpus.should_not_flag:
        text, age = (n, None) if isinstance(n, str) else (n.text, n.age_months)
        assert not match(rf.rules, text, age), text


def test_emergency_sorted_first() -> None:
    rf = load_rule_file()
    hits = match(rf.rules, "He has no wet nappies and has lost his words", age_months=8)
    assert hits[0].level == "EMERGENCY"
