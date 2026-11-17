#!/usr/bin/env python3
"""Run one hook script. A missing file must not block PreToolUse.

Claude Code treats a missing PreToolUse command (exit 127, or exit 2) as a
deny, so every later tool call stops. This wrapper prints the missing path
and exits 0. When the file exists, the script's own exit code is kept, so
push-gate can still deny.

One exception: the Educate gate (push-gate.py) fails closed. If it is missing
or crashes, an exit 0 would silently turn the gate off. For that script only,
anything that can write (Write, Edit, MultiEdit, NotebookEdit, Bash) is denied
and an audit row is written. Read-only tools still pass, and so does everything
when the user turned Educate off, so a broken gate never bricks a session.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FAIL_CLOSED_SCRIPTS = {"push-gate.py"}
WRITE_CAPABLE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash"}
GATE_TIMEOUT_SEC = 30


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


def _project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _audit(script: str, event: str = "missing-script", **extra) -> None:
    """A missing or crashed script must leave a row. Stderr on exit 0 is easy to miss."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = _project_root() / ".raven" / "audit" / f"{day}.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {"ts": int(time.time()), "source": "hook-run", "event": event, "script": script, **extra}
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
    except OSError as exc:
        print(f"hook-run audit failed: {exc}", file=sys.stderr)


def _educate_off() -> bool:
    try:
        data = json.loads((_project_root() / ".raven" / "educate.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    mode = str(data.get("mode") if isinstance(data, dict) else data).strip().lower()
    return mode in ("off", "auto", "lucky")


def _gate_failed(script: str, why: str, stdin_bytes: bytes) -> int:
    """The gate is missing or broken: deny write-capable calls, pass the rest."""
    tool = None
    try:
        tool = json.loads(stdin_bytes or b"{}").get("tool_name") or ""
    except (ValueError, AttributeError):
        tool = ""  # unreadable payload: treat as write-capable
    _audit(script, "gate-fail-closed", detail=why, tool=tool or "unknown")
    if _educate_off():
        return 0
    if tool and tool not in WRITE_CAPABLE_TOOLS:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Educate gate unavailable — failing closed",
        },
        "systemMessage": (
            f"🪶 Educate gate {why}. Write-capable tools are DENIED until it is "
            "fixed. See .raven/audit/. Turn off: educate off or Lucky."
        ),
    }))
    return 0


def _run_fail_closed(script: str, argv: list) -> int:
    stdin_bytes = sys.stdin.buffer.read()
    if not os.path.isfile(script):
        print(f"hook script missing: {script}", file=sys.stderr)
        return _gate_failed(script, "is missing", stdin_bytes)
    try:
        ran = subprocess.run(
            [sys.executable, script, *argv],
            input=stdin_bytes, capture_output=True, timeout=GATE_TIMEOUT_SEC,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _gate_failed(script, f"failed to run ({type(exc).__name__})", stdin_bytes)
    if ran.returncode not in (0, 2):
        return _gate_failed(script, f"crashed (exit {ran.returncode})", stdin_bytes)
    sys.stdout.buffer.write(ran.stdout)
    sys.stderr.buffer.write(ran.stderr)
    return ran.returncode


def main() -> int:
    if len(sys.argv) < 2:
        print("hook-run: no script path", file=sys.stderr)
        return 0
    script = _resolve(sys.argv[1])
    if os.path.basename(script) in FAIL_CLOSED_SCRIPTS:
        return _run_fail_closed(script, sys.argv[2:])
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
