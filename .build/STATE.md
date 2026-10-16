status: running
phase: P5
updated: 2026-10-15 22:20 IST (human gate decision; negatives map corrected)

## Phase table
| Phase | Work order | Status | Gate evidence (short; link logs) |
|---|---|---|---|
| P0 | phases/P0-scaffold.md | done | CI run 38627498456 green; make check OK; test-int 2 passed; /api/health 200; GRAPH.LIST ok; review-check: only 'not yet REVIEWED' for safety_rules + negatives (stories/letters REVIEWED); FalkorDB 6.0.2 + timeouts in docs/VERIFIED.md |
| P1 | phases/P1-knowledge.md | done | coverage 99.7% (lpo test 68.7%); lay top-3 100% verbatim / 45% sentences; make kb 120 s cold; counts in ADR-0002; test sha 223e6076…b6d5; make check+test-int green |
| P2 | phases/P2-engine.md | done | held-out 400 dev: top-10 Ours 60.2% vs B0 56.2 / B1 58.5 / B2 60.5 (gate as worded NOT met, human option a, ADR-0007); negatives false referral 0%, false see-doctor 20%; safety corpus 60/60; bench p90 retrieve 80 / score 31 / plan 98 ms; make check + test-int green |
| P3 | phases/P3-agents-api.md | done | journeys green on fake+off (+ urgent, restart in 2 processes, injection, erasure); parent-route auth 401 on every route + payload scan; Phenopacket validated (official protobuf); MCP 4 tools list+call; demo-replay reproduces Kabir/Arjun/Maya offline; LLM profiles NOT measured (no key, ADR-0009); make check + test-int (64) green |
| P4 | phases/P4-web.md | done | Lighthouse a11y 100/100/100 (/, /demo, round page; make lighthouse); 26 Playwright (axe WCAG2.2 AA on 12+ pages, keyboard-only journey/Kabir demo/tour, 360 px, parent DOM free of banned words + 19,680 disease names) + 41 Vitest; make check + test-int (65) green; screenshots 360/1280 + A4/Letter PDFs in docs/explain/P4-screens/; lexicon kb_20260901 probed (0 collisions); ADR-0012 |
| P5 | phases/P5-centre-eval.md | todo | |
| P6 | phases/P6-ship.md | todo | |

## Current tasks
- [x] 1 Probe algo.* + GRAPH.COPY on pinned image; log VERIFIED.md
- [x] 2 `make eval` harness (resumable, aggregates only, timeouts counted) + dev dry run, timing
- [x] 3 Pre-registration ADR (case list fixed on standard kb; lpo misses counted; scope; SHA check) committed BEFORE any test run
- [ ] 4 Start frozen run in background (lpo + standard)
- [ ] 5 Older KB (two real releases): verify tag/URL, build kb_<prev> (ADR)
- [ ] 6 Centre seed `make centre` (cases, HAS_ANC, SIMILAR_TO, clinicians, protocols, decisions; ADR rules)
- [ ] 7 Q7 routing (ancestor expansion, UNWIND-safe) + MCP update + int test
- [ ] 8 Q8 algorithms (bridges, WCC, label propagation)
- [ ] 9 Notes
- [ ] 10 What-if (GRAPH.COPY, rescore open cases, KbUpdate)
- [ ] 11 Ask the centre (centre_template_pick, fallback, whitelist)
- [ ] 12 API routes + benchmark test (routing p90<100ms, others <2s)
- [ ] 13 Centre dashboard page (copy-a11y-reviewer, axe, Playwright)
- [ ] 14 Report eval/reports/<date>.md + JSON + charts; gate

## Needs from human
- [ ] (non-blocking) Review ADR-0012 (441 disease names that equal HPO sign labels are exempt from the parent-text check; a few, e.g. "Acute myeloid leukemia", read as diagnoses)
- [ ] (non-blocking) Official HPO logo file for footer/About (HPO requests it); not added
- [ ] (non-blocking) set ANTHROPIC_API_KEY in .env then `make llm-contract` to measure profiles (ADR-0009 says not measured); then re-record demos with LLM_MODE=record
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

