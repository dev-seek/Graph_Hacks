---
phase: P5
title: Centre brain (Track 3) + frozen evaluation
model: sonnet
advisor: opus
effort: high
max_budget_usd: 15
needs_reviewed_files: []
---
## Goal
A clinic's shared memory that answers "who solved cases like this, with which protocol" and re-checks open cases when knowledge changes; plus one honest run on the frozen test split.

## Read (only when needed)
§9 centre agent `07-agents.md` · §11.3 `09-graph-model.md` · §12 centre routes `10-api-mcp.md` · §13 Q7, Q8 `11-cypher.md` · §14 `12-eval.md` · cheat sheet §5–6.

## Tasks
1. Seed `centre` from DEV cases only (~250 resolved, ~50 open; `synthetic: true`), HAS_ANC closure, SIMILAR_TO (IC-weighted overlap in Python, top-5, written back).
2. Clinicians (6–8 role pseudonyms with specialties), DiagnosticProtocols (5–8), CaseDecisions assigned by simple documented rules (diagnosis type → protocol; specialty → clinician). Write the rules into an ADR. All labelled "illustrative clinic data" in the UI.
3. Verify exact names/yields of `algo.betweenness`, `algo.WCC`, `algo.labelPropagation` against the pinned image; log in VERIFIED.md.
4. Q7 routing, Q8 algorithms, notes, what-if (`GRAPH.COPY centre centre_whatif`; rescore open cases on the newer kb if two KB versions exist, else under a changed τ2), "ask the centre" (task `centre_template_pick`; never free Cypher; keyword fallback); inspector timings.
5. Centre dashboard page; API routes.
6. Frozen evaluation: run ONCE on the test split with `kb_<release>_lpo` and once with the standard kb. Never change parameters after seeing results; bugs → fix, note, re-run.
7. Report `eval/reports/<date>.md` + JSON + charts; headline = lpo.

## Gate
- Centre queries < 2 s (routing target < 100 ms); dashboard works on seeded data.
- Evaluation report committed with CIs, coverage %, negatives false rates, sensitivity sweep.

## Handoff note
Headline numbers (one line), any caveat the README must state.
