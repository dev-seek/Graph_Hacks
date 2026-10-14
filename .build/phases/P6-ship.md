---
phase: P6
title: Harden, deploy, README, submission drafts
model: sonnet
advisor: opus
effort: medium
max_budget_usd: 10
needs_reviewed_files: []
---
## Goal
A public repo that satisfies every submission rule, a live HTTPS deployment in replay mode, and drafts the human turns into the video and blog.

## Read (only when needed)
§17 `14-ops-security.md` · §18–20 `15-submission.md` · hackathon rules summary in DECISIONS.

## Tasks
1. Hardening: rate limits, upload limits, CSP/HSTS via Caddy, 7-day deletion job, pip-audit + pnpm audit (clean or justified), gitleaks clean.
2. Fresh-clone test: in a temp dir, follow only the README (`make setup data kb up`, `LLM_MODE=replay`); time it; fix every snag.
3. Deployment: if `DEPLOY_HOST` and `DEPLOY_DOMAIN` are set in `.env`, deploy with docker compose + Caddy (FalkorDB internal only; replay mode default; live mode rate-limited with a daily budget) and verify with Playwright against the live URL. If not set, write `docs/submission/deploy.md` with exact commands, add "Provide DEPLOY_HOST/DEPLOY_DOMAIN" under Needs from human (non-blocking), and continue.
4. README per §18: Mermaid diagrams for kb/family/centre; Cypher + algorithms table linking to files; eval headline (lpo) with CIs and honest framing; published figures as context only; exact attributions; all three tracks; AI disclosure (truthful: what Claude drafted, what the human decided, reviewed and changed); 3-command local setup; how to run keyless (replay) or with an `ANTHROPIC_API_KEY`, and the measured cost per family journey.
5. `docs/USER_GUIDE.md`: a 5-minute illustrated tour for anyone (parent, clinician, centre, judge) using screenshots from P4, with one worked example per role; linked from the README and `/help`.
6. `docs/submission/video_script.md`: 3-minute script in §18 order with exact clicks and plain-English lines for the human to voice.
7. `docs/submission/blog_outline.md`: 5 title options, outline, 3 diagrams to include, 4 key Cypher queries with one-line explanations — no finished prose (the human writes it).
8. `docs/submission/checklist.md`: §18 checklist with evidence links; what the human must still do (video, blog, form).
9. `reviewer` over the whole repo against AGENTS.md; fix blockers.

## Gate
- Checklist complete except human-only items; fresh-clone < 15 min; live URL verified (or deploy doc ready).
- Set `status: done` and list remaining human-only items under "Needs from human".
