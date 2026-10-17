# Verified facts

Each entry: what was checked, how, when. Nothing is used before it is listed here.

## FalkorDB Docker image tag (P0, 2026-10-15)
- Pinned tag: `falkordb/falkordb:6.0.2` (Docker Hub; same digest as `latest` at the time: `sha256:107455e8…59ba6`; amd64 + arm64). Server reports module `graph` ver `60002`, Redis 8.10.2.
- Never use `latest`. Compose and CI use this exact tag.

## FalkorDB query timeouts (P0, 2026-10-15)
- Mechanism: env var `FALKORDB_ARGS="TIMEOUT_MAX 10000 TIMEOUT_DEFAULT 3000"` on the image; confirmed with `GRAPH.CONFIG GET TIMEOUT_MAX` → 10000 and `TIMEOUT_DEFAULT` → 3000.
- Behaviour: a runaway `GRAPH.RO_QUERY` returned "Query timed out" after 3.0 s (default); with `TIMEOUT 200` appended it timed out after 0.23 s. Per-query timeouts therefore work and are capped by TIMEOUT_MAX.

## Local container runtime (P0)
- macOS dev machine uses colima (`colima start --cpu 2 --memory 4`) with docker-compose plugin 5.x.

## Source file structures (P1, 2026-10-15; derived from the pinned files by script, not memory)
- **hp.json** (v2026-09-01, obographs): `graphs[0].nodes[]` {id: URI `.../obo/HP_0001250`, lbl, type CLASS, meta{definition.val, synonyms[{pred, val, synonymType?}], basicPropertyValues[...], deprecated}}. 20,532 nodes, 24,436 edges, all `pred == "is_a"` (`sub`/`obj` URIs). Layperson synonyms: `synonymType == http://purl.obolibrary.org/obo/hp#layperson` (≈8,000 of them, any pred). Alt IDs: basicPropertyValues pred `...oboInOwl#hasAlternativeId` (val CURIE). Obsolete: `meta.deprecated == true`; replacement: pred `http://purl.obolibrary.org/obo/IAO_0100001` (val CURIE). Version: `meta.version` URL / owl#versionInfo = `2026-09-01`.
- **phenotype.hpoa** (`#version: 2026-09-02`, `#hpo-version` → hp release 2026-09-01): comment lines start `#`; header row is the first non-comment line with the 12 expected columns. 286,651 rows: OMIM 169,694 / ORPHA 116,661 / DECIPHER 296. OMIM evidence: PCS 119,283, IEA 30,061, TAS 20,350 (so the OMIM+IEA filter drops 30,061 rows). Aspects P 268,906 / I 8,978 / C 8,559 / H 131 / M 77. Qualifier `NOT`: 733. Frequency: HP term 119,446; `n/m` 103,704; `x%` 105; empty 63,396; `0/n` occurs (e.g. `0/2`). `reference` may hold several `;`-separated entries (PMID:, ORPHA:, OMIM:, ISBN-13:, DECIPHER:, http). ORPHA rows cite `ORPHA:<id>` itself, so PMID-based leave-publication-out only affects OMIM rows.
- **en_product1.json.tar.gz** (Orphanet 2026-06-23): single member `en_product1.json`; `JDBOR[0].DisorderList[0].Disorder[]` (11,645) with every field wrapped in lists: `OrphaCode`, `Name[0].label`, `ExternalReferenceList[0].ExternalReference[]` {Source, Reference, `DisorderMappingRelation[0].Name[0].label`}. Sources: MONDO 9,979 · UMLS · OMIM 8,745 · ICD-10 · ICD-11 · GARD · MeSH · MedDRA. Relation label starts with the code: `E (Exact mapping…)`, `BTNT (ORPHAcode is broader than the targeted code…)`, `NTBT (… narrower …)`, `ND`. OMIM: E 3,781 · BTNT 4,138 · NTBT 797 · ND 29. We store the bare code (`E`, `BTNT`, `NTBT`, `ND`) so Q5's `relation = 'E'` matches. Bare numeric codes are normalised to `ORPHA:<n>` / `OMIM:<n>`.
- **en_product9_prev.xml**: `Disorder/OrphaCode`, `PrevalenceList/Prevalence` {PrevalenceType/Name, PrevalenceClass/Name (may be empty), PrevalenceGeographic/Name, PrevalenceValidationStatus/Name (may be absent)}. Classes seen: `<1 / 1 000 000`, `1-9 / 1 000 000`, `1-9 / 100 000`, `1-5 / 10 000`, `6-9 / 10 000`, `>1 / 1000`, `Unknown`, `Not yet documented`. Types: Point prevalence 8,304 · Cases/families · Annual incidence · Prevalence at birth · Lifetime Prevalence.
- **Phenopacket Store 0.1.27** `all_phenopackets.zip`: 10,377 `*.json` (`0.1.27/<gene or group>/<id>.json`); every case has exactly 1 `interpretations[0].diagnosis.disease.id`, **always `OMIM:`** (no ORPHA), exactly 1 `metaData.externalReferences[].id` = `PMID:n` (also in `id` `PMID_n_…`). `phenotypicFeatures[]` {type.id, type.label, `excluded: true`?, `onset`: `{age:{iso8601duration}}` or `{ontologyClass}`}; `subject.timeAtLastEncounter.age.iso8601duration` for 7,873 cases; `subject.sex`. 132,795 excluded features; 9,652 cases have ≥ 5 features. Coverage therefore depends entirely on OMIM nodes having annotations or exact ORPHA bridges.

