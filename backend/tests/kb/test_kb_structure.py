"""Tests for app.kb.structure (ancestor closure, depth, system, annotation stats)."""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.kb.structure import annotation_stats, build_structure

ALL = "HP:0000001"
ROOT = "HP:0000118"  # phenotypic abnormality
A = "HP:0000010"
B = "HP:0000005"
C = "HP:0000020"  # child of A and B (diamond)
D = "HP:0000030"  # child of C
E = "HP:0000040"  # child of D and directly of ROOT
OUT = "HP:0000999"  # outside the phenotype subtree

DIAMOND = {
    ALL: [],
    ROOT: [ALL],
    A: [ROOT],
    B: [ROOT],
    C: [A, B],
    D: [C],
    E: [D, ROOT],
    OUT: [ALL],
}


def test_ancestors_exclude_the_term_itself():
    s = build_structure(DIAMOND, ROOT)
    for t, anc in s.ancestors.items():
        assert t not in anc


def test_ancestors_cover_every_term_in_parents():
    s = build_structure(DIAMOND, ROOT)
    assert set(s.ancestors) == set(DIAMOND)


def test_diamond_term_has_both_parents_and_all_higher_ancestors():
    s = build_structure(DIAMOND, ROOT)
    assert s.ancestors[C] == frozenset({A, B, ROOT, ALL})
    assert s.ancestors[D] == frozenset({C, A, B, ROOT, ALL})


def test_root_term_has_no_ancestors():
    s = build_structure(DIAMOND, ROOT)
    assert s.ancestors[ALL] == frozenset()


def test_depth_of_pheno_root_is_zero():
    assert build_structure(DIAMOND, ROOT).depth[ROOT] == 0


def test_depth_is_shortest_path_through_diamond():
    s = build_structure(DIAMOND, ROOT)
    assert s.depth[A] == 1
    assert s.depth[C] == 2
    assert s.depth[D] == 3


def test_depth_uses_shortest_of_two_paths():
    # E is 4 hops via D but 1 hop directly under the root.
    assert build_structure(DIAMOND, ROOT).depth[E] == 1


def test_terms_outside_pheno_root_are_absent_from_depth_and_system():
    s = build_structure(DIAMOND, ROOT)
    for t in (OUT, ALL):
        assert t not in s.depth
        assert t not in s.system


def test_pheno_root_is_absent_from_system():
    assert ROOT not in build_structure(DIAMOND, ROOT).system


def test_top_level_term_maps_to_itself_in_system():
    s = build_structure(DIAMOND, ROOT)
    assert s.system[A] == A
    assert s.system[B] == B


def test_descendant_maps_to_its_top_level_branch():
    s = build_structure(DIAMOND, ROOT)
    assert s.system[D] == s.system[C]


def test_system_tie_break_takes_smallest_branch_id():
    # C descends from both A (HP:0000010) and B (HP:0000005): smallest id is B.
    s = build_structure(DIAMOND, ROOT)
    assert s.system[C] == B
    assert s.system[D] == B


def test_term_directly_under_root_and_under_other_branch_maps_to_itself():
    s = build_structure(DIAMOND, ROOT)
    assert s.system[E] == E


def test_system_branch_is_a_child_of_pheno_root():
    s = build_structure(DIAMOND, ROOT)
    for t, branch in s.system.items():
        assert ROOT in DIAMOND[branch]
        assert branch in s.ancestors[t] or branch == t


# ---------------------------------------------------------------- annotation_stats

T_R, T_A, T_A1, T_A2, T_B = "HP:1", "HP:2", "HP:3", "HP:4", "HP:5"
TINY = {T_R: [], T_A: [T_R], T_A1: [T_A], T_A2: [T_A], T_B: [T_R]}
ROWS = [
    ("D1", T_A1, 0.5),
    ("D1", T_B, 1.0),
    ("D2", T_A2, 0.25),
    ("D3", T_A1, 1.0),
    ("D3", T_A1, 0.5),
]


@pytest.fixture
def stats():
    return annotation_stats(build_structure(TINY, T_R), ROWS)


def test_stats_have_entry_for_every_term_in_structure(stats):
    assert set(stats) == set(TINY)


