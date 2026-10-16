# ADR 0015: Additive centre API fields and routes

Status: accepted (P5). `schemas.py` was frozen after P2; these are additive only (no field removed or retyped).
- `CentreRouting`: `suggested_clinician`, `suggested_specialty`, `suggested_protocol`, `suggested_tests`, `expected_days`, `disclaimer` (the clinic view must say what the data is).
- `CentreWhatIfIn.tau2` (optional); `CentreWhatIfOut`: `from_version`, `to_version`, `tau2`, `rescored`, `details[{case_id, before, after, direction}]`, `ms`, `graph`.
- New models/routes: `GET /centre/cases`, `GET/POST /centre/notes`, `GET /centre/protocols`, `GET /centre/workload`, `GET /centre/inspector` (the centre's recent queries: name, Cypher, params, rows, ms; no free text — note text is redacted like other free text). `GET /centre/lookalikes` takes `case_id` or `terms`; `GET /centre/clusters` takes `method=lp|wcc`.
- Centre routes carry no parent data and no auth: the graph is synthetic and labelled so. `/centre/whatif` is rate limited (6/min) because it copies a graph.
- Demo-only seams (review P5): notes and the what-if are unauthenticated writes. The what-if holds a lock (a second concurrent run is refused) and notes are capped at 50 in total; a real deployment would put both behind staff authentication. The `GRAPH.COPY` isolates the audit write-back (`KbUpdate`, `AFFECTED`, new `rare_mass` values) so the live centre is never modified; the rescoring itself reads the two kb graphs.
