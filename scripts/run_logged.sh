#!/usr/bin/env bash
# Usage: run_logged.sh <target> <command...>
# Runs the command, writes full output to .build/logs/<target>.log, prints a short summary.
set -u
target="$1"; shift
mkdir -p .build/logs
log=".build/logs/${target}.log"
"$@" >"$log" 2>&1
rc=$?
if [ $rc -eq 0 ]; then
  echo "[$target] OK  (log: $log)"
  tail -n 8 "$log"
else
  echo "[$target] FAILED rc=$rc (log: $log)"
  tail -n 25 "$log"
fi
exit $rc