def test_leaf_bg_uses_max_frequency_per_disease(stats):
    # A1: D1 0.5, D3 max(1.0, 0.5)=1.0, N=3
    assert stats[T_A1].bg == pytest.approx(1.5 / 3)
    assert stats[T_A1].n_diseases == 2
    assert stats[T_A1].ic == pytest.approx(-math.log(2 / 3))


def test_single_disease_leaf_hand_computed(stats):
    assert stats[T_A2].bg == pytest.approx(0.25 / 3)
    assert stats[T_A2].n_diseases == 1
    assert stats[T_A2].ic == pytest.approx(math.log(3))


def test_parent_takes_max_of_descendant_frequencies_per_disease(stats):
    # A: D1 0.5 (via A1), D2 0.25 (via A2), D3 1.0 (via A1)
    assert stats[T_A].bg == pytest.approx(1.75 / 3)
    assert stats[T_A].n_diseases == 3
    assert stats[T_A].ic == pytest.approx(0.0)


def test_root_propagation_takes_max_across_branches(stats):
    # R: D1 max(0.5, 1.0)=1.0, D2 0.25, D3 1.0
    assert stats[T_R].bg == pytest.approx(2.25 / 3)
    assert stats[T_R].n_diseases == 3


def test_unannotated_term_gets_floor_zero_diseases_and_log_n():
    s = build_structure({**TINY, "HP:6": [T_B]}, T_R)
    st_ = annotation_stats(s, ROWS)
    assert st_["HP:6"].bg == pytest.approx(1e-4)
    assert st_["HP:6"].n_diseases == 0
    assert st_["HP:6"].ic == pytest.approx(math.log(3))


def test_custom_floor_is_applied():
    s = build_structure({**TINY, "HP:6": [T_B]}, T_R)
    assert annotation_stats(s, ROWS, floor=0.01)["HP:6"].bg == pytest.approx(0.01)


def test_tiny_frequency_sum_is_floored():
    s = build_structure(TINY, T_R)
    out = annotation_stats(s, [("D1", T_A1, 1e-9), ("D2", T_B, 1.0)], floor=1e-3)
    assert out[T_A1].bg == pytest.approx(1e-3)
    assert out[T_A1].n_diseases == 1


def test_annotations_with_unknown_terms_are_ignored():
    s = build_structure(TINY, T_R)
    out = annotation_stats(s, [*ROWS, ("D9", "HP:unknown", 1.0)])
    assert "HP:unknown" not in out
    # D9 still counts toward N only if its rows are used; unknown rows must not change stats
    base = annotation_stats(s, ROWS)
    assert out[T_A1].bg == pytest.approx(base[T_A1].bg)
    assert out[T_A1].n_diseases == base[T_A1].n_diseases


@st.composite
def dag_and_rows(draw):
    n = draw(st.integers(min_value=2, max_value=12))
    ids = [f"HP:{i:07d}" for i in range(n)]
    parents: dict[str, list[str]] = {ids[0]: []}
    for i in range(1, n):
        k = draw(st.integers(min_value=1, max_value=min(2, i)))
        ps = draw(st.lists(st.integers(0, i - 1), min_size=k, max_size=k, unique=True))
        parents[ids[i]] = [ids[p] for p in ps]
    rows = draw(
        st.lists(
            st.tuples(
                st.sampled_from([f"D{i}" for i in range(5)]),
                st.sampled_from(ids),
                st.floats(min_value=0.01, max_value=1.0),
            ),
            min_size=1,
            max_size=25,
        )
    )
    return parents, ids[0], rows


@settings(max_examples=60, deadline=None, derandomize=True)
@given(dag_and_rows())
def test_stats_invariants_hold_on_random_dags(data):
    parents, root, rows = data
    s = build_structure(parents, root)
    out = annotation_stats(s, rows, floor=1e-4)
    for ts in out.values():
        assert 1e-4 - 1e-12 <= ts.bg <= 1.0 + 1e-9
        assert ts.ic >= -1e-12
    for child, ps in parents.items():
        for p in ps:
            assert out[p].n_diseases >= out[child].n_diseases
            assert out[p].bg >= out[child].bg - 1e-9
