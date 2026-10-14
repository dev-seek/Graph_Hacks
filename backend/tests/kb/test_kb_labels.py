"""Tests for app.kb.labels.rule_label (rules-only labelling, spec 8.2)."""

from __future__ import annotations

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.kb.labels import rule_label

BLOOD = "Abnormality of blood and blood-forming tissues"
METAB = "Abnormality of metabolism/homeostasis"


@pytest.mark.parametrize(
    "name",
    [
        "Elevated serum creatinine level",
        "Increased urine lactate concentration",
        "Abnormal brain MRI",
        "Abnormal EEG",
        "Abnormal EMG",
        "Abnormal ECG",
        "Abnormal muscle biopsy",
        "Abnormal liver histology",
        "Abnormal imaging of the kidney",
        "Abnormal chest radiograph",
        "Abnormal chest X-ray",
        "Abnormal renal ultrasound",
        "Abnormal karyotype",
        "Reduced enzyme activity",
        "Low plasma carnitine",
    ],
)
def test_test_word_in_name_makes_term_a_test(name):
    assert rule_label(name, [], set()).cx_obs == "test"


@pytest.mark.parametrize("anc", [BLOOD, METAB])
def test_blood_or_metabolism_ancestor_makes_term_a_test(anc):
    assert rule_label("Anemia", [], {anc}).cx_obs == "test"


@pytest.mark.parametrize("name", ["Fatigue", "Pallor", "Easy bruising", "Jaundice", "Bleeding"])
@pytest.mark.parametrize("anc", [BLOOD, METAB])
def test_home_word_overrides_blood_or_metabolism_ancestor(name, anc):
    assert rule_label(name, [], {anc}).cx_obs == "home"


@pytest.mark.parametrize(
    "name",
    [
        "Head circumference above normal",
        "Short stature",
        "Tall height",
        "Weight loss",
        "High blood pressure",
        "Heart murmur",
        "Brisk reflexes",
        "Reduced muscle tone",
        "Hypotonia",
        "Hypertonia",
        "Hepatomegaly",
        "Splenomegaly",
        "Scoliosis",
        "High palate",
        "Dysmorphic facial features",
        "Macrocephaly",
        "Microcephaly",
    ],
)
def test_exam_word_in_name_makes_term_an_exam(name):
    assert rule_label(name, [], set()).cx_obs == "exam"


@pytest.mark.parametrize("name", ["Seizure", "Fever", "Frequent vomiting", "Poor appetite"])
def test_plain_symptom_without_special_words_is_home(name):
    assert rule_label(name, [], set()).cx_obs == "home"


@pytest.mark.parametrize(
    "name,age",
    [
        ("Delayed puberty", 108),
        ("Precocious pubertal development", 108),
        ("Absent menarche", 108),
        ("Delayed breast development", 108),
        ("Reading difficulty", 60),
        ("Poor school performance", 60),
        ("Learning disability", 60),
        ("Poor academic achievement", 60),
        ("Difficulty walking", 12),
        ("Abnormal gait", 12),
        ("Unable to run", 0),
        ("Running difficulty", 12),
        ("Unable to jump", 12),
        ("Fever", 0),
    ],
)
def test_min_age_months_follows_keyword_rules(name, age):
    assert rule_label(name, [], set()).cx_min_age_months == age


def test_puberty_wins_over_school_and_gait_keywords():
    label = rule_label("Delayed puberty with learning and gait problems", [], set())
    assert label.cx_min_age_months == 108


def test_school_wins_over_walking_keywords():
    assert rule_label("School problems with walking", [], set()).cx_min_age_months == 60


def test_plain_label_prefers_shortest_layperson_synonym_by_words_then_chars():
    label = rule_label("Seizure", ["Epilepsy", "fit"], set())
    assert label.cx_plain_label.lower() == "fit"


def test_plain_label_prefers_fewer_words_over_fewer_characters():
    label = rule_label("Seizure", ["a b c", "abcdefgh"], set())
    assert label.cx_plain_label.lower() == "abcdefgh"


def test_plain_label_ignores_synonyms_longer_than_eight_words():
    long_syn = "one two three four five six seven eight nine"
    label = rule_label("Seizure", [long_syn], set())
    assert label.cx_plain_label == "seizure"


def test_plain_label_falls_back_to_lowercased_name_without_synonyms():
    assert rule_label("Fatigue", [], set()).cx_plain_label == "fatigue"


def test_plain_label_never_exceeds_eight_words():
    name = "An extremely long phenotype name with far too many words in it"
    assert len(rule_label(name, [], set()).cx_plain_label.split()) <= 8


def test_lay_text_joins_synonyms_and_plain_label_deduplicated_case_insensitively():
    label = rule_label("Seizure", ["Fit", "fit", "Epilepsy"], set())
    parts = label.cx_lay_text.split(" | ")
    lowered = [p.lower() for p in parts]
    assert len(lowered) == len(set(lowered))
    assert {"fit", "epilepsy"} <= set(lowered)


def test_lay_text_is_plain_label_when_no_synonyms():
    label = rule_label("Fatigue", [], set())
    assert label.cx_lay_text == label.cx_plain_label


def test_label_source_is_rules():
    assert rule_label("Fever", [], set()).cx_label_source == "rules"


@pytest.mark.parametrize(
    "name,lay,anc",
    [
        ("Seizure", ["fit"], set()),
        ("Fever", [], set()),
        ("Hypotonia", ["floppiness"], set()),
        ("Elevated serum creatinine level", [], set()),
        ("Anemia", ["low blood count"], {BLOOD}),
        ("Delayed puberty", [], set()),
    ],
)
def test_question_is_a_short_plain_sentence_without_term_id(name, lay, anc):
    q = rule_label(name, lay, anc).cx_question
    assert q.strip() and q.endswith("?")
    assert len(q) <= 160
    assert "HP:" not in q


@pytest.mark.parametrize("name,lay", [("Seizure", ["fit"]), ("Fever", []), ("Poor appetite", [])])
def test_home_question_mentions_the_plain_label(name, lay):
    label = rule_label(name, lay, set())
    assert label.cx_obs == "home"
    assert label.cx_plain_label.lower() in label.cx_question.lower()


@pytest.mark.parametrize("name", ["Seizure", "Fever", "Poor appetite"])
def test_home_question_avoids_diagnostic_words(name):
    q = rule_label(name, [], set()).cx_question.lower()
    assert not re.search(r"diagnos|disease|syndrome", q)


def test_test_term_question_is_phrased_as_a_test_result():
    q = rule_label("Elevated serum creatinine level", [], set()).cx_question
    assert q.startswith("Has a test shown")
    assert q.endswith("?")


@pytest.mark.parametrize("name", ["Seizure", "Hypotonia", "Abnormal EEG", "Fever"])
def test_why_and_how_to_check_are_non_empty(name):
    label = rule_label(name, [], set())
    assert label.cx_why.strip()
    assert label.cx_how_to_check.strip()


@settings(max_examples=100, deadline=None, derandomize=True)
@given(
    st.text(max_size=200),
    st.lists(st.text(max_size=60), max_size=4),
    st.sets(st.text(max_size=40), max_size=3),
)
def test_rule_label_never_raises_for_arbitrary_text(name, lay, anc):
    label = rule_label(name, lay, anc)
    assert label.cx_obs in {"home", "exam", "test"}
    assert label.cx_min_age_months in {0, 12, 60, 108}
