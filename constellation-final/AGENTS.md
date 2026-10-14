# AGENTS.md — Constellation (rules for every coding agent)

Scope: **hackathon build only.** The spec in `docs/spec/` is locked (v2); locked decisions are in `docs/DECISIONS.md` — do not reopen them. Progress lives in `.build/STATE.md`; work orders in `.build/phases/`. When this file and the spec disagree, this file wins; record the conflict in STATE.md.

## The product in one paragraph
Constellation helps families of children and teenagers (0–20) with unexplained health problems gather the right evidence and reach the right specialist sooner. The parent tells the story; the agent asks small rounds of plain questions; when evidence is strong enough it says "see a doctor" and produces a one-page doctor pack; doctor findings come back in; when the pattern fits rare conditions strongly it drafts a referral letter plus a GA4GH Phenopacket v2 file; it keeps watching for years. A Centre brain gives a clinic shared memory (look-alike cases, who solved them, with which protocol). FalkorDB is the memory and reasoning substrate. Hackathon: WeMakeDevs × FalkorDB "Graph Hacks", all three tracks.

## Non-negotiables (never break, not even temporarily, not even in tests or demo data)
1. **Not a diagnosis tool.** Parent-facing API and UI never contain disease names, probabilities or rankings. Candidates appear only in the clinician view with the disclaimer.
2. **Safety first.** Deterministic red-flag rules (`review/safety_rules.yaml`) run on every parent message, answer batch and document before anything else. An LLM may only add a flag, never remove one.
3. **Code decides, the LLM talks.** Scores, rankings, gates and red flags come only from `backend/app/engine/` and `backend/app/safety/`.
4. **Graph-first (hackathon Rule 3).** Pruning, candidate retrieval, planner inputs and explanations run as Cypher on FalkorDB every round (spec §13). Python does arithmetic on returned rows. Only allowed in-memory structure: the HPO ancestor-set cache. No code path may produce candidates or scores without FalkorDB.
5. **LLM = Claude, behind one port (spec §10).** All LLM calls go through `LLMPort` via `backend/app/llm/router.py`. The `anthropic` SDK is imported only in `backend/app/llm/adapters/anthropic_adapter.py`; model IDs appear only in `config/llm.yaml`. Every LLM task has a deterministic fallback. Tests use `fake` or `replay`; tests never call the network. The key comes only from `ANTHROPIC_API_KEY`.
6. **Data.** Only public, licensed or synthetic data. Never real patient data. Demo families and centre seed come from the dev split only.
7. **Licences.** Never alter HPO content (our labels are separate `cx_*` properties). Drop HPOA rows with `OMIM:` source **and** `IEA` evidence unless `KB_INCLUDE_OMIM_IEA=true`. Attributions exactly as spec §5.
8. **FalkorDB hygiene.** Official `falkordb` client; parameterised queries only; `ro_query` for reads; timeouts on every query; all Cypher in the query registry (`backend/app/graph/queries/`); guardrails in `docs/FALKORDB_CHEATSHEET.md` §7–8.
9. **Frozen test split.** Never tune on it or inspect per-case test output. Test runs use `kb_<release>_lpo`; hits count only via exact mappings.
10. **Reviewed inputs and honest disclosure (hackathon Rules 11–13).** `review/` holds the inputs that need human judgement: safety rules, 40 common-case vignettes, demo stories, doctor letters. You draft them in P0 and set their first line to `# STATUS: DRAFT — drafted by Claude, awaiting human review`. The human reviews and edits them and changes that line to `# STATUS: REVIEWED by <name> on <date>`. Once a file says REVIEWED, never edit it (a hook blocks this). If a needed file is not REVIEWED, set `status: needs-human`. In `docs/AI_USAGE.md`, record truthfully who drafted and who reviewed each part. Never try to make AI-written text pass as human-written.
11. **Secrets.** `.env` is git-ignored; `.env.example` lists names only; never print keys. The user's email address is never sent to any service.
12. **Pinned versions everywhere**, including the FalkorDB Docker image tag (never `latest`).
13. **Hackathon scope only.** Build the seams in spec §17.1 (interfaces), never the production features behind them.

