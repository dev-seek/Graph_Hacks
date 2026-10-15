"""Integration: family graph repository against FalkorDB (every `f_*` registry query)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest

from app.graph.client import QueryLog, set_query_log
from app.graph.family import CHECKPOINT_GRAPH, FamilyRepo
from app.graph.queries import _DIR

pytestmark = pytest.mark.integration


@pytest.fixture
def repo() -> Iterator[FamilyRepo]:
    r = FamilyRepo(uuid.uuid4().hex[:12])
    r.create("kb_test", 30, "male")
    yield r
    r.delete()


def test_create_and_info(repo: FamilyRepo) -> None:
    info = repo.info()
    assert info is not None and info.age_months == 30 and info.sex == "male"
    assert info.kb_version == "kb_test" and info.consent is False
    repo.set_age(36)
    repo.set_kb_version("kb_newer")
    info2 = repo.info()
    assert info2 is not None and info2.age_months == 36 and info2.kb_version == "kb_newer"


def test_findings_are_idempotent_and_corrections_keep_history(repo: FamilyRepo) -> None:
    h = repo.add_story("he is floppy")
    f1 = repo.add_finding(
        term_id="HP:1",
        label="floppy",
        status="present",
        source="parent_story",
        quote="floppy",
        start=6,
        end=12,
        story_hash=h,
        finding_id="f1",
    )
    repo.add_finding(
        term_id="HP:1",
        label="floppy",
        status="present",
        source="parent_story",
        quote="floppy",
        start=6,
        end=12,
        story_hash=h,
        finding_id="f1",
    )
    assert [f.id for f in repo.findings()] == ["f1"]
    f2 = repo.correct_finding(
        f1,
        term_id="HP:2",
        label="very floppy",
        status="present",
        source="parent_story",
        finding_id="f2",
    )
    assert [f.id for f in repo.findings()] == [f2]
    assert {f.id for f in repo.findings(include_inactive=True)} == {"f1", "f2"}
    repo.deactivate_finding("f2")
    assert repo.findings() == []


def test_termrefs_documents_and_evidence_links(repo: FamilyRepo) -> None:
    repo.copy_termrefs({"HP:1": "A", "HP:0": "Root"}, [("HP:1", "HP:0")])
    repo.copy_termrefs({"HP:1": "A", "HP:0": "Root"}, [("HP:1", "HP:0")])  # idempotent
    doc = repo.add_document("text", "letter text")
    repo.add_finding(
        term_id="HP:1",
        label="a",
        status="absent",
        source="doctor_exam",
        ev_kind="document",
        doc_id=doc,
        finding_id="fd",
    )
    n = repo.graph.ro_query("MATCH (:Evidence)-[:IN_DOCUMENT]->(:Document) RETURN count(*)")
    assert n.result_set[0][0] == 1
    e = repo.graph.ro_query("MATCH (:TermRef)-[r:IS_A]->(:TermRef) RETURN count(r)")
    assert e.result_set[0][0] == 1


def test_rounds_answers_and_asked_terms(repo: FamilyRepo) -> None:
    qs = [
        {"qid": "q1", "term_id": "HP:9", "text": "Does he tire?", "why": "w", "how": "h"},
        {"qid": "q2", "term_id": "HP:8", "text": "Any rash?", "ask_doctor": True},
    ]
    repo.add_round(1, "home", qs)
    repo.add_round(1, "home", qs)  # idempotent
    got = repo.round(1)
    assert [r["qid"] for r in got] == ["q1", "q2"] and got[1]["ask_doctor"] is True
    assert repo.latest_round() == (1, "home") and repo.asked_terms() == {"HP:9", "HP:8"}
    fid = repo.add_finding(
        term_id="HP:9",
        label="tires",
        status="present",
        source="parent_answer",
        ev_kind="answer",
        finding_id="fa",
    )
    repo.record_answer("q1", "yes", fid)
    repo.record_answer("q2", "no", None)
    assert {r["qid"]: r["answer"] for r in repo.round(1)} == {"q1": "yes", "q2": "no"}


def test_snapshot_gate_flag_artifact_state_events(repo: FamilyRepo) -> None:
    at = repo.add_snapshot(
        1,
        "kb_test",
        0.4,
        3,
        [
            {"id": "ORPHA:1", "name": "X", "rank": 1, "post": 0.2},
            {"id": "ORPHA:2", "name": "Y", "rank": 2, "post": 0.1},
        ],
    )
    snap = repo.latest_snapshot()
    assert snap is not None and [c["id"] for c in snap["candidates"]] == ["ORPHA:1", "ORPHA:2"]
    repo.add_gate(1, at, "SEE_DOCTOR", {"rare_mass": 0.4}, "G1")
    gate = repo.latest_gate()
    assert gate is not None and gate["kind"] == "SEE_DOCTOR" and gate["inputs"]["rare_mass"] == 0.4
    repo.add_flag("seizure_long_or_repeated", "EMERGENCY", "it lasted ten minutes")
    repo.add_flag("seizure_long_or_repeated", "EMERGENCY", "it lasted ten minutes")
    assert len(repo.flags()) == 1
    repo.add_finding(
        term_id="HP:1", label="a", status="present", source="parent_story", finding_id="fz"
    )
    a1 = repo.add_artifact("doctor_pack", {"n": 1}, ["fz"])
    repo.add_artifact("doctor_pack", {"n": 2}, ["fz"])
    latest = repo.latest_artifact("doctor_pack")
    assert latest is not None and latest["version"] == 2 and latest["payload"] == {"n": 2} and a1
    assert repo.get_state() == ("story", 0)
    repo.set_state("questions", 2)
    assert repo.get_state() == ("questions", 2)
    repo.add_event("story", "Story shared", "e1")
    repo.add_event("story", "Story shared", "e1")
    assert len(repo.events()) == 1


def test_delete_removes_graph_and_checkpoints() -> None:
    from langchain_falkordb.checkpoint import FalkorDBSaver

    fid = uuid.uuid4().hex[:12]
    r = FamilyRepo(fid)
    r.create("kb_test", 12, None)
    saver = FalkorDBSaver(database=CHECKPOINT_GRAPH)
    saver._query(  # noqa: SLF001
        "CREATE (:Checkpoint {thread_id: $t, checkpoint_id: 'c1'})", {"t": f"family_{fid}"}
    )
    r.delete()
    assert f"family_{fid}" not in r.db.list_graphs()
    left = saver._query(
        "MATCH (c:Checkpoint {thread_id: $t}) RETURN count(c)", {"t": f"family_{fid}"}
    )  # noqa: SLF001
    assert left[0][0] == 0


def test_query_log_records_params_without_free_text(repo: FamilyRepo) -> None:
    log = QueryLog()
    set_query_log(log)
    try:
        repo.add_finding(
            term_id="HP:1",
            label="private words",
            status="present",
            source="parent_story",
            quote="secret quote",
            finding_id="fq",
        )
    finally:
        set_query_log(None)
    e = next(x for x in log.entries if x.name == "f_add_finding")
    assert e.params["quote"] == "<redacted>" and e.params["label"] == "<redacted>"
    assert "MERGE" in e.cypher and e.ms >= 0


def test_every_family_query_file_is_exercised() -> None:
    import inspect
    import sys

    src = inspect.getsource(sys.modules["app.graph.family"])
    for p in _DIR.glob("f_*.cypher"):
        assert p.stem in src, f"{p.stem} is not used by the repository"
