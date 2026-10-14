#!/usr/bin/env bash
# Autopilot: runs one fresh Claude Code session per phase (small context, low cost), until done or a human is needed.
# Usage: scripts/autopilot.sh            (env overrides: MAX_RUNS, PERMISSION_MODE, BUDGET_SCALE, ADVISOR_MODEL=fable|opus)
# Each phase: Sonnet main model + Opus advisor (Claude consults the advisor at decision points).
set -uo pipefail
cd "$(dirname "$0")/.."
export AUTOPILOT=1
S=.build/STATE.md
MAX_RUNS=${MAX_RUNS:-24}
PERMISSION_MODE=${PERMISSION_MODE:-auto}     # auto (classifier reviews actions) | acceptEdits (+ allowlist in .claude/settings.json)
BUDGET_SCALE=${BUDGET_SCALE:-1}
mkdir -p .build/logs

field(){ awk -v k="$1:" '$1==k{print $2; exit}' "$2"; }

# Git preflight: history is the project's record, so make sure commits can land and be pushed.
git rev-parse --git-dir >/dev/null 2>&1 || { echo "■ Not a git repo. Clone your GitHub repo and unzip the kit into it first."; exit 1; }
git config user.name >/dev/null && git config user.email >/dev/null || { echo "■ Set git identity first: git config user.name \"You\"; git config user.email \"you@example.com\""; exit 1; }
if git remote get-url origin >/dev/null 2>&1; then HAS_REMOTE=1; else HAS_REMOTE=0; echo "⚠ No 'origin' remote: commits stay local until you add one (git remote add origin <url>)."; fi
push(){ [ "$HAS_REMOTE" = 1 ] || return 0
  git push -q origin HEAD --follow-tags 2>/dev/null && echo "  ↑ pushed $(git rev-parse --short HEAD) ($(git rev-list --count HEAD) commits)" || echo "  ⚠ push failed — will retry after the next run"; }
push

# A new autopilot start means the human has acted: let Claude re-check a needs-human/blocked state once.
st=$(field status "$S")
if [ "$st" = "needs-human" ] || [ "$st" = "blocked" ]; then
  sed -i.bak 's/^status: .*/status: running/' "$S" && rm -f "$S.bak"; echo "↻ Resuming after human action (was: $st)"
fi

for i in $(seq 1 "$MAX_RUNS"); do
  status=$(field status "$S"); phase=$(field phase "$S")
  case "$status" in
    done) echo "✔ All phases done."; sed -n '/## Needs from human/,/## Decisions/p' "$S"; exit 0;;
    needs-human|blocked) echo "■ Stopped: $status (phase $phase)"; sed -n '/## Needs from human/,/## Decisions/p' "$S"; exit 1;;
  esac
  if [ "$phase" = "${last_phase:-}" ]; then repeats=$((repeats+1)); else repeats=1; last_phase=$phase; fi
  if [ "$repeats" -gt "${MAX_RUNS_PER_PHASE:-4}" ]; then echo "■ Phase $phase did not finish in ${MAX_RUNS_PER_PHASE:-4} runs — check $S notes and .build/logs/"; exit 1; fi
  wo=$(ls .build/phases/${phase}-*.md 2>/dev/null | head -1)
  [ -z "$wo" ] && { echo "No work order for phase $phase"; exit 1; }
  model=$(field model "$wo"); advisor=${ADVISOR_MODEL:-$(field advisor "$wo")}; effort=$(field effort "$wo"); budget=$(field max_budget_usd "$wo")
  budget=$(awk -v b="$budget" -v s="$BUDGET_SCALE" 'BEGIN{printf "%.2f", b*s}')
  log=".build/logs/run-$(date +%Y%m%d-%H%M%S)-$phase.json"
  echo "▶ Run $i: $phase ($(basename "$wo")) model=$model advisor=$advisor effort=$effort budget=\$$budget"
  claude -p "/build" \
    --model "$model" --advisor "$advisor" --effort "$effort" \
    --permission-mode "$PERMISSION_MODE" --permission-prompts none \
    --max-budget-usd "$budget" \
    --output-format json > "$log" 2> "${log%.json}.err"
  rc=$?
  jq -r '"  cost≈$\(.total_cost_usd // "?")  turns=\(.num_turns // "?")"' "$log" 2>/dev/null || true
  jq -r '.result // empty' "$log" 2>/dev/null | tail -n 8 | sed 's/^/  │ /'
  push   # backstop: whatever Claude committed this run reaches GitHub even if its own push failed
  [ -n "$(git status --porcelain)" ] && echo "  ⚠ uncommitted changes left by this run (the next session commits them as part of its first task)"
  new_phase=$(field phase "$S"); new_status=$(field status "$S")
  if [ "$rc" -ne 0 ] && [ "$new_phase" = "$phase" ] && [ "$new_status" = "running" ]; then
    echo "  (run ended early: rc=$rc — resuming the same phase in a fresh session)"
  fi
done
echo "Reached MAX_RUNS=$MAX_RUNS. Check $S."; exit 1
