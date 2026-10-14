#!/usr/bin/env bash
# UserPromptSubmit: a human prompt resets the auto-continue counter.
cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null && rm -f .build/logs/.autocontinue
exit 0
