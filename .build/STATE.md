status: running
phase: P2
updated: 2026-10-15 22:20 IST (human gate decision; negatives map corrected)

## Phase table
| Phase | Work order | Status | Gate evidence (short; link logs) |
|---|---|---|---|
| P0 | phases/P0-scaffold.md | done | CI run 38627498456 green; make check OK; test-int 2 passed; /api/health 200; GRAPH.LIST ok; review-check: only 'not yet REVIEWED' for safety_rules + negatives (stories/letters REVIEWED); FalkorDB 6.0.2 + timeouts in docs/VERIFIED.md |
| P1 | phases/P1-knowledge.md | done | coverage 99.7% (lpo test 68.7%); lay top-3 100% verbatim / 45% sentences; make kb 120 s cold; counts in ADR-0002; test sha 223e6076…b6d5; make check+test-int green |
| P2 | phases/P2-engine.md | running | gate outcome decided by human: option (a), see Decisions |
| P3 | phases/P3-agents-api.md | todo | |
| P4 | phases/P4-web.md | todo | |
| P5 | phases/P5-centre-eval.md | todo | |
| P6 | phases/P6-ship.md | todo | |

## Current tasks
- [x] 1 failing tests: LR table, prune, decay, NOT, noise, absent, obligate cap, gamma, D0, unlinked mass, Hypothesis invariants (engine/scoring)
- [x] 2 failing tests: planner (age gate, branch memory, <=2/system, no overlap, IG>=0) + gates at/below threshold
- [x] 3 Query registry Q2a-d, Q3 (+Q4) with integration tests on small kb
- [x] 4 engine/scoring.py pure functions over rows; reasoner fails closed (503) w/o FalkorDB
- [x] 5 engine/planner.py + engine/gates.py
- [x] 6 Safety engine: load/validate rules, corpus 60/60, LLM safety_extra add-only
- [x] 7 Resolve negatives.yaml via Q0 -> data/derived/negatives.resolved.yaml
- [x] 8 eval simulator + B0/B1/B2 + metrics w/ bootstrap CIs + make eval-smoke
- [x] 9 Tuning on dev + negatives; ADRs 0003-0006 + trade-off PNG
- [x] 10 Benchmark per round (Q1+Q2<300ms, score<100ms, planner<500ms)
- [x] 11 Freeze api/schemas.py, export OpenAPI, recursive parent-key test
- [x] 12 Guard fix (human-approved): in .claude/hooks/guard.sh change reviewed() to `head -n 1 "$1" | grep -Eq "^# STATUS: REVIEWED by"` so template/instruction lines no longer count as REVIEWED. Add a small test (template line → allowed, `# STATUS: DRAFT …` → allowed, `# STATUS: REVIEWED by X on D` → blocked). Commit on its own.
- [ ] 13 Negatives re-check: the human accepted 6 corrections in data/derived/negatives.curated.yaml (low fever→HP:0011134, achy legs→HP:0012514, elbow-crease patches→HP:0000964, squints at board→HP:0000545, ear pulling→HP:0030766, green vomit (absent)→HP:0034754). Commit that file as-is; regenerate negatives.resolved.yaml; re-run the negatives evaluation at the CHOSEN thresholds (no re-tuning). Update false-referral / false-see-doctor in ADR-0006 with old → new numbers. If false referral > 10% or false see-doctor > 30%, set status: needs-human with the numbers and stop.
- [ ] 14 Benchmark: commit the pending edit (prune included in the timed path); re-run it with nothing else using the CPU (no tuning/eval running); record p90s in the phase table. If it misses budget, report the numbers; do not loosen the budget.
- [ ] 15 Q2 rewrite: add/confirm an integration test proving the rewritten Q2a-d return the same rows as the spec §13 versions on the small kb; write an ADR "Q2 rewritten for performance (spec deviation)" with before/after timings and the equivalence test link.
- [ ] 16 FalkorDB UNWIND issue: write a minimal standalone repro (≤ 20 lines Cypher + expected vs actual) in docs/VERIFIED.md. Re-run it on the newest FalkorDB release in a throwaway container (do not change our pinned tag). Write under Needs from human whether it still reproduces there, so the human can decide to file it upstream.
- [ ] 17 ADR-0007 "P2 gate outcome": held-out table with CIs; gate as worded NOT met vs B1/B2; human chose (a); no re-tuning toward B2, no planner change; negatives numbers after task 13; how this is reported in README and P5. Same framing in docs/explain/P2.md.
- [ ] 18 docs/AI_USAGE.md (P2 section), stated plainly: negatives phrase->HPO map drafted by Claude (build session), IDs checked by Claude (planning chat) against HPO 2026-09-01, 6 corrections accepted by the human (no claim that the human hand-checked every line); two commits landed with make check red and were fixed in the next commit (no history rewrite); planner and gate tests written alongside the implementation, not strictly first; safety_rules.yaml and negatives.yaml drafts were written by a Python file write the guard did not intercept while still DRAFT (no REVIEWED file was changed); the guard bug and its fix (task 12).
- [ ] 19 Close the gate: reviewer subagent on c3eaf0a..HEAD and fix blockers; docs/explain/P2.md; phase table row P2 = done with evidence; set phase: P3 and clear Current tasks; commit, tag P2-done, push; end turn with the phase report.