## Commands (all through the Makefile; quiet by default — full output goes to `.build/logs/`)
| Command | What it does |
|---|---|
| `make setup` | install Python (uv) + web (pnpm) deps, pre-commit |
| `make data` / `make kb` | download pinned data + verify checksums / build `kb_<release>` and `kb_<release>_lpo` |
| `make up` / `make down` | start / stop docker compose |
| `make check` | lint + typecheck + unit tests (< 60 s); prints a ≤ 30-line summary |
| `make test-int` | integration tests against FalkorDB |
| `make llm-key-check` | prints whether `ANTHROPIC_API_KEY` is set in `.env` (never the value) |
| `make review-check` | validate `review/` files: schema, no leftovers, first line REVIEWED (exit 1 with a short reason per file) |
| `make eval-smoke` / `make eval` | 30 dev cases, 3 rounds / full frozen-test evaluation |
| `make llm-contract` | per-task contract suite; writes the cheapest passing Claude profile to config (spec §10.6) |
| `make demo-record` / `make demo-replay` | record / replay the three demo journeys |
| `make web` / `make e2e` | web dev server / Playwright end-to-end (replay mode) |

## Repo map
```
backend/app/  api/ agents/ engine/ graph/(queries/) kb/ llm/(port.py router.py adapters/{anthropic_adapter,fake,replay}.py prompts/) safety/ mcp/
config/       llm.yaml (no secrets), app settings
review/       inputs drafted by Claude, reviewed by the human: safety_rules.yaml, negatives.yaml, demo_stories.md, doctor_letters.md
eval/         simulator, baselines, metrics, splits/, reports/
web/          Next.js app (parent, clinician, centre, demo + live inspector)
data/         raw/ (git-ignored), fixtures/ (synthetic test ontology), derived/, llm_cache/
docs/         spec/ (locked), DECISIONS.md, FALKORDB_CHEATSHEET.md, VERIFIED.md, adr/, explain/, AI_USAGE.md, DATA_LICENSES.md
.build/       STATE.md (progress), phases/ (work orders), logs/ (git-ignored)
```

## Engineering rules
- Tests first for engine, safety, kb parsers, gates, planner; property tests (Hypothesis) for scoring invariants. Integration test for every registry query.
- Python 3.12 + uv lockfile; Node 22 + pnpm lockfile; pyright strict on core packages; Pydantic v2 at every boundary; TypeScript strict.
- Conventional commits, one logical change each, `make check` green first, pushed right away (format and rules: CLAUDE.md "Git history"). Tag each passed phase `<phase>-done`.
- ADR in `docs/adr/` for any choice that changes architecture, data, scoring or safety, and for every tuned value.
- Verify before use: any API, Cypher feature, config option or version not yet in `docs/VERIFIED.md` must be proven by docs + a test, then logged. Never invent an API.
- FalkorDBSaver: only put / `get_state` / `list(limit=…)`; not `copy_thread`, `delete_for_runs`, `prune`.
- structlog JSON; never log raw parent text at INFO.
- Two failed attempts on the same error → change approach; three → `status: blocked` with a 5-line note.

## Definition of done (every task)
`make check` green; integration test if it touches FalkorDB; copy follows spec §6; accessibility checked for UI; STATE.md ticked; committed with a proper message; pushed.

## Scope control (no deadlines here — build everything, properly)
There is no time pressure inside a session: never skip tests, gates or quality to go faster. Cut a feature only if the human writes `cut: <numbers>` under "Notes for next session" in STATE.md. Cut order, from the top: 1) two real KB versions; 2) GRAPH.COPY what-if; 3) "ask the centre"; 4) PDF upload beyond one sample; 5) vector index (keep full-text + LLM guess); 6) MCP to 2 tools. **Never cut:** safety rules, parent-view rules, graph-first rounds, frozen `lpo` evaluation, live inspector, doctor pack, Phenopacket export, README graph model + Cypher list, AI disclosure.
