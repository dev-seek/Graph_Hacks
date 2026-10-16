#!/usr/bin/env bash
# make check: lint + typecheck + unit tests for backend, and web when present. Full output in .build/logs/check.log
set -u
export PATH="/opt/homebrew/opt/node@22/bin:$PATH"
mkdir -p .build/logs
log=".build/logs/check.log"
: >"$log"
fail=0
step() {
  name="$1"; shift
  echo "== $name ==" >>"$log"
  if "$@" >>"$log" 2>&1; then echo "  ok    $name"; else echo "  FAIL  $name"; fail=1; fi
}
step "ruff lint"      uv run ruff check .
step "ruff format"    uv run ruff format --check .
step "pyright"        uv run pyright
step "pytest (unit)"  uv run pytest -q
if [ -f web/package.json ]; then
  step "web lint"       pnpm --dir web lint
  step "web typecheck"  pnpm --dir web typecheck
  step "web api types"  pnpm --dir web check:types-sync
  step "web unit tests" pnpm --dir web test
fi
if [ $fail -ne 0 ]; then
  echo "check FAILED. Last log lines:"; tail -n 15 "$log"; exit 1
fi
echo "check OK (log: $log)"