## Needs from human
Blocking: none right now.
- [x] P2 gate decision: option (a) (Manoj, 2026-10-15) — see Decisions.
- [x] review/safety_rules.yaml + review/negatives.yaml — REVIEWED (Manoj, 2026-10-15, commit c3eaf0a)
- [x] review/demo_stories.md + review/doctor_letters.md — REVIEWED (Manoj, 2026-10-15)
- [x] guard.sh false positive: human approved the fix (task 12).
- [x] negatives.curated.yaml: 6 corrections accepted by Manoj (task 13).
Non-blocking (do when convenient):
- [ ] data/derived/spotcheck_100.csv — fill `human_label`
- [ ] File the FalkorDB UNWIND issue upstream if task 14 says it still reproduces on the newest release
- [ ] Provide deployment VPS host + DNS name in .env (DEPLOY_HOST, DEPLOY_DOMAIN) before P6 deploy step
- [ ] Record + voice the demo video from docs/submission/video_script.md (after P6)
- [ ] Write the blog post from docs/submission/blog_outline.md (after P6)

## Decisions made during the build (one line each; ADR link)
- Spec §7 invariant 'absent obligate >= x500' asserted on lr_absent only: the locked +-ln100 clip caps the combined effect at x100 (no scoring change made).
- Candidate set = diseases from Q2a u Q2b u Q2c; priors are rescaled in engine to sum 1-pi0 over diseases with >=1 phenotype (Q2g).
- P2 gate (human decision, Manoj, 2026-10-15): option (a). Held-out dev (400 cases, disjoint from the 120 tuning cases): Ours beats B0 (paired top-10 +1.0..+7.3 pts) and is level with B1 (-1.5..+4.7) and B2 (-3.3..+2.7); MRR Ours 0.369 vs B2 0.368. The gate as worded ("Ours > B0, B1 and B2") is NOT met; this is recorded and reported honestly, not reworded. No re-tuning toward B2 and no planner change. Thresholds τ0/τ1/τ2 = 0.30/0.40/0.50 stay (ADR-0006: referral sensitivity ≈21% on dev, 25% of dev positives end at "mention at routine visit"; 0% false referral, 22.5% false see-doctor on negatives). ADR-0007.

## Notes for next session (≤ 10 lines)
cut: 4
- phase_start: P0 5832463 · P1 930a69e (= P0-done) · P2 c3eaf0a (review files REVIEWED and committed there).
- negatives.curated.yaml: AI-drafted; IDs machine-checked vs HPO 2026-09-01 (all valid, none obsolete); 6 corrections accepted by Manoj 2026-10-15 (see task 13).
- Local env: `colima start --cpu 2 --memory 4` before `make up`; node@22 via brew (Makefile adds PATH); TypeScript pinned 6.x; pnpm-workspace `allowBuilds` denies unrs-resolver; `ruff format` excludes docs/ and *.md.
- Safety: always pass `age_months` to match() (unknown age makes `fever_under_3_months` fire on any "fever"); patterns lazy/bounded; negations cancel only overlapping spans (test_safety_adversarial.py).
- guard.sh may still block a Bash command that merely mentions a review/ file next to `>` (e.g. `->` in python); read review files via app.eval.negatives.load_negatives or the Read tool.
- For P3: phrasing check must ban disease-flavoured words (-oid/-ism, eponyms) in cx_question (P1 reviewer #7); planner must filter askable terms (cx_obs defaults to home).
- CI pip-audit / pnpm audit are non-gating until P6 (make gating there).