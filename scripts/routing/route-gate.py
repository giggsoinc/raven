#!/usr/bin/env python3
"""PreToolUse: deny work until model-router has stamped this turn.

Allows the router command itself. Other Write/Edit/Bash need a fresh stamp.
Codex/Cursor/Grok have no PreToolUse — AGENTS.md + empty Logs is the proof.
"""
from __future__ import annotations

import json
import os
import sys
import time

ROOT = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
STAMP = os.path.join(ROOT, ".raven", ".route-stamp")
TTL = 600
ALLOW_SUBSTR = ("model-router.py", "cost_calc.py --end", "cost_calc.py --start")


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = payload.get("tool_name") or ""
    cmd = ""
    if tool == "Bash":
        cmd = str((payload.get("tool_input") or {}).get("command") or "")
        if any(s in cmd for s in ALLOW_SUBSTR):
            sys.exit(0)
    if tool not in ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"):
        sys.exit(0)
    try:
        age = time.time() - os.path.getmtime(STAMP)
        if age <= TTL and os.path.isfile(STAMP):
            sys.exit(0)
    except OSError:
        pass
    print(json.dumps({
        "systemMessage": (
            "🪶 Router not fired this turn. Run "
            "python3 scripts/routing/model-router.py --prompt \"<user message>\" "
            "before any other tool. git/status is not an exemption. "
            "This gate checks the router stamp only. It does not force-load Andie."
        ),
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "No fresh .raven/.route-stamp — router must run first.",
        },
    }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
