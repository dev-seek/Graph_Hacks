---
phase: P2
title: Graph-first engine, gates, safety, simulator
model: sonnet
advisor: opus
effort: high
max_budget_usd: 20
needs_reviewed_files: [review/safety_rules.yaml, review/negatives.yaml]
---
## Goal
Deterministic scoring, planning, gating and safety over graph-returned rows, beating simple baselines on the dev split with a controlled false-alarm rate. API contracts frozen.

## First step
Run `make review-check`. If `safety_rules.yaml` or `negatives.yaml` fails or is not REVIEWED: set `status: needs-human`, name the file and the first error under "Needs from human", end the turn.

## Read (only when needed)
§7 `05-scoring.md` · §8 `06-planner-gates-safety.md` · §13 Q1–Q3 `11-cypher.md` · §14 `12-eval.md` · §12 `10-api-mcp.md` (schemas only) · DECISIONS rows 3, 5–7.

## Tasks
1. `test-engineer`: failing tests for the LR table (hand-computed fixtures), pruning, decay, NOT, noise, absent + obligate cap, γ on/off, D₀ decay, unlinked-mass term, invariants (Hypothesis), planner rules (age gate, branch memory, ≤ 2 per system, no overlap, IG ≥ 0), each gate at and just below threshold.
2. Q1, Q2a–d, Q3 in the query registry with integration tests on a small real kb.
3. `engine/` pure functions over query rows; reasoner fails closed (503) without FalkorDB.
4. Safety engine: loads `review/safety_rules.yaml`, validates it, runs the corpus inside it (must be 60/60 — if a rule fails its own corpus, report the failing items under "Needs from human" as non-blocking and continue with the passing rules); LLM `safety_extra` add-only.
5. Resolve `review/negatives.yaml` to HPO terms via Q0 → `data/derived/negatives.resolved.yaml`.
6. Simulator (unmentioned → 90% unsure / 10% no; sweep 0/30%), B0, B1, B2, metrics with bootstrap CIs, `make eval-smoke`.
7. Tuning on DEV + negatives only, by these pre-declared rules (no human choice needed):
   - ε, λ, w, γ on/off, π₀, β: grid search maximising dev MRR after 3 rounds, subject to false referral ≤ 10% on negatives.
   - τ1 (see doctor), τ2 (referral), τ0: choose the values that maximise referral sensitivity on dev positives subject to false referral ≤ 10% and false see-doctor ≤ 30% on negatives; ties → the more conservative (higher τ2).
   - Write ADRs 0003–0006 with the chosen values and the trade-off chart (PNG in docs/adr/).
8. Benchmark per round: Q1+Q2 < 300 ms, scoring < 100 ms, planner < 500 ms.
9. Freeze `backend/app/api/schemas.py`; export OpenAPI; recursive parent-key test.

## Gate
- Unit + property + integration tests green; benchmark within budget.
- Dev: Ours > B0, B1 and B2 on top-10 after 3 rounds (with CIs).
- Negatives at chosen τ: false referral ≤ 10%, false see-doctor ≤ 30%.
- Safety corpus result recorded.

## Handoff note
Chosen values (link ADRs), dev table, anything fragile.
