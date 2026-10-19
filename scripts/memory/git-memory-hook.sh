#!/bin/bash
# Git-side caller for memory-card-hook.py.
# Installed as post-commit (checkin), pre-push (push), post-merge (pull).
# Always exits 0 so it cannot block git.
set +e
EVENT="${1:-checkin}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
python3 "$ROOT/scripts/memory/memory-card-hook.py" --event "$EVENT"
exit 0
