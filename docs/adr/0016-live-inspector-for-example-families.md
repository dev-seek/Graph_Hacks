# ADR-0016: live inspector for example families

Status: accepted (P6). Date: 2026-10-17.

## Context
The live inspector is on the never-cut list. Until P6 the demo pages replayed the queries recorded when each example family was run, and
`GET /api/debug/queries` only worked for the scripted (demo-flagged) families, which a visitor could not create. So a judge could not watch
queries run for their own click-through.

## Decision
- `POST /api/demo/families` creates a demo-flagged family (same limits as `POST /api/families`). The web app's "Use an example story" button
  uses it; a family built from a visitor's own story still uses `POST /api/families`.
- Demo-flagged families already log their graph queries in memory (bounded, parameters redacted, no free text) and expose them at
  `GET /api/debug/queries` with the family token. Ordinary families still get 403 there.
- New page `/j/<id>/inspector` (linked from the journey page only when the API allows the log) lists the queries with their Cypher, rows and
  milliseconds.

## Consequences
- The parent API still never contains disease names or scores: the log holds query names, Cypher text, redacted parameters, row counts and timings.
- A visitor's example family is a demo family: it is erased with the rest after 7 days on the public demo.
- The replayed inspector on `/demo/*` is unchanged and still labelled as a recorded run.
