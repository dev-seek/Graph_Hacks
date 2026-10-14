"""Integration: FalkorDB pinned image answers and enforces query timeouts (docs/VERIFIED.md)."""

import os

import pytest
from falkordb import FalkorDB

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db() -> FalkorDB:
    return FalkorDB(
        host=os.environ.get("FALKORDB_HOST", "localhost"),
        port=int(os.environ.get("FALKORDB_PORT", "6379")),
    )


def test_list_graphs_responds(db: FalkorDB) -> None:
    assert isinstance(db.list_graphs(), list)


def test_ro_query_with_timeout_is_enforced(db: FalkorDB) -> None:
    g = db.select_graph("p0_timeout_probe")
    g.query("CREATE (:Probe)", timeout=2000)
    try:
        with pytest.raises(Exception, match="(?i)time"):
            g.ro_query("UNWIND range(1, 1000000000) AS x RETURN count(x)", timeout=200)
    finally:
        g.delete()
