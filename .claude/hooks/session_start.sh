#!/usr/bin/env bash
# SessionStart: print build state so Claude starts oriented without reading the repo.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
S=.build/STATE.md
[ -f "$S" ] || { echo "No .build/STATE.md found."; exit 0; }
phase=$(awk '/^phase:/{print $2; exit}' "$S")
echo "=== BUILD STATE (.build/STATE.md) ==="
cat "$S"
echo "=== Current work order: $(ls .build/phases/${phase}-*.md 2>/dev/null) ==="
echo "Follow the operating loop in CLAUDE.md. AUTOPILOT=${AUTOPILOT:-0}"
exit 0
