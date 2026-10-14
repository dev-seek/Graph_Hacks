from __future__ import annotations

from pathlib import Path

import pytest

from app.kb.parsers.phenopackets import EvalCase
from app.kb.split import assign, is_dev, write_split


def case(i: int, pmid: str) -> EvalCase:
    return EvalCase(case_id=f"c{i}", pmid=pmid, disease_id="OMIM:1")


CASES = [case(i, f"PMID:{i // 4}") for i in range(2000)]  # 4 cases per publication


def test_deterministic_and_order_independent() -> None:
    a = assign(CASES)
    b = assign(list(reversed(CASES)))
    assert a == b


def test_same_publication_same_side_and_no_overlap() -> None:
    dev, test, test_pmids = assign(CASES)
    assert not set(dev) & set(test) and len(dev) + len(test) == len(CASES)
    dev_pmids = {CASES[int(d[1:])].pmid for d in dev}
    assert not dev_pmids & set(test_pmids)


def test_dev_share_is_about_thirty_percent() -> None:
    dev, _, _ = assign(CASES)
    assert 0.24 < len(dev) / len(CASES) < 0.36


def test_seed_changes_assignment() -> None:
    assert assign(CASES, seed=1) != assign(CASES, seed=2)
    assert is_dev("PMID:1") == is_dev("PMID:1")


def test_case_without_pmid_is_its_own_unit() -> None:
    dev, test, test_pmids = assign([case(1, ""), case(2, "")])
    assert len(dev) + len(test) == 2 and test_pmids == []


def test_write_split_refuses_to_overwrite_frozen_test_list(tmp_path: Path) -> None:
    (tmp_path / "test_ids.txt").write_text("x\n")
    with pytest.raises(FileExistsError):
        write_split(tmp_path / "missing.zip", out_dir=tmp_path)
