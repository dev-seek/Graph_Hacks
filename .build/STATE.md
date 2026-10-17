status: done
phase: done
updated: 2026-10-17 (P6 gate closed; build complete)

## Phase table
| Phase | Work order | Status | Gate evidence (short; link logs) |
|---|---|---|---|
| P0 | phases/P0-scaffold.md | done | CI run 38627498456 green; make check OK; test-int 2 passed; /api/health 200; GRAPH.LIST ok; review-check: only 'not yet REVIEWED' for safety_rules + negatives (stories/letters REVIEWED); FalkorDB 6.0.2 + timeouts in docs/VERIFIED.md |
| P1 | phases/P1-knowledge.md | done | coverage 99.7% (lpo test 68.7%); lay top-3 100% verbatim / 45% sentences; make kb 120 s cold; counts in ADR-0002; test sha 223e6076…b6d5; make check+test-int green |
| P2 | phases/P2-engine.md | done | held-out 400 dev: top-10 Ours 60.2% vs B0 56.2 / B1 58.5 / B2 60.5 (gate as worded NOT met, human option a, ADR-0007); negatives false referral 0%, false see-doctor 20%; safety corpus 60/60; bench p90 retrieve 80 / score 31 / plan 98 ms; make check + test-int green |
| P3 | phases/P3-agents-api.md | done | journeys green on fake+off (+ urgent, restart in 2 processes, injection, erasure); parent-route auth 401 on every route + payload scan; Phenopacket validated (official protobuf); MCP 4 tools list+call; demo-replay reproduces Kabir/Arjun/Maya offline; LLM profiles NOT measured (no key, ADR-0009); make check + test-int (64) green |
| P4 | phases/P4-web.md | done | Lighthouse a11y 100/100/100 (/, /demo, round page; make lighthouse); 26 Playwright (axe WCAG2.2 AA on 12+ pages, keyboard-only journey/Kabir demo/tour, 360 px, parent DOM free of banned words + 19,680 disease names) + 41 Vitest; make check + test-int (65) green; screenshots 360/1280 + A4/Letter PDFs in docs/explain/P4-screens/; lexicon kb_20260901 probed (0 collisions); ADR-0012 |
| P5 | phases/P5-centre-eval.md | done | frozen test 5,336 cases, lpo headline top-1 3.4% / top-10 13.0% (14.3% after doctor), level with B2, +0.7..+1.7 pts over B0 (report eval/reports/2026-10-16-test.md); negatives 0% false referral / 22.5% false see-doctor; centre routing p90 <100 ms, other centre queries <2 s; centre e2e + axe pass; make check + test-int (76) green; ADRs 0013-0015 |
| P6 | phases/P6-ship.md | done | CI green (run 38989853255 on the live-inspector commit; audits gating); fresh `git clone` + separate compose project: setup+data+up+seed 3.3 min (warm caches; 4 min first run), then make check, test-int (77) and make demo-replay green; 29 Playwright tests through Caddy (CSP/HSTS) + 31 local; Lighthouse a11y 100/100/100; pip-audit, pnpm audit, gitleaks (92 commits) clean; live inspector wired (ADR-0016); deploy doc ready, NOT deployed (no DEPLOY_HOST/DOMAIN); reviewer: 0 blockers, 3 SHOULD fixed; ADR-0016 |

## Current tasks
(none: build complete)

## Needs from human
- [ ] (non-blocking) Review ADR-0012 (441 disease names that equal HPO sign labels are exempt from the parent-text check; a few, e.g. "Acute myeloid leukemia", read as diagnoses)
- [ ] (non-blocking) Official HPO logo file for footer/About (HPO requests it); not added
- [ ] (non-blocking) set ANTHROPIC_API_KEY in .env then `make llm-contract` to measure profiles (ADR-0009 says not measured); then re-record demos with LLM_MODE=record
Blocking: none. Remaining human-only items (all in docs/submission/checklist.md):
- [ ] Provide DEPLOY_HOST + DEPLOY_DOMAIN (or deploy yourself with docs/submission/deploy.md), then put the live URL in the README table and run `E2E_BASE_URL=https://<domain> pnpm --dir web e2e`
- [ ] Record + voice the 3-minute video (docs/submission/video_script.md); write the blog post (docs/submission/blog_outline.md); add team and tagline to the README
- [ ] Make the GitHub repo public (the /help link to docs/USER_GUIDE.md 404s until then); ask on Discord whether one project can win several tracks; submit the form naming all three tracks
- [ ] (non-blocking) Delete the leftover temp clone `~/Documents/cx-fresh-clone` (my `rm -rf` was denied; not retried)
- [ ] (non-blocking) Review the "pending (human)" rows in docs/AI_USAGE.md, or leave them marked pending
- [x] P2 gate decision: option (a) (Manoj, 2026-10-15) — see Decisions.
- [x] review/safety_rules.yaml + review/negatives.yaml — REVIEWED (Manoj, 2026-10-15, commit c3eaf0a)
- [x] review/demo_stories.md + review/doctor_letters.md — REVIEWED (Manoj, 2026-10-15)
- [x] guard.sh false positive: human approved the fix (task 12).
- [x] negatives.curated.yaml: 6 corrections accepted by Manoj (task 13).
Non-blocking (do when convenient):
- [ ] data/derived/spotcheck_100.csv — fill `human_label`
- [ ] File the FalkorDB UNWIND issue upstream: it STILL reproduces on 6.0.2 and edge-rs (2026-10-15), not on v4.22.1; repro in docs/VERIFIED.md
- [ ] Provide deployment VPS host + DNS name in .env (DEPLOY_HOST, DEPLOY_DOMAIN) before P6 deploy step