## Decisions made during the build
- P4: lexicon probe (scripts/export_lexicon.py, 20,087 disease names, `make lexicon`) found 0 collisions with recorded demo parent text, even at min length 4: no ADR needed. `CLINICIAN_DISCLAIMER` in frozen schemas.py is not the §6.5 text; web shows §6.5 verbatim from `web/src/copy.ts` (API field left unchanged). "Use an example story" auto-confirms (made-up, labelled) so round 1 is two clicks away.
- Spec §10 model id `claude-haiku-5-5` is not a verified id; `config/llm.yaml` uses `claude-haiku-4-5` (conflict with the locked spec, AGENTS.md rule wins; ADR-0009). Parent-askable filter changes planner inputs (ADR-0011).
- P3 demos recorded with LLM_MODE=off (no ANTHROPIC_API_KEY): fallback extraction + parent accepting list items related to the matched dev case. Kabir case PMID_40215970_F11_II_2 (22 signs, similarity 0.306, REFERRAL_READY; the earlier "PMID_33674768 / 0.379" note was stale: P3-done already had this case), Arjun = neg08 (no escalation), Maya urgent. Query embeddings cached in data/demo/query_embeddings.json so replay needs no model/network. ADR-0009/0010. (one line each; ADR link)
- Spec §7 invariant 'absent obligate >= x500' asserted on lr_absent only: the locked +-ln100 clip caps the combined effect at x100 (no scoring change made).
- Candidate set = diseases from Q2a u Q2b u Q2c; priors are rescaled in engine to sum 1-pi0 over diseases with >=1 phenotype (Q2g).
- P2 gate (human decision, Manoj, 2026-10-15): option (a). Held-out dev (400 cases, disjoint from the 120 tuning cases): Ours beats B0 (paired top-10 +1.0..+7.3 pts) and is level with B1 (-1.5..+4.7) and B2 (-3.3..+2.7); MRR Ours 0.369 vs B2 0.368. The gate as worded ("Ours > B0, B1 and B2") is NOT met; this is recorded and reported honestly, not reworded. No re-tuning toward B2 and no planner change. Thresholds τ0/τ1/τ2 = 0.30/0.40/0.50 stay (ADR-0006: referral sensitivity ≈21% on dev, 25% of dev positives end at "mention at routine visit"; 0% false referral, 22.5% false see-doctor on negatives). ADR-0007.

## Notes for next session (≤ 10 lines)
- phase_start P5: 35ca415 (= tag P4-done)
- P4 handoff (known gaps): inspector replays RECORDED queries (/debug/queries is live but the UI does not call it; a live "run my family" panel needs an API/ADR); doctor step "Why now" shows the pack summary, not §4.2's three plain reasons; example story gives 1 question in round 1 (copy promises 3-5); with no key the demo clinician view/Phenopacket contain junk findings ("Community Paediatrics Clinic", "DOB…", "No seizures reported" as present): don't linger on them in the video; no-key story reader only splits clauses (free narratives end at "watching").
- Video should show: landing → example story → round → /demo/kabir?judge=1 (queries, gate numbers, graph) → pack print → clinician view → Phenopacket download → Maya urgent.
- Run `make lexicon` before the gate (needs FalkorDB). e2e: `make e2e` (own API :8010 LLM_MODE=off + prod web :3100); `make lighthouse`; screenshots: `SCREENSHOTS=1 pnpm --dir web e2e screens`.
- P3 handoff: re-record with `LLM_MODE=record make demo-record` after `make llm-contract` once a key exists. MCP http transport has no auth: localhost only. Daily watcher: WATCHER_INTERVAL_S. Two real KB versions + centre graph still to do (P5).
cut: 4
- phase_start: P3 230f8bd · P4 = tag P3-done (6cd1432) · P5 = tag P4-done · P0 5832463 · P1 930a69e (= P0-done) · P2 c3eaf0a (review files REVIEWED and committed at P2-done).
- negatives.curated.yaml: AI-drafted; IDs machine-checked vs HPO 2026-09-01 (all valid, none obsolete); 6 corrections accepted by Manoj 2026-10-15 (see task 13).
- Local env: `colima start --cpu 2 --memory 4` before `make up`; node@22 via brew (Makefile adds PATH); TypeScript pinned 6.x; pnpm-workspace `allowBuilds` denies unrs-resolver; `ruff format` excludes docs/ and *.md.
- Safety: always pass `age_months` to match() (unknown age makes `fever_under_3_months` fire on any "fever"); patterns lazy/bounded; negations cancel only overlapping spans (test_safety_adversarial.py).
- guard.sh may still block a Bash command that merely mentions a review/ file next to `>` (e.g. `->` in python); read review files via app.eval.negatives.load_negatives or the Read tool.
- CI pip-audit / pnpm audit are non-gating until P6 (make gating there).