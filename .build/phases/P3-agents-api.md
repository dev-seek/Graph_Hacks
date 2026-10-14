---
phase: P3
title: Agents, API, family memory, Phenopacket export, MCP, demo recording
model: sonnet
advisor: opus
effort: high
max_budget_usd: 20
needs_reviewed_files: [review/demo_stories.md, review/doctor_letters.md]   # needed for task 10 only
---
## Goal
The full family loop runs through the API with durable agent state in FalkorDB, every LLM task works with Claude (cheapest passing profile) or with its fallback, and the three demo journeys are recorded for zero-cost replay.

## Read (only when needed)
§3 `01-product.md` · §9 `07-agents.md` · §10 `08-llm.md` · §11.2 `09-graph-model.md` · §12 `10-api-mcp.md` · §17 `14-ops-security.md` · cheat sheet §1.

## Tasks
1. Spike (≤ 40 lines, then delete or keep as a test): LangGraph `interrupt()` + `Command(resume=…)` with FalkorDBSaver (`thread_id = family_<id>`), survives process restart; `get_state`, `list(limit=…)`. Log in VERIFIED.md. If it fails → `blocked` with evidence.
2. LLM layer per §10: `LLMPort`, router (profiles, budgets, timeouts, repair retry, fallback), adapters `anthropic` (`messages.parse` structured output, prompt caching, advisor profiles, batches), `fake`, `replay`; prompts per task. `make llm-contract`: if `make llm-key-check` prints `set`, run it and write the cheapest passing profile per task to `config/llm.yaml` + ADR; CI runs it against `fake` only.
3. Family graph repository (registry queries; REPLACED_BY corrections; TermRef copies).
4. Agent nodes per §9 including `exporter` (Phenopacket v2 JSON validated against the official schema).
5. API routes per §12; family bearer tokens (hashed), clinician codes; parent-key test on every parent route; rate limits.
6. Doctor pack data; doc reader (pasted text + one sample PDF fixture); referral draft; watcher ("advance 6 months" endpoint + daily scheduler); DELETE family (GRAPH.DELETE + checkpoints).
7. Live-inspector query log (name, Cypher, params without free text, rows, ms) for demo families.
8. MCP server, four read-only tools (§12), with a list-and-call test.
9. Tests: full Kabir-like journey on `fake` through every gate and the urgent path; resume after restart; injection letter changes nothing; all with `LLM_MODE=off` too (fallback path works end to end).
10. Demo recording: `make review-check` for demo_stories + doctor_letters (if invalid or not REVIEWED → `needs-human`, end turn). Pick dev cases per match_criteria (log choices + similarity in STATE). Record with `LLM_MODE=record` if `make llm-key-check` prints `set`; otherwise record with `LLM_MODE=off` (fallback outputs) and note it. `make demo-replay` must reproduce all three journeys with no keys.

## Gate
- Journey tests green on `fake` and `off`; resume-after-restart green; parent-key test green on every parent route; Phenopacket schema validation green; MCP tools callable.
- `make demo-replay` reproduces Kabir (referral), Arjun (no escalation), Maya (urgent stop) with no network.

## Handoff note
Which profiles won the contract suite and their cost per call; how the demos were recorded; anything fragile in the agent graph.
