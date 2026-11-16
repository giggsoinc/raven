#!/usr/bin/env python3
"""Run one hook script. A missing file must not block PreToolUse.

Claude Code treats a missing PreToolUse command (exit 127, or exit 2) as a
deny, so every later tool call stops. This wrapper prints the missing path
and exits 0. When the file exists, the script's own exit code is kept, so
push-gate can still deny.
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _resolve(rel: str) -> str:
    if os.path.isabs(rel):
        return rel
    roots = [
        os.environ.get("CLAUDE_PLUGIN_ROOT") or "",
        os.environ.get("CLAUDE_PROJECT_DIR") or "",
        os.getcwd(),
    ]
    for root in roots:
        if not root:
            continue
        candidate = os.path.join(root, rel)
        if os.path.isfile(candidate):
            return candidate
    root = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.join(root, rel)


def _audit(script: str) -> None:
    """A missing script must leave a row. Stderr on exit 0 is easy to miss."""
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = root / ".raven" / "audit" / f"{day}.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": int(time.time()), "source": "hook-run", "event": "missing-script", "script": script}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    except OSError as exc:
        print(f"hook-run audit failed: {exc}", file=sys.stderr)


def main() -> int:
    if len(sys.argv) < 2:
        print("hook-run: no script path", file=sys.stderr)
        return 0
    script = _resolve(sys.argv[1])
    if not os.path.isfile(script):
        print(f"hook script missing: {script}", file=sys.stderr)
        _audit(script)
        return 0
    os.execv(sys.executable, [sys.executable, script, *sys.argv[2:]])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except OSError as exc:
        print(f"hook-run failed: {exc}", file=sys.stderr)
        sys.exit(0)
