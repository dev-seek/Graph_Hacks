@AGENTS.md

# Operating loop (Claude Code) — follow exactly

You build Constellation autonomously, phase by phase, from `.build/`. The human is mostly away. Do not ask for approval between tasks or phases; stop only for the reasons in step 7.

1. **Orient (cheap).** The session-start hook has printed `.build/STATE.md`. If it hasn't, read it. Never read whole folders. Ignore `START_HERE.md` (it's for the human). Run `git status --short`: if a previous session left uncommitted work, check it with `make check` and commit it properly (or finish it as part of the current task) before starting anything new.
2. **Status.** `done` → print a 5-line summary and stop. `needs-human` or `blocked` → re-check the listed condition (e.g. `make review-check`); if it is now resolved, tick it, set `status: running` and continue; otherwise print the "Needs from human" section and stop. `running` → continue.
3. **Load only the current work order:** `.build/phases/<phase>-*.md`. Read the spec files it lists, only when a task needs them (map: `docs/spec/00-index.md`). For Cypher, also `docs/FALKORDB_CHEATSHEET.md`.
4. **Plan once per phase** (no approval needed): record `phase_start: <git sha>` under "Notes for next session", then write the phase's task list into STATE.md "Current tasks" if it is empty, refining the work order's list into ≤ 15 concrete tasks. Then work them top to bottom.
5. **Per task:** tests first where the work order says so → implement → `make check` (and `make test-int` if FalkorDB is touched) → tick the task in STATE.md → commit (with the STATE.md tick in the same commit) → `git push origin HEAD` (see "Git history" below). Keep "Notes for next session" ≤ 10 lines, updated when something non-obvious happens.
6. **Phase gate:** run the gate commands in the work order; run the `reviewer` subagent on the phase diff and fix blockers; write `docs/explain/<phase>.md` (plain English) and append to `docs/AI_USAGE.md`; mark the phase done in the phase table with gate evidence; set `phase:` to the next phase and clear "Current tasks"; commit `chore(build): close <phase> gate`, then `git tag -a <phase>-done -m "<phase>: <one-line gate evidence>"` and `git push origin HEAD --follow-tags`. Then:
   - if `AUTOPILOT=1` is set in the environment (check once with `echo $AUTOPILOT`), **end your turn** — the runner starts a fresh session for the next phase;
   - otherwise continue straight into the next phase.
7. **Stop only when:** a `review/` file is not REVIEWED or invalid when needed (`status: needs-human`, say exactly which file and what's wrong); a locked decision is contradicted by evidence (`blocked`, cite evidence); a credential/budget/tooling problem you can't solve; three failed attempts on one problem (`blocked`). Write the reason under "Needs from human" first.

## Git history (it is the project's record — judges read it)
- **Small, frequent commits:** one logical change per commit, every task, never a big "wip" dump. Never commit with `make check` red, except a test-first commit of failing tests, marked `test(<scope>): failing tests for …`.
- **Message format** (Conventional Commits):
  ```
  <type>(<scope>): <imperative summary, ≤ 72 chars>

  <why this change, 1–3 lines; what was verified (tests/gate numbers)>

  Refs: <phase> task <n>
  ```
  types: feat, fix, test, refactor, perf, docs, data, chore, ci. Scope = the area (engine, safety, kb, graph, llm, api, web, centre, eval, build).
- **Push after every commit** with `git push origin HEAD`. If there is no remote or the push fails, don't stop: commit locally, add "Push failing: <error, one line>" under "Needs from human" (non-blocking) once, and keep working; the runner retries pushes.
- Keep Claude Code's default `Co-Authored-By` trailer on commits (honest AI disclosure, Rule 11). Never rewrite history: no `--amend` on pushed commits, no rebase, no force push.
- Commits made by the human (e.g. review approvals) are theirs; never re-commit or squash them.

## Advisor (Sonnet does the work, Opus advises)
Every session runs with an advisor model attached (`--advisor` / `advisorModel`). Calling it forwards the whole conversation; it returns a short plan or correction. It costs tokens at the advisor's rate, so use it at decision points only:
- **Before substantive work** on each phase and on any task longer than a few steps: orient first (read the work order, grep), then call the advisor before writing code or committing to an approach.
- **When stuck:** the same error twice, results that don't fit, or when considering a change of approach.
- **Before declaring a phase gate passed:** first make the work durable (tests green, committed, STATE.md updated), then call the advisor.
- Give its advice serious weight; if a step it suggests fails empirically, or files contradict it, adapt and note why in STATE.md.
- Don't call it for routine, reactive steps whose next action is obvious from the last tool output.

## Context hygiene (this repo is large; keep your context small)
- Run commands through `make` targets — they print short summaries and write full logs to `.build/logs/`. Read logs with Grep or `tail`, never whole.
- Never open `data/raw/**` (blocked); inspect structure with `head -c 2000` or a 20-line Python snippet.
- Use subagents for anything that reads a lot or produces a lot: `Explore` for searching, `test-engineer` for writing tests, `reviewer` at gates, `copy-a11y-reviewer` for UI text. Ask them for short reports.
- Read files with offsets/limits when they're long. Don't re-read files you just wrote.
- Don't paste large outputs into STATE.md or chat; link the log file instead.

## Subagents (`.claude/agents/`)
| Agent | When | Notes |
|---|---|---|
| `reviewer` | every phase gate | read-only; checks AGENTS.md rules + the phase's spec |
| `test-engineer` | before core logic (engine, safety, kb, gates, planner, API contracts) | writes failing tests first |
| `copy-a11y-reviewer` | P4 and any UI text change | read-only; returns exact replacement text |

## Hooks (`.claude/settings.json`)
- SessionStart: prints STATE.md (status, phase, current tasks, notes).
- PreToolUse: blocks edits to REVIEWED files in `review/`, raw data, the frozen test split, `.env`; blocks reading `data/raw/**`. Never work around a block (no shell redirection either); record why in STATE.md.
- PostToolUse: auto-formats edited files.
- Stop (interactive runs only): if `status: running`, you are sent back to continue the next task.
