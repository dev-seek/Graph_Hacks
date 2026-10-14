#!/usr/bin/env bash
# PostToolUse formatter. Never fails the tool call; formatting problems surface in `make check`.
path="$(jq -r '.tool_input.file_path // empty')"
[ -z "$path" ] || [ ! -f "$path" ] && exit 0
case "$path" in
  *.py)
    uv run ruff format "$path" >/dev/null 2>&1 || true
    uv run ruff check --fix "$path" >/dev/null 2>&1 || true
    ;;
  *.ts|*.tsx|*.js|*.jsx|*.json|*.css|*.md)
    (cd web 2>/dev/null && pnpm exec prettier --write "$path" >/dev/null 2>&1) || true
    ;;
esac
exit 0
