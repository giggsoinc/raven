#!/usr/bin/env python3
"""
Raven — Guard Override Audit v1.0
Called by the pre-commit hook when a [GUARD:ALLOW-*] flag is present in the commit message.

Writes an unconditional audit entry and fires emit-violation (after-the-fact notification).
This ensures overrides are never silent — they always produce a record and email.

Usage (from pre-commit hook):
  python3 .claude/scripts/guard-override-audit.py --message "$COMMIT_MSG"

Or pipe the commit message:
  cat .git/COMMIT_EDITMSG | python3 .claude/scripts/guard-override-audit.py

Exit 0 always — audit only, never blocks.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

SCRIPTS_DIR = pathlib.Path(__file__).parent

# All recognised GUARD:ALLOW flags
OVERRIDE_FLAGS = re.compile(
    r"\[GUARD:ALLOW-(SCHEMA-DROP|DELETE|RESET|CLEAN|CVE:[^\]]+|SECRET:[^\]]+|[A-Z0-9_-]+)\]",
    re.IGNORECASE,
)


def write_audit(entries: list[dict]) -> None:
    """Write override events to .raven/audit/YYYY-MM-DD.log — always, unconditionally."""
    try:
        audit_dir = pathlib.Path(".raven/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(audit_dir / f"{date_str}.log", "a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def emit_violation(flag: str, commit_msg_snippet: str) -> None:
    """Fire emit-violation.py async for each override flag."""
    try:
        emit = SCRIPTS_DIR / "emit-violation.py"
        if not emit.exists():
            return
        subprocess.Popen(
            [
                "python3", str(emit),
                "--type",     "guard_override",
                "--severity", "P2",
                "--detail",   f"[GUARD:ALLOW-{flag}] used in commit: {commit_msg_snippet[:100]}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", default="", help="Commit message text")
    args = parser.parse_args()

    # Accept message from CLI arg or stdin
    if args.message:
        commit_msg = args.message
    elif not sys.stdin.isatty():
        commit_msg = sys.stdin.read()
    else:
        # Try reading from git commit message file directly
        try:
            commit_msg = pathlib.Path(".git/COMMIT_EDITMSG").read_text()
        except Exception:
            commit_msg = ""

    if not commit_msg.strip():
        sys.exit(0)

    matches = OVERRIDE_FLAGS.findall(commit_msg)
    if not matches:
        sys.exit(0)

    dev = (
        os.environ.get("GIT_AUTHOR_EMAIL")
        or os.environ.get("GIT_COMMITTER_EMAIL")
        or os.environ.get("USER", "unknown")
    )
    session = os.environ.get("CLAUDE_SESSION_ID", "")
    project = os.path.basename(os.getcwd())
    snippet = commit_msg.strip()[:200]

    entries = []
    for flag in matches:
        entry = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "event":   "guard_override",
            "flag":    f"GUARD:ALLOW-{flag}",
            "action":  "override_used",
            "dev":     dev,
            "session": session,
            "project": project,
            "commit":  snippet,
        }
        entries.append(entry)
        emit_violation(flag, snippet)

    write_audit(entries)

    print(
        f"[RAVEN] {len(entries)} guard override(s) recorded in .raven/audit/: "
        + ", ".join(f"[GUARD:ALLOW-{f}]" for f in matches),
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
