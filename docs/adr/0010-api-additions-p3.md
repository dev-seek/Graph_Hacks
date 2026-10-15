# ADR-0010: API additions in P3

Status: accepted (2026-10-15)

The §12 contract (`schemas.py`) is unchanged: no model was added, removed or edited. Two additions to the route set:
- `POST /api/families/{id}/advance` (parent token): the "6 months later" demo button the watcher needs (P3 task 6 and spec §9 `watcher`). Returns `ParentState`.
- `GET /api/debug/queries` now requires the family bearer token and answers 403 for non-demo families (spec §12 says "demo families only").
Parent-route auth failures (unknown family or wrong token) both answer 401, so ids cannot be enumerated. `OPTIONS`/health stay open. Rate limits (in memory): 120 requests/min per token, 10 new families/hour per client address, 60 clinician requests/min per family.
