from __future__ import annotations

import math

from app.eval.metrics import bootstrap_ci, median_rank, mrr, paired_diff_ci, summarise, top_k
from app.eval.simulator import SimFeature, SimParent

ANC = {
    "seizure": {"seizure", "neuro"},
    "focal": {"focal", "seizure", "neuro"},
    "ataxia": {"ataxia", "neuro"},
    "anemia": {"anemia", "blood"},
}


def test_yes_for_present_descendant_and_no_for_excluded_ancestor() -> None:
    sim = SimParent([SimFeature("focal")], {"blood"}, ANC, no_rate=0.0)
    answers = [sim.answer("seizure") for _ in range(200)]
    assert {"yes", "unsure"} == set(answers) and answers.count("unsure") < 40
    assert sim.answer("anemia") == "no"
    assert sim.answer("ataxia") == "unsure"


def test_unmentioned_no_rate_is_respected_and_deterministic() -> None:
    mk = lambda: SimParent([], set(), ANC, no_rate=0.3, seed=7)  # noqa: E731
    a = [mk().answer("ataxia") for _ in range(1)]
    s1, s2 = mk(), mk()
    xs = [s1.answer("ataxia") for _ in range(2000)]
    assert xs == [s2.answer("ataxia") for _ in range(2000)]
    assert 0.25 < xs.count("no") / 2000 < 0.35 and a


def test_story_takes_earliest_two_or_three_home_features() -> None:
    feats = [
        SimFeature("a", 30),
        SimFeature("b", 6),
        SimFeature("c", None),
        SimFeature("d", 12),
        SimFeature("e", 2),
    ]
    sim = SimParent(feats, set(), ANC)
    assert sim.story({"a", "b", "c", "d"}) == ["b", "d", "a"]
    assert sim.story({"a"}) == ["e", "b", "d"]  # fewer than 2 home features: fall back to all


def test_rank_metrics() -> None:
    ranks = [1, 2, 11, None]
    assert top_k(ranks, 1) == 0.25 and top_k(ranks, 10) == 0.5
    assert math.isclose(mrr(ranks), (1 + 0.5 + 1 / 11) / 4)
    assert median_rank(ranks) == 6.5 and median_rank([1, None, None]) == math.inf


def test_bootstrap_ci_brackets_the_estimate_and_is_seeded() -> None:
    ranks = [1] * 30 + [None] * 70
    lo, hi = bootstrap_ci(ranks, lambda r: top_k(r, 1))
    assert lo < 0.3 < hi and (lo, hi) == bootstrap_ci(ranks, lambda r: top_k(r, 1))
    assert summarise(ranks)["top1"] == 0.3


def test_paired_diff_ci_positive_when_a_better() -> None:
    a = [1] * 60 + [None] * 40
    b = [None] * 60 + [1] * 40
    lo, hi = paired_diff_ci(a, b, lambda r: top_k(r, 1))
    assert lo < 0.2 < hi
    a2 = [1] * 90 + [None] * 10
    b2 = [None] * 100
    assert paired_diff_ci(a2, b2, lambda r: top_k(r, 1))[0] > 0.7