## FalkorDB 6.0.2 behaviours used by the kb build (P1, 2026-10-15; tests: backend/tests/kb/test_kb_graph_integration.py)
- Range indexes: `CREATE INDEX FOR (t:Term) ON (t.id)` and `(d:Disease)` — verified (`CALL db.indexes()` lists RANGE).
- Full-text: **`CALL db.idx.fulltext.createNodeIndex('Term','a','b','c')` is rejected** ("expected at most 1" argument). Working form: `CREATE FULLTEXT INDEX FOR (t:Term) ON (t.name, t.synonyms_text, t.cx_lay_text)`. `db.idx.fulltext.queryNodes('Term', $q)` works; words are AND-ed (`keeps falling fit` → no hit), `a | b` is OR, `"exact phrase"` works (phrase containing stop words like "in" matches), prefix `conv*` works; the `seizur~` fuzzy form I tried is a syntax error.
- Vector: `CREATE VECTOR INDEX FOR (t:Term) ON (t.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine', M: 16, efConstruction: 200}` accepted. **`score` from `db.idx.vector.queryNodes` is a cosine distance (lower = closer)**: "seizure" → Seizure 0.108, Tonic seizure 0.124. Vector property is written with `vecf32($list)`.
- `TIMEOUT_MAX` (10000 ms) also bounds write queries: a `timeout` argument above it is rejected ("cannot exceed the TIMEOUT_MAX"). The kb build therefore writes in batches (≤ 5000 rows) with `timeout=10000`; each batch finishes in < 3 s.
- Index listing columns: `[label, [fields], {field: [types]}, ...]`; indexes on one label are merged into one row.

## FalkorDB 6.0.2 query-planning quirks found in P2 (2026-10-15; tests: backend/tests/test_graph_queries_p2.py, benchmark in P2)
- **Spec §13 Q2a/Q2b/Q2d as written take 0.7–1.2 s regardless of the finding**: the planner starts from all `HAS_PHENOTYPE` relationships and filters afterwards (`GRAPH.EXPLAIN`: `Conditional Traverse (x)<-[r]-(d)` under `Unwind`). Fix: bind the term first and force the order with `WITH DISTINCT x` before the relationship match (14 ms for 2,690 rows).
- **`UNWIND … MATCH (f {id: fid})<-[:IS_A*0..10]-(x)` (downward var-length after UNWIND) returns zero rows** (silently). Upward var-length after UNWIND works (Q1, Q2b, Q2c, Q2e). Therefore Q2a and Q2d run once per finding with `$fid`. Results were compared against the spec form (same row counts, e.g. 2,690).
- `WITH a, min(length(p)) AS hops MATCH (a)<-[r]-(d)` (aggregate then match) loses rows; use `WITH DISTINCT fid, a, length(p) AS hops` (Python keeps the best LR across hop counts).
- Ancestor cache query (q3d, by depth band) loads 19,178 terms in 0.45 s.

## Minimal repro: UNWIND + downward variable-length match returns 0 rows (checked 2026-10-15)
```cypher
// setup
CREATE (r:T {id:'r'}), (c:T {id:'c'})-[:IS_A]->(r)
// expected 2 (r itself and c)            actual on 6.0.2: 2
MATCH (f:T {id:'r'})<-[:IS_A*0..10]-(x:T) RETURN count(*)
// expected 2                             actual on 6.0.2: 0
UNWIND ['r'] AS fid MATCH (f:T {id: fid})<-[:IS_A*0..10]-(x:T) RETURN count(*)
```
Same 0 with `*1..10` and with no labels. Upward (`-[:IS_A*0..]->`) after UNWIND works.
Throwaway containers (our pinned tag was not changed), run via `scratchpad/repro.py` against a 2-node graph:
| image | module ver | UNWIND form |
|---|---|---|
| `falkordb/falkordb:6.0.2` (our pin) | 999999 | **0 rows (bug)** |
| `falkordb/falkordb:edge-rs` (2026-10-15) | 999999 | **0 rows (bug)** |
| `falkordb/falkordb:v4.22.1` (Docker Hub `latest`) | 42201 | 2 rows (correct); `*1..10` form returns 1, which is also correct |
So the bug exists in the 6.x line through the newest edge build; the 4.22 line does not show it. Impact on us: none (Q2a/Q2d run once per finding, ADR-0008).

## LangGraph interrupt + FalkorDBSaver across a process restart (P3 task 1, 2026-10-15)
Versions: langgraph 1.2.15, langgraph-checkpoint 4.3.0, langchain-falkordb 0.2.0 (as locked in `uv.lock`).
- Import: `from langchain_falkordb.checkpoint import FalkorDBSaver`; ctor `FalkorDBSaver(host=, port=, database="langgraph_checkpoints")`.
- Storage: **one shared graph** (default `langgraph_checkpoints`) with node labels for checkpoints, blobs and writes, each carrying `thread_id` (range-indexed). It does NOT create `family_<id>` graphs, so there is no name clash with family graphs. Erasure therefore needs a delete keyed by `thread_id` in that graph (registry Cypher; we do not call `prune`/`delete_for_runs`/`copy_thread`).
- Process A (`invoke` until `interrupt()`, then exit) and process B (fresh saver + fresh compiled graph): `get_state` shows `next=('ask',)` with the pending interrupt value; `invoke(Command(resume="yes"))` completes; `saver.list(cfg, limit=5)` returns 4 checkpoints. Test: `backend/tests/agents/test_checkpoint_restart.py` (integration, two real subprocesses).
- A resumed node re-runs from its first line, so nodes keep LLM calls/writes out of the node that calls `interrupt()`.

## Anthropic adapter request shape (P3 task 2, 2026-10-15) — offline only, live NOT measured
SDK `anthropic==1.14.0` (httpx2-based). Verified against a stub transport (`backend/tests/llm/test_anthropic_adapter.py`):
`client.messages.parse(model, max_tokens, system=[{type:text, text, cache_control:{type:ephemeral}}], messages, output_format=<Pydantic>)` sends `output_config.format.type=json_schema` and returns `parsed_output`; advisor profiles use `client.beta.messages.parse(..., betas=["advisor-tool-2026-03-01"], tools=[{type:"advisor_20260301", name:"advisor", model, max_uses, max_tokens}])`. `stop_reason` `refusal`/`max_tokens` -> `LLMUnavailable` -> fallback. Model id `claude-haiku-5-5` (spec) replaced by `claude-haiku-4-5` (ADR-0009). Live behaviour (advisor + structured output together, real costs) is unmeasured: no key.

## MCP SDK 2.x, Phenopacket validation, pypdf (P3, 2026-10-16)
- `mcp==2.3.0`: `from mcp.server.fastmcp import FastMCP` no longer exists; use `from mcp.server.mcpserver import MCPServer` (`@server.tool(name=...)`, `.run("stdio" | "streamable-http")`) and `from mcp.client import Client` (`async with Client(server) as c: c.list_tools(); c.call_tool(name, args)`, in-process). Test: `backend/tests/test_mcp_server.py`.
- `phenopackets==2.0.2.post5` (official GA4GH protobuf classes): `google.protobuf.json_format.ParseDict(doc, Phenopacket(), ignore_unknown_fields=False)` rejects unknown or mistyped fields; used by `app.agents.packs.validate_phenopacket`.
- `pypdf==6.20.1`: `PdfReader(BytesIO(data)).pages[i].extract_text()` reads `data/fixtures/sample_letter.pdf`; garbage input raises and becomes HTTP 409.
- FastAPI in this lockfile wraps included routers (`app.routes` holds `_IncludedRouter`), so route enumeration for tests uses the OpenAPI document.

## Web toolchain (P4, 2026-10-16)
Pinned exactly in `web/package.json` (pnpm lockfile): `openapi-typescript 7.13.0` (`pnpm gen:types` writes `src/api/schema.d.ts` from the frozen `src/api/openapi.json`; `pnpm check:types-sync` fails on drift), `vitest 5.0.4` + `@testing-library/react 16.3.3` + jsdom 30 (`pnpm test`), `@playwright/test 1.64.1` + `@axe-core/playwright 4.13.0`, `cytoscape 3.34.3`, `lucide-react 1.57.0`, `qrcode 1.5.4`. Next rewrites `/api/*` to `API_ORIGIN` (default `http://127.0.0.1:8000`) so the browser is same-origin. Each library is exercised by a test or the build before it is relied on (see P4 tasks).