## Decisions made during the build
- P4: lexicon probe (scripts/export_lexicon.py, 20,087 disease names, `make lexicon`) found 0 collisions with recorded demo parent text, even at min length 4: no ADR needed. `CLINICIAN_DISCLAIMER` in frozen schemas.py is not the §6.5 text; web shows §6.5 verbatim from `web/src/copy.ts` (API field left unchanged). "Use an example story" auto-confirms (made-up, labelled) so round 1 is two clicks away.
- Spec §10 model id `claude-haiku-5-5` is not a verified id; `config/llm.yaml` uses `claude-haiku-4-5` (conflict with the locked spec, AGENTS.md rule wins; ADR-0009). Parent-askable filter changes planner inputs (ADR-0011).
- P3 demos recorded with LLM_MODE=off (no ANTHROPIC_API_KEY): fallback extraction + parent accepting list items related to the matched dev case. Kabir case PMID_40215970_F11_II_2 (22 signs, similarity 0.306, REFERRAL_READY; the earlier "PMID_33674768 / 0.379" note was stale: P3-done already had this case), Arjun = neg08 (no escalation), Maya urgent. Query embeddings cached in data/demo/query_embeddings.json so replay needs no model/network. ADR-0009/0010. (one line each; ADR link)
- Spec §7 invariant 'absent obligate >= x500' asserted on lr_absent only: the locked +-ln100 clip caps the combined effect at x100 (no scoring change made).
- Candidate set = diseases from Q2a u Q2b u Q2c; priors are rescaled in engine to sum 1-pi0 over diseases with >=1 phenotype (Q2g).
- P2 gate (human decision, Manoj, 2026-10-15): option (a). Held-out dev (400 cases, disjoint from the 120 tuning cases): Ours beats B0 (paired top-10 +1.0..+7.3 pts) and is level with B1 (-1.5..+4.7) and B2 (-3.3..+2.7); MRR Ours 0.369 vs B2 0.368. The gate as worded ("Ours > B0, B1 and B2") is NOT met; this is recorded and reported honestly, not reworded. No re-tuning toward B2 and no planner change. Thresholds τ0/τ1/τ2 = 0.30/0.40/0.50 stay (ADR-0006: referral sensitivity ≈21% on dev, 25% of dev positives end at "mention at routine visit"; 0% false referral, 22.5% false see-doctor on negatives). ADR-0007.

## Notes for next session (≤ 10 lines)
- P6 handoff (build complete): after ANY FalkorDB restart use `make reset` (docs/VERIFIED.md: a restarted volume drifts in term search even after re-seeding; a fresh volume is deterministic). Colima shares only $HOME with the VM (clones outside it get empty bind mounts). Prod stack: `docker-compose.prod.yml` + `Caddyfile`; local run: `HTTP_PORT=8088 docker compose -f docker-compose.prod.yml up`, e2e via `E2E_BASE_URL`.
- phase_start P6: e986f82 (= tag P5-done)
- P5 handoff: headline lpo top-10 13.0% (after doctor 14.3%); Ours does NOT beat B2 (README must say so); referral sensitivity ~13%; lpo only 68.7% of test targets still annotated. After any FalkorDB restart run `make kb && make kb-prev && make centre` (VERIFIED.md). Centre what-if first run ~40 s. Don't run e2e while heavy jobs run.
- P5 frozen run: `.build/frozen/test_checkpoint.jsonl` (git-ignored, never open it). Resume: `PYTHONPATH=backend nohup uv run python -u -m app.eval.frozen test all 6`; progress in .build/logs/frozen-test.log. Then `python -m app.eval.frozen_report test` and `python -m app.eval.frozen_render <json>`. Do not run e2e/builds while it runs (FalkorDB crashed once under load; error rows are retried on resume). `make centre` after any FalkorDB restart (centre graph is not persisted until a BGSAVE).
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