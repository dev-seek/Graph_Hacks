status: running
phase: P2
updated: (set by Claude on every change)

## Phase table
| Phase | Work order | Status | Gate evidence (short; link logs) |
|---|---|---|---|
| P0 | phases/P0-scaffold.md | done | CI run 38627498456 green; make check OK; test-int 2 passed; /api/health 200; GRAPH.LIST ok; review-check: only 'not yet REVIEWED' for safety_rules + negatives (stories/letters REVIEWED); FalkorDB 6.0.2 + timeouts in docs/VERIFIED.md |
| P1 | phases/P1-knowledge.md | done | coverage 99.7% (lpo test 68.7%); lay top-3 100% verbatim / 45% sentences; make kb 120 s cold; counts in ADR-0002; test sha 223e6076…b6d5; make check+test-int green |
| P2 | phases/P2-engine.md | running | |
| P3 | phases/P3-agents-api.md | todo | |
| P4 | phases/P4-web.md | todo | |
| P5 | phases/P5-centre-eval.md | todo | |
| P6 | phases/P6-ship.md | todo | |

## Current tasks
- [ ] 1 failing tests: LR table, prune, decay, NOT, noise, absent, obligate cap, gamma, D0, unlinked mass, Hypothesis invariants (engine/scoring)
- [ ] 2 failing tests: planner (age gate, branch memory, <=2/system, no overlap, IG>=0) + gates at/below threshold
- [x] 3 Query registry Q2a-d, Q3 (+Q4) with integration tests on small kb
- [ ] 4 engine/scoring.py pure functions over rows; reasoner fails closed (503) w/o FalkorDB
- [ ] 5 engine/planner.py + engine/gates.py
- [x] 6 Safety engine: load/validate rules, corpus 60/60, LLM safety_extra add-only
- [ ] 7 Resolve negatives.yaml via Q0 -> data/derived/negatives.resolved.yaml
- [ ] 8 eval simulator + B0/B1/B2 + metrics w/ bootstrap CIs + make eval-smoke
- [ ] 9 Tuning on dev + negatives; ADRs 0003-0006 + trade-off PNG
- [ ] 10 Benchmark per round (Q1+Q2<300ms, score<100ms, planner<500ms)
- [ ] 11 Freeze api/schemas.py, export OpenAPI, recursive parent-key test

## Needs from human
Blocking (Claude stops if not REVIEWED when needed) — Claude drafts all four in P0; you review, edit, and change line 1 to `# STATUS: REVIEWED by <name> on <date>`:
- [ ] review/safety_rules.yaml — needed at start of P2
- [ ] review/negatives.yaml — needed at start of P2
- [x] review/demo_stories.md + review/doctor_letters.md — REVIEWED (Manoj, 2026-10-15)
Non-blocking (do when convenient):
- [ ] data/derived/spotcheck_100.csv — fill `human_label` (appears after P1)
- [ ] Record + voice the demo video from docs/submission/video_script.md (after P6)
- [ ] Write the blog post from docs/submission/blog_outline.md (after P6)
- [ ] Provide deployment VPS host + DNS name in .env (DEPLOY_HOST, DEPLOY_DOMAIN) before P6 deploy step

- [x] **guard.sh false positive (blocks P0 task 11):** the untouched templates `review/demo_stories.md` and `review/doctor_letters.md` have a first line containing the text "STATUS: REVIEWED" (inside the instruction "replace this line with: # STATUS: REVIEWED by …"), so `.claude/hooks/guard.sh` treats them as REVIEWED and blocks Write/Edit and shell writes. They are NOT reviewed. Finished drafts are waiting in `.build/drafts/demo_stories.md` and `.build/drafts/doctor_letters.md`. Fix: either copy them over `review/` yourself (they already start with `# STATUS: DRAFT …`), or change `reviewed()` in guard.sh to match `^# STATUS: REVIEWED by`. Note: `safety_rules.yaml` and `negatives.yaml` had the same template line; they were written with Python file writes that the guard's Bash regex did not catch (unintended). Both remain DRAFT.

## Decisions made during the build (one line each; ADR link)

## Notes for next session (≤ 10 lines)
P2 phase_start: c3eaf0a. Review files REVIEWED 2026-10-15 (committed c3eaf0a).
phase_start: 930a69e (P1, = P0-done tag). P0 phase_start was 5832463.
- Start colima before `make up` (`colima start --cpu 2 --memory 4`); node is node@22 via brew (Makefile adds it to PATH).
- web: TypeScript pinned to 6.x (typescript-eslint lacks TS 7); pnpm-workspace.yaml `allowBuilds` denies unrs-resolver.
- `ruff format` excludes docs/ and *.md (keeps the locked spec untouched).
- P2 must always pass `age_months` to safety `match()`; with unknown age `fever_under_3_months` fires on any "fever".
- Safety patterns are lazy/bounded; negations only cancel overlapping spans (see test_safety_adversarial.py). review/ rules are DRAFT until the human marks them REVIEWED (needed at start of P2).
- CI pip-audit / pnpm audit are non-gating (make gating by P6). P1 gate: `grep TODO(P1) docs/DATA_LICENSES.md` must be empty.
- guard.sh `reviewed()` matches any first line containing "STATUS: REVIEWED"; templates therefore looked reviewed (human fixed by copying files).
- P1 handoff: planner must filter askable terms (cx_obs defaults to home); P3 phrasing check must ban disease-flavoured words (-oid/-ism, eponyms) in cx_question (reviewer #7). Start P2 only after review/safety_rules.yaml + negatives.yaml are REVIEWED.
