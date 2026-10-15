status: running
phase: P3
updated: 2026-10-15 22:20 IST (human gate decision; negatives map corrected)

## Phase table
| Phase | Work order | Status | Gate evidence (short; link logs) |
|---|---|---|---|
| P0 | phases/P0-scaffold.md | done | CI run 38627498456 green; make check OK; test-int 2 passed; /api/health 200; GRAPH.LIST ok; review-check: only 'not yet REVIEWED' for safety_rules + negatives (stories/letters REVIEWED); FalkorDB 6.0.2 + timeouts in docs/VERIFIED.md |
| P1 | phases/P1-knowledge.md | done | coverage 99.7% (lpo test 68.7%); lay top-3 100% verbatim / 45% sentences; make kb 120 s cold; counts in ADR-0002; test sha 223e6076…b6d5; make check+test-int green |
| P2 | phases/P2-engine.md | done | held-out 400 dev: top-10 Ours 60.2% vs B0 56.2 / B1 58.5 / B2 60.5 (gate as worded NOT met, human option a, ADR-0007); negatives false referral 0%, false see-doctor 20%; safety corpus 60/60; bench p90 retrieve 80 / score 31 / plan 98 ms; make check + test-int green |
| P3 | phases/P3-agents-api.md | todo | |
| P4 | phases/P4-web.md | todo | |
| P5 | phases/P5-centre-eval.md | todo | |
| P6 | phases/P6-ship.md | todo | |

## Current tasks
(empty; plan P3 at its start)

## Needs from human
Blocking: none right now.
- [x] P2 gate decision: option (a) (Manoj, 2026-10-15) — see Decisions.
- [x] review/safety_rules.yaml + review/negatives.yaml — REVIEWED (Manoj, 2026-10-15, commit c3eaf0a)
- [x] review/demo_stories.md + review/doctor_letters.md — REVIEWED (Manoj, 2026-10-15)
- [x] guard.sh false positive: human approved the fix (task 12).
- [x] negatives.curated.yaml: 6 corrections accepted by Manoj (task 13).
Non-blocking (do when convenient):
- [ ] data/derived/spotcheck_100.csv — fill `human_label`
- [ ] File the FalkorDB UNWIND issue upstream: it STILL reproduces on 6.0.2 and edge-rs (2026-10-15), not on v4.22.1; repro in docs/VERIFIED.md
- [ ] Provide deployment VPS host + DNS name in .env (DEPLOY_HOST, DEPLOY_DOMAIN) before P6 deploy step
- [ ] Record + voice the demo video from docs/submission/video_script.md (after P6)
- [ ] Write the blog post from docs/submission/blog_outline.md (after P6)

## Decisions made during the build (one line each; ADR link)
- Spec §7 invariant 'absent obligate >= x500' asserted on lr_absent only: the locked +-ln100 clip caps the combined effect at x100 (no scoring change made).
- Candidate set = diseases from Q2a u Q2b u Q2c; priors are rescaled in engine to sum 1-pi0 over diseases with >=1 phenotype (Q2g).
- P2 gate (human decision, Manoj, 2026-10-15): option (a). Held-out dev (400 cases, disjoint from the 120 tuning cases): Ours beats B0 (paired top-10 +1.0..+7.3 pts) and is level with B1 (-1.5..+4.7) and B2 (-3.3..+2.7); MRR Ours 0.369 vs B2 0.368. The gate as worded ("Ours > B0, B1 and B2") is NOT met; this is recorded and reported honestly, not reworded. No re-tuning toward B2 and no planner change. Thresholds τ0/τ1/τ2 = 0.30/0.40/0.50 stay (ADR-0006: referral sensitivity ≈21% on dev, 25% of dev positives end at "mention at routine visit"; 0% false referral, 22.5% false see-doctor on negatives). ADR-0007.

## Notes for next session (≤ 10 lines)
cut: 4
- P2 review: no blockers; fixed inline Cypher (negatives.py) + bounded Q2c/Q2e. Open minor: confirm test-int/eval round latency with 15+ findings in P3; parent-view string-value check in P3.
- phase_start: P0 5832463 · P1 930a69e (= P0-done) · P2 c3eaf0a · P3 = P2-done tag (review files REVIEWED and committed there).
- negatives.curated.yaml: AI-drafted; IDs machine-checked vs HPO 2026-09-01 (all valid, none obsolete); 6 corrections accepted by Manoj 2026-10-15 (see task 13).
- Local env: `colima start --cpu 2 --memory 4` before `make up`; node@22 via brew (Makefile adds PATH); TypeScript pinned 6.x; pnpm-workspace `allowBuilds` denies unrs-resolver; `ruff format` excludes docs/ and *.md.
- Safety: always pass `age_months` to match() (unknown age makes `fever_under_3_months` fire on any "fever"); patterns lazy/bounded; negations cancel only overlapping spans (test_safety_adversarial.py).
- guard.sh may still block a Bash command that merely mentions a review/ file next to `>` (e.g. `->` in python); read review files via app.eval.negatives.load_negatives or the Read tool.
- For P3: phrasing check must ban disease-flavoured words (-oid/-ism, eponyms) in cx_question (P1 reviewer #7); planner must filter askable terms (cx_obs defaults to home).
- CI pip-audit / pnpm audit are non-gating until P6 (make gating there).