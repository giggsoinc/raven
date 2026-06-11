#!/usr/bin/env python3
"""
Raven — Skill Invocation Marker

Appends one JSON line to .raven/state/skill-invocations.jsonl whenever an
enforced skill is invoked. Each gated skill's SKILL.md instructs the model to
run this as its FIRST step:

    python3 .claude/scripts/raven-mark-skill.py andie-jr

The SCRIPT stamps the timestamp — the model cannot forge freshness. The
marker is what raven-skill-gate.py (PreToolUse) checks before allowing edits.

Honest contract: this proves the skill RAN, not that its output was used
well. That residual gap is inherent to LLM systems.

Local-only. No telemetry. Zero model tokens (runs outside the model).
"""

import json
import os
import sys
import time
from pathlib import Path

STATE_DIR = Path(".raven") / "state"
MARKER_FILE = STATE_DIR / "skill-invocations.jsonl"
MAX_LINES = 200  # rotate: keep the file tiny so the gate stays <100ms


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("usage: raven-mark-skill.py <skill-name>", file=sys.stderr)
        return 1
    skill = sys.argv[1].strip()

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            "ts": int(time.time()),
            "skill": skill,
            "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
        })
        existing = []
        if MARKER_FILE.exists():
            existing = MARKER_FILE.read_text().splitlines()[-(MAX_LINES - 1):]
        MARKER_FILE.write_text("\n".join(existing + [line]) + "\n")
        print(f"raven: marked skill invocation — {skill}")
        return 0
    except Exception as exc:  # fail-soft: a marker failure must never break a skill
        print(f"raven: marker write failed ({exc}) — continuing", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
