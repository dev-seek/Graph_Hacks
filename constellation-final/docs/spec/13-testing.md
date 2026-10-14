<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 15. Testing strategy

| Layer | Tooling | What |
|---|---|---|
| Unit | pytest, Hypothesis | engine invariants (§7), planner rules, gates, safety corpus, HPOA/HPO/Orphanet/phenopacket parsers on fixtures, LLM schema validation & lexicon checks, API contract tests with the `fake` LLM adapter |
| Integration | pytest + FalkorDB container | kb build from a small real subset, every registry query, indexes exist, family lifecycle, delete, checkpointer interrupt/resume across process restart, centre algorithms |
| Agent | pytest | full journey on the `fake` adapter and with `LLM_MODE=off` (fallbacks) through every gate; replay-mode journey with recorded outputs |
| Web unit | Vitest + Testing Library | components, copy constants, no banned words in parent strings (lint rule) |
| E2E | Playwright | 3 demo journeys; parent DOM never contains any disease name from the kb lexicon; urgent banner above the fold; keyboard-only run of journey 1; axe-core no serious/critical violations; 360 px viewport |
| Eval | `make eval-smoke` | in CI; full eval manual |
| CI | GitHub Actions | lint, typecheck, unit, integration (FalkorDB service container, pinned image), e2e (replay), eval-smoke; cache downloaded data by manifest hash |

Coverage target: ≥ 90% lines on `engine/`, `safety/`, `kb/`; ≥ 75% overall backend. Coverage is a floor, not the goal — invariants and journeys matter more.
