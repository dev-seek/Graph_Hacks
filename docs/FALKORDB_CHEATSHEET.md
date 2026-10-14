# FALKORDB_CHEATSHEET.md — syntax from the docs, to be confirmed by tests

Status: gathered from FalkorDB docs and the pre-kickoff research. **Each item becomes "verified" only after an integration test against the pinned FalkorDB image passes**; then copy the line into `docs/VERIFIED.md` with the date and test name. Core queries for this project live in spec §13 (`docs/spec/11-cypher.md`).

## 1. LangGraph checkpointer (langchain-falkordb 0.2.0; tested with langgraph 1.2.15 + langgraph-checkpoint 4.3.0)
```python
from langchain_falkordb.checkpoint import FalkorDBSaver
saver = FalkorDBSaver(host=settings.falkordb_host, port=settings.falkordb_port)
app = workflow.compile(checkpointer=saver)
config = {"configurable": {"thread_id": f"family_{family_id}"}}
```
Use only put / `get_state` / `list(limit=...)`. Do not use `copy_thread`, `delete_for_runs`, `prune`. The async API is not truly async. Pin versions in `pyproject.toml`; don't rely on extras names. Source: https://docs.falkordb.com/genai-tools/langgraph

## 2. Vector index
```cypher
CREATE VECTOR INDEX FOR (t:Term) ON (t.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine', M: 16, efConstruction: 200}
MATCH (t:Term {id: $id}) SET t.embedding = vecf32($embedding)
CALL db.idx.vector.queryNodes('Term', 'embedding', 10, vecf32($query_vec)) YIELD node, score
RETURN node.id AS id, node.name AS name, score
```
VERIFIED (6.0.2): `score` is a cosine distance (lower = closer); `M`/`efConstruction` accepted. Vector search cannot be combined with property filters in the same call. Source: https://docs.falkordb.com/cypher/indexing/vector-index

## 3. Full-text index
```cypher
CREATE FULLTEXT INDEX FOR (t:Term) ON (t.name, t.synonyms_text, t.cx_lay_text)   // VERIFIED 6.0.2; the 4-argument createNodeIndex procedure is rejected
CALL db.idx.fulltext.queryNodes('Term', $q) YIELD node, score
RETURN node.id AS id, node.name AS name, score ORDER BY score DESC LIMIT 10
```
Query syntax supports prefix (`seiz*`), fuzzy (`%seizur%1`) and `|` OR (RediSearch syntax). Escape user text before building queries (strip RediSearch operators). Source: https://docs.falkordb.com/cypher/indexing/fulltext-index

## 4. Range indexes
```cypher
CREATE INDEX FOR (t:Term) ON (t.id)
CREATE INDEX FOR (d:Disease) ON (d.id)
CREATE INDEX FOR (c:Case) ON (c.case_id)
```

## 5. Algorithms
```cypher
CALL algo.betweenness({nodeLabels: ['Case', 'Term'], relationshipTypes: ['PRESENTED_WITH'], samplingSize: 64, samplingSeed: 42})
YIELD node, score

CALL algo.WCC({nodeLabels: ['Case'], relationshipTypes: ['SIMILAR_TO']}) YIELD node, componentId

CALL algo.labelPropagation({nodeLabels: ['Case'], relationshipTypes: ['SIMILAR_TO'], maxIterations: 10}) YIELD node, communityId
```
Always set `samplingSeed` for deterministic tests. To test: exact procedure name for label propagation (CDLP page) and its yield column name. Sources: https://docs.falkordb.com/algorithms/

## 6. Graph commands
- `GRAPH.COPY centre centre_whatif` (what-if snapshot). Source: https://docs.falkordb.com/commands/graph.copy
- `GRAPH.DELETE family_<id>` (erasure).
- `GRAPH.RO_QUERY` for every read (Python client `graph.ro_query(...)`), with a timeout argument.
- Config: `TIMEOUT_MAX`, `TIMEOUT_DEFAULT`, `QUERY_MEM_CAPACITY` — to test how to pass them in the pinned Docker image. Source: https://docs.falkordb.com/getting-started/configuration

## 7. Guardrails from "known limitations" (https://docs.falkordb.com/cypher/known-limitations)
- **A. Unreferenced relationship variables:** if `r` in `(a)-[r]->(b)` is not referenced, FalkorDB may only check that at least one edge exists. When counting or aggregating over edges, reference it: `WHERE ID(r) >= 0`.
- **B. No aggregates inside pattern comprehensions:** use `size([(n)-[]->(m) | m])` or aggregate in a preceding `WITH`.
- **C. `LIMIT` doesn't limit eager writes:** put `LIMIT` in a `WITH` before `CREATE/SET/MERGE/DELETE`.
- **D. `<>` filters don't use indexes.**
- Prefer `round(x * 100) / 100.0` over two-argument `round` unless tested.

## 8. Query hygiene for this repo
- Anchor every variable-length pattern on an indexed node (`{id: $param}`); never scan all paths of the HPO tree.
- Upward IS_A walks are cheap (few ancestors); downward walks from general terms can be large — cap depth.
- Parenthesise mixed `AND`/`OR` conditions explicitly.
- A `WHERE` after `OPTIONAL MATCH` filters only that optional pattern — put guards on the right clause.
