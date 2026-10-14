status: running
phase: P0
updated: (set by Claude on every change)

## Phase table
| Phase | Work order | Status | Gate evidence (short; link logs) |
|---|---|---|---|
| P0 | phases/P0-scaffold.md | todo | |
| P1 | phases/P1-knowledge.md | todo | |
| P2 | phases/P2-engine.md | todo | |
| P3 | phases/P3-agents-api.md | todo | |
| P4 | phases/P4-web.md | todo | |
| P5 | phases/P5-centre-eval.md | todo | |
| P6 | phases/P6-ship.md | todo | |

## Current tasks
(empty — Claude writes ≤ 15 concrete tasks for the current phase here, then ticks them)

## Needs from human
Blocking (Claude stops if not REVIEWED when needed) — Claude drafts all four in P0; you review, edit, and change line 1 to `# STATUS: REVIEWED by <name> on <date>`:
- [ ] review/safety_rules.yaml — needed at start of P2
- [ ] review/negatives.yaml — needed at start of P2
- [ ] review/demo_stories.md + review/doctor_letters.md — needed for demo recording in P3
Non-blocking (do when convenient):
- [ ] data/derived/spotcheck_100.csv — fill `human_label` (appears after P1)
- [ ] Record + voice the demo video from docs/submission/video_script.md (after P6)
- [ ] Write the blog post from docs/submission/blog_outline.md (after P6)
- [ ] Provide deployment VPS host + DNS name in .env (DEPLOY_HOST, DEPLOY_DOMAIN) before P6 deploy step

## Decisions made during the build (one line each; ADR link)

## Notes for next session (≤ 10 lines)