## Centre algorithms and GRAPH.COPY on falkordb/falkordb:6.0.2 (P5 task 1, 2026-10-16)
Probe on a 5-node toy graph (3 Case, 2 Term). `CALL dbms.procedures()` lists: `algo.BFS, HarmonicCentrality, MSF, SPpaths, SSpaths, WCC, betweenness, labelPropagation, maxFlow, pageRank`.
- `algo.betweenness({nodeLabels, relationshipTypes, samplingSize, samplingSeed})` YIELD `node, score` works with those keys; unknown keys fail with `Unknown parameter: <key>`. **Edges are followed in their stored direction only** (no orientation option): on `(:Case)-[:PRESENTED_WITH]->(:Term)` every score is 0.0. Adding the reverse edge type (`(:Term)-[:PRESENTED_IN]->(:Case)`) and listing both types in `relationshipTypes` gives non-zero scores (t1 = t2 = 6, case b = 8). Centre seed therefore writes the reverse edge (ADR-0014).
- `algo.WCC({nodeLabels, relationshipTypes})` YIELD `node, componentId` works (weak components).
- `algo.labelPropagation({nodeLabels, relationshipTypes, maxIterations})` YIELD `node, communityId` works.
- `Graph.copy(dest)` (GRAPH.COPY) works from the python client.
- Gotcha: a long-running first script here hung when output was piped (buffering); use `python -u` and a background run.

## FalkorDB 6.0.2 panic on an aggregate over a null column (P5, 2026-10-16)
`MATCH (c:Case {case_id:$id}) OPTIONAL MATCH (c)-[:PRESENTED_WITH]->(t:Term) RETURN c.case_id, c.status, c.age_band, c.diagnosis_name, c.kb_version, collect(t.name)` on a Case with **no** `diagnosis_name` property made the server panic (`src/reply.rs:655: called Option::unwrap() on a None value`) and restart; graphs created since the last RDB snapshot were lost. Not minimised further. Workaround in the registry: return the case row and the term names as two plain queries (`c_case`, `c_case_terms`). A regression test pins both an open and a resolved case.

## A FalkorDB crash/restart changes the kb's term search (P5, 2026-10-16)
After the 6.0.2 panic above, the server reloaded `kb_<release>` from its RDB snapshot. Row counts were identical to `kb_info.json`, the ancestor cache was identical, yet the Kabir journey picked different HPO terms for the same story (two integration tests and `make demo-replay` failed). `make kb` (22 s) restored the original behaviour. Most likely the rebuilt full-text/vector indexes rank differently after a reload; not proven. Rule: after any FalkorDB crash or restart run `make kb && make kb-prev && make centre` before trusting search-dependent tests. The frozen evaluation does not use term search (it feeds HPO ids directly), so its numbers are unaffected.

## Public deployment stack (P6, 2026-10-17)
- `caddy:2.10.2-alpine` exists (pulled, image 4c6e91c6ed0e). `docker-compose.prod.yml` is a standalone file (no dev ports); only caddy publishes 80/443. `docker compose -f docker-compose.prod.yml config` lists no other published port.
- Seed in a fresh FalkorDB volume (`--profile seed run --rm seed`: data check + `kb` + `kb-prev` + `centre`): 42 s with raw data already present.
- Through Caddy (`HTTP_PORT=8088`): CSP/HSTS/nosniff/frame headers present; `/api/*` goes straight to the api (no Next rewrite hop); a spoofed `X-Forwarded-For` is ignored (Caddy replaces it), uvicorn sees the real client address, so the per-client family limit (10/h) is per visitor, not global. The 11th create returned 429.
- Playwright against the Caddy stack (`E2E_BASE_URL=http://127.0.0.1:8088 pnpm e2e`, `CREATE_LIMIT_PER_HOUR=1000`): 29 passed, 1 skipped, with the strict CSP (`script-src 'self' 'unsafe-inline'`: Next.js inlines its hydration scripts). The api container needs `review/` mounted (safety rules are read at start-up), which the dev compose had missed.

## Restarting a seeded FalkorDB volume changes term search; a fresh volume does not (P6, 2026-10-17)
Reproduced twice: after `docker compose down` + `up` of an existing volume, followed by `make seed` (kb rebuilt in place), `make demo-replay` reported `kabir: DIFFERS` and two integration tests that follow Kabir's story to a referral failed (`watching` instead of `specialist_step`). After `docker compose down -v` + `make up seed` (fresh volume), `make demo-replay` reproduced all three journeys and `make test-int` passed. A clean `git clone` + fresh volume also passed (three runs). Cause still unproven (see the P5 note above). Practical rule: `make reset` after any FalkorDB restart before trusting search-dependent tests. The public demo pages replay static recordings and are not affected; only free-text term search on a reloaded volume is.
