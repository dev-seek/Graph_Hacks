"""Frozen-split runner: trace serialisation round trip and the split-hash guard."""

from __future__ import annotations

import pytest

from app.eval import frozen
from app.eval.runner import CaseTrace, RoundRecord, Snapshot


def _trace() -> CaseTrace:
    snap = Snapshot(rank=3, rare_mass=0.4, top10_share=0.7, n_doctor_test_findings=0)
    doc = Snapshot(rank=1, rare_mass=0.9, top10_share=0.9, n_doctor_test_findings=2)
    return CaseTrace(
        "c1",
        "ours",
        [
            RoundRecord(0, snap, 0.2, 0.1, 0, 12.0, 30.0, doc),
            RoundRecord(1, snap, 0.1, 0.1, 4, 1, 2),
        ],
    )


def test_trace_round_trip() -> None:
    t = _trace()
    back = frozen.trace_from_dict(frozen.trace_to_dict(t))
    assert back == t


def test_plan_is_preregistered_scope() -> None:
    tags = [j.tag for j in frozen.plan()]
    kinds = [(j.kb, j.strategy) for j in frozen.plan()[:6]]
    assert kinds == [(k, s) for k in ("lpo", "std") for s in ("ours", "b1", "b2")]
    assert set(tags[6:]) == {"lpo:ours:0.00", "lpo:ours:0.30"}


def test_test_split_hash_is_checked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(frozen, "TEST_IDS_SHA256", "0" * 64)
    with pytest.raises(SystemExit):
        frozen.split_ids("test")
