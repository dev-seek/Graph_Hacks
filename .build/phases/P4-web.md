---
phase: P4
title: Web experience + live FalkorDB inspector
model: sonnet
advisor: opus
effort: high
max_budget_usd: 15
needs_reviewed_files: []
---
## Goal
A calm, legible, accessible web app that a worried parent understands in 10 seconds, a clinician view, and a demo mode where judges watch FalkorDB do the work.

## Read (only when needed)
§4 `02-ux.md` · §6 `03-design-copy.md` (all of it) · §12 `10-api-mcp.md` (routes only).

## Tasks
1. Generate TypeScript types from the frozen OpenAPI.
2. Routes per §4.1; one main action per screen; copy from §6.4–6.5 verbatim.
3. Constellation visual (SVG; stars as findings confirm; respects prefers-reduced-motion).
4. Question rounds with aria-live; age-appropriate wording from the API.
5. Doctor step; printable pack (A4 + Letter; clinician code + QR).
6. Clinician view: findings with sources, candidates with explanation paths, suggested checks, referral draft, "Download Phenopacket".
7. /about: exact attributions (§5), limitations (§19), AI disclosure (what Claude drafted, what the human decided and reviewed).
8. /demo: Kabir, Arjun, Maya step-through with captions + the live inspector (split screen: query name, Cypher, rows, ms, gate numbers, cytoscape evidence subgraph).
9. Guided tour, example story, contextual help and `/help` per §4.7 (parent, clinician, centre tours).
10. Lint rule or unit test: parent-view strings contain no banned words and no disease names (lexicon generated from kb).
11. Tests: Vitest components; Playwright three journeys (replay), keyboard-only Kabir, keyboard-only tour (next/back/skip/reopen), "Use an example story" reaches round 1 in two clicks, 360 px, axe-core clean, parent DOM contains no disease names.
12. Run `copy-a11y-reviewer`; apply its replacements (except §6.5 mandatory texts).

## Gate
- Playwright + axe green; Lighthouse accessibility ≥ 95 on /, /demo, a round page.
- Screenshots at 360 px and 1280 px saved in `docs/explain/P4-screens/`.

## Handoff note
Known UI gaps; anything the video script should show.
