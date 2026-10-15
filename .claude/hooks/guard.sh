#!/usr/bin/env bash
# PreToolUse guard. Exit 2 blocks the call; stderr is shown to Claude.
input="$(cat)"
tool=$(jq -r '.tool_name // empty' <<<"$input")
path=$(jq -r '.tool_input.file_path // empty' <<<"$input")
cmd=$(jq -r '.tool_input.command // empty' <<<"$input")
block(){ echo "Blocked by guard: $1 (AGENTS.md non-negotiables). Record why you needed it in .build/STATE.md instead of working around it." >&2; exit 2; }
reviewed(){ [ -f "$1" ] && head -n 1 "$1" | grep -Eq "^# STATUS: REVIEWED by"; }
case "$tool" in
  Read)
    case "$path" in */data/raw/*) block "reading raw data files floods context; inspect with head -c or a small script";; esac ;;
  Edit|Write|MultiEdit|NotebookEdit)
    case "$path" in
      */data/raw/*|*/eval/splits/test_ids.txt|*/.env) block "protected file (raw data, frozen test split or secrets)";;
    esac
    reviewed "$path" && block "this file was REVIEWED and approved by the human; propose changes in STATE.md instead" ;;
  Bash)
    for f in "${CLAUDE_PROJECT_DIR:-.}"/review/*; do
      if reviewed "$f" && grep -Eq "(>|>>|tee|sed -i|mv|cp|rm|truncate|perl -pi)[^|;&]*$(basename "$f")" <<<"$cmd"; then block "shell write to REVIEWED file $f"; fi
    done
    if grep -Eq '(>|>>|tee|sed -i|rm)[^|;&]*eval/splits/test_ids\.txt' <<<"$cmd"; then block "shell write to the frozen test split"; fi
    if grep -Eq '(^|[ ;&|])cat[^|;&]*\.env($|[ ;&|])' <<<"$cmd"; then block "printing .env"; fi ;;
esac
exit 0
