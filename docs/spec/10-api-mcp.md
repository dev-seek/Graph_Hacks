<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 12. API and MCP tools

FastAPI, `/api` prefix, all bodies Pydantic. Contract file: `backend/app/api/schemas.py` (frozen after Phase 2; changes need an ADR). OpenAPI exported to `web/src/api/openapi.json`; TypeScript types generated from it.

| Method | Path | Notes |
|---|---|---|
| POST | `/families` | → `{family_id, family_token}` |
| POST | `/families/{id}/story` | `{text ≤ 4000 chars, child_age_months, sex?}` → `{safety, extraction_to_confirm}` |
| POST | `/families/{id}/confirm` | `{accept[], reject[], edits[]}` |
| GET | `/families/{id}/state` | phase, round, banner, next step (parent-safe) |
| GET | `/families/{id}/round` | current questions |
| POST | `/families/{id}/round/{n}/answers` | `{answers:[{qid, value}]}` → `{safety, next}` |
| GET | `/families/{id}/pack` | doctor pack data (+ clinician code) |
| POST | `/families/{id}/documents` | text or PDF ≤ 5 MB → extraction to confirm |
| GET | `/families/{id}/timeline` | findings + events |
| GET | `/families/{id}/constellation` | nodes/edges for the star visual (findings only) |
| DELETE | `/families/{id}` | deletes family graph and checkpoints |
| GET | `/clinician/{id}` | header `X-Clinician-Code`; candidates, explanations, suggested checks, referral draft |
| GET | `/clinician/{id}/phenopacket` | header `X-Clinician-Code`; GA4GH Phenopacket v2 JSON |
| GET | `/centre/overview`, `/centre/lookalikes`, `/centre/routing/{case_id}`, `/centre/bridges`, `/centre/clusters`, `/centre/cases/{case_id}` | |
| POST | `/centre/ask`, `/centre/whatif` | |
| GET | `/demo/journeys`, `/demo/{journey}/steps` | replay data |
| GET | `/health`, `/version` | versions of kb, HPO, Orphanet, Phenopacket Store, app |
| GET | `/debug/queries?family_id=` | live inspector query log: query name, Cypher text, params (no free text), rows, ms (demo families only) |

Auth: `Authorization: Bearer <family_token>` on family routes (token = 32 random bytes, stored hashed). Parent responses are validated by a test that recursively rejects keys like `disease`, `candidate`, `probability`, `rank`, `posterior`.

**MCP server** (`backend/app/mcp/`, Python MCP SDK, stdio + streamable HTTP): four read-only tools — `resolve_phenotype(text)`, `rank_candidates(findings[])` (clinician-style output, disclaimer included), `explain_candidate(findings[], disease_id)`, `centre_route_case(hpo_ids[])` (look-alikes + clinician + protocol). Cut order keeps the first two. Document how to connect it from Claude Desktop / Claude Code in the README. This lets other agents act on the connected graph (Track 1).
