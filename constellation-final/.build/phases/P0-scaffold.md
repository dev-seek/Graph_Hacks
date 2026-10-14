---
phase: P0
title: Scaffold, tooling, CI
model: sonnet
advisor: opus
effort: medium
max_budget_usd: 8
needs_reviewed_files: []
---
## Goal
A repo where `make check` is green locally and in CI, FalkorDB runs in Docker with a pinned tag, and every later phase has its place, commands and guard rails.

## Read (only when needed)
AGENTS.md (already loaded) · spec §17 (`14-ops-security.md`) · §6.1–6.2 tokens and fonts (`03-design-copy.md`) · §10.3 config shape (`08-llm.md`).

## Tasks
1. `git init` if needed; extend the existing `.gitignore` if new tools need it (keep its secrets and data/raw entries).
2. Repo map from AGENTS.md: create packages with `__init__.py`, `backend/app/ports/` (five Protocols from §17.1, no implementations yet), `config/llm.yaml` exactly as §10.3, `.env.example` listing every env var name (no values).
3. Python 3.12 project with uv: FastAPI, pydantic v2, structlog, httpx, falkordb (pin), langgraph 1.2.15, langgraph-checkpoint 4.3.0, langchain-falkordb 0.2.0, anthropic (official SDK, pinned), pytest, hypothesis, ruff, pyright. Pin everything; commit the lockfile.
4. `docker-compose.yml`: FalkorDB with a **pinned image tag** (look up the current stable tag; log it in docs/VERIFIED.md), internal network, Browser on 3000 for local dev only; query timeout config (verify the mechanism for that image; log it); api and web services stubbed.
5. Makefile with every command in AGENTS.md; it loads `.env` itself (`-include .env` + `export`) so app and scripts see `ANTHROPIC_API_KEY` without it being in Claude's shell. Add `make llm-key-check` (prints `set`/`unset`, never the key). Each target prints a ≤ 30-line summary and writes full output to `.build/logs/<target>.log`. Unimplemented targets print "not yet implemented (P<n>)" and exit 0 — except `check`.
6. `make review-check`: `scripts/review_check.py` validates `review/` files (no FILL_ME, required rule IDs, 40 cases, 3 stories, 2 letters, schema, own safety corpus passes, first line `# STATUS: REVIEWED by …`). Exit 1 with a one-line reason per file.
7. **Draft the four `review/` files** following the instructions inside each template: realistic, varied, plainly worded; safety rules cite a real public guidance URL per rule (verify each with WebFetch); crisis/emergency numbers verified from official pages. Set line 1 to `# STATUS: DRAFT — drafted by Claude, awaiting human review`. Use the advisor before finalising the safety rules. Log in `docs/AI_USAGE.md`: drafted by Claude, reviewer: pending.
8. FastAPI app with `/api/health` and `/api/version` (versions from KbInfo when present, else "no kb").
9. Next.js (TypeScript strict, Tailwind) skeleton: tokens from §6.1 as CSS variables, Atkinson Hyperlegible + Fraunces via next/font, one placeholder page using the tokens. pnpm lockfile.
10. pre-commit: ruff, prettier, gitleaks. GitHub Actions CI: lint, typecheck, unit tests, integration tests with a FalkorDB service container on the same pinned tag.
11. Docs skeleton: LICENSE (MIT), docs/DATA_LICENSES.md (sections per source, text from §5), docs/AI_USAGE.md (table: part | drafted by | reviewed/edited by | tool), docs/VERIFIED.md, docs/adr/0001-record-architecture-decisions.md, README skeleton following §18.
12. `chmod +x .claude/hooks/*.sh scripts/*.sh`.

## Gate
- `make check` green locally; CI green on the pushed branch (if no remote yet, record "CI config validated with act/yamllint" and move on).
- `make up` → `/api/health` 200; FalkorDB responds to `GRAPH.LIST`.
- The four `review/` drafts exist, pass schema checks, and `make review-check` reports only "not yet REVIEWED".
- FalkorDB tag + timeout config logged in docs/VERIFIED.md.

## Handoff note
Pinned FalkorDB tag; any tooling surprise; anything the next phase must know.
