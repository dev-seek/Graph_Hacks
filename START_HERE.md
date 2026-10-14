# START HERE (for the human — Claude ignores this file)

Everything Claude needs is in this folder: rules (`AGENTS.md`, `CLAUDE.md`), the locked spec (`docs/spec/`), progress (`.build/STATE.md`), seven work orders (`.build/phases/`) and the four inputs it drafts for your review (`review/`). Claude reads only what the current phase needs, so its context stays small.

## Once, before kickoff
Install Docker, Python 3.12 + `uv`, Node 22 + `pnpm`, `git`, `jq`, and Claude Code (`claude update`). Sign in to Claude Code. The build runs **Sonnet as the main model with Opus as its advisor** (Opus is consulted only at decision points). Don't set `DISABLE_TELEMETRY` — it switches the advisor off.

## At kickoff
1. Create a **public** GitHub repo and clone it. Set your git name and email (`git config user.name`, `git config user.email`). Make sure you can push without a prompt (`gh auth login`, or SSH).
2. From inside the repo folder: `unzip -o ~/Downloads/constellation-kit-final.zip -d .` (files must land in the repo root: `ls -a` shows `AGENTS.md`, `CLAUDE.md`, `.claude`, `.build`). Then `git add -A && git commit -m "chore: add build kit (spec, rules, work orders)" && git push`.
3. Start the build in one of two ways (both resume from `.build/STATE.md`; you can switch any time):

**A. Watch and steer (recommended).** In the repo root run `claude --permission-mode auto` (if `auto` isn't offered on your plan: `claude --permission-mode acceptEdits` and answer prompts with "Yes, don't ask again"), then type `/build`. You see every step. To correct it, press **Esc** and type what you want ("use X instead", "skip this, do Y first"); it applies the correction, notes it, and continues. After each phase it stops with a short report: read it, then type `/clear` and `/build` for the next phase (fresh context = lower cost).

**B. Autopilot (when you step away).** `bash scripts/autopilot.sh` — one fresh session per phase, live one-line feed of what Claude does, pushes after every run. **Ctrl-C** stops everything; run it again to resume. `VERBOSE=0` shows only Claude's messages.

## Your review (~45–60 min, any time before phase P2 starts)
In phase P0 Claude drafts four files in `review/`. Open each, read it, fix anything you disagree with, then change line 1 to `# STATUS: REVIEWED by <your name> on <date>`. After that Claude can't change them. Check with `make review-check`, then commit them yourself, e.g. `git commit -am "review: approve safety rules and negatives after edits"` and push. Those commits carry your name and show your part honestly.
- `safety_rules.yaml` — red-flag rules checked before anything else (most important: each message calm and clear, each source link real).
- `negatives.yaml` — 40 made-up "nothing serious" children used to test false alarms.
- `demo_stories.md` — the three example families judges click (Kabir, Arjun, Maya).
- `doctor_letters.md` — two made-up doctor letters for the demo.

## Git history
Claude commits after every task with a clear message (`feat(engine): …`, plus why and which task), pushes right away, and tags each finished phase (`P0-done` … `P6-done`). The runner also pushes after every session as a backstop. Watch progress on GitHub any time. Don't rewrite or squash history.

## When it stops
It prints what it needs (from `.build/STATE.md` → "Needs from human"). Fix it and run the same command again.

## If you are running out of time
Claude's files contain no deadlines on purpose, so it never rushes or skips quality. You control time: add `cut: 1,2` under "Notes for next session" in `.build/STATE.md` (cut list in `AGENTS.md`: 1 two knowledge versions, 2 what-if copy, 3 ask-the-centre, 4 PDF upload, 5 vector search, 6 MCP down to 2 tools).

## Claude in the product (optional key)
Haiku 5.5 for quick steps, Haiku + Sonnet advisor for doctor letters, Sonnet 5.5 for referral drafts, Batch API at half price for offline labelling; the build keeps the cheapest setup that passes per task. Put `ANTHROPIC_API_KEY` in `.env` only (don't export it in your shell, or Claude Code may bill it instead of your subscription) and set a spend limit in the Claude Console. Without a key everything still works with fallbacks and demo replay.

## After it says done
Read `docs/USER_GUIDE.md` and click through the tour yourself. Record and voice the video from `docs/submission/video_script.md`; write the blog from `docs/submission/blog_outline.md` in your own words; submit with all three tracks named.

## Being honest about AI use (hackathon Rules 11–13)
AI assistants are allowed; their use must be disclosed, and you must understand the code. `docs/AI_USAGE.md` (kept by Claude, checked by you) says truthfully what Claude drafted and what you decided, reviewed and changed. Your real contribution is large — the problem choice, the research, every product and technical decision in `docs/DECISIONS.md`, reviewing the inputs, and presenting. Read `docs/explain/` before judging so you can answer any question about the code.

## Cost knobs
Per-phase caps in each work order (total ≈ $103; caps, not estimates); `BUDGET_SCALE=0.5` halves them; `MAX_RUNS_PER_PHASE` (default 4) stops a phase that keeps failing; `ADVISOR_MODEL=fable` if you have Fable access.
