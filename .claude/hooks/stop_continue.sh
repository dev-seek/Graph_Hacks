#!/usr/bin/env bash
# Stop hook (interactive runs only): keep working while the current phase has unticked tasks.
# At a phase boundary ("Current tasks" has no unticked item) Claude may stop, so the human can check direction,
# then type /clear and /build for the next phase. Loop-guarded.
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0
[ "${AUTOPILOT:-0}" = "1" ] && exit 0
S=.build/STATE.md; [ -f "$S" ] || exit 0
status=$(awk '/^status:/{print $2; exit}' "$S")
[ "$status" = "running" ] || exit 0
open=$(awk '/^## Current tasks/{f=1;next} /^## /{f=0} f && /- \[ \]/' "$S" | wc -l | tr -d ' ')
[ "$open" -gt 0 ] || exit 0
C=.build/logs/.autocontinue; mkdir -p .build/logs
n=$(cat "$C" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "$C"
[ "$n" -gt "${MAX_AUTOCONTINUE:-25}" ] && exit 0
echo "$open unticked task(s) remain in this phase (.build/STATE.md). Continue with the next one. If you genuinely need the human, first set status: needs-human and write the reason under 'Needs from human'." >&2
exit 2
