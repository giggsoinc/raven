#!/usr/bin/env python3
"""
schema-guard.py — Raven PreToolUse hook v1.1
Blocks dangerous SQL operations run via Bash:
  DROP TABLE / DATABASE / SCHEMA
  TRUNCATE
  DELETE FROM without WHERE clause

On every block:
  - Writes unconditional audit entry to .raven/audit/YYYY-MM-DD.log
  - Fires emit-violation.py async (non-blocking)

Returns JSON to Claude Code to block tool execution.
Exit 0 always — blocking is via JSON output, not exit code.
"""
import sys
import json
import re
import os
import subprocess
import pathlib
from datetime import datetime, timezone

# Patterns that signal destructive SQL — ordered most-specific first
DANGER_PATTERNS = [
    (r"\bDROP\s+TABLE\b",                             "DROP TABLE"),
    (r"\bDROP\s+DATABASE\b",                           "DROP DATABASE"),
    (r"\bDROP\s+SCHEMA\b",                             "DROP SCHEMA"),
    (r"\bTRUNCATE\s+(?:TABLE\s+)?\w",                 "TRUNCATE"),
    # DELETE FROM <table> with no WHERE — ends in semicolon, newline, EOF, or pipe
    (r"\bDELETE\s+FROM\s+\w[\w.]*\s*(?:;|$|\|)",     "DELETE without WHERE"),
]

# Commands that could contain or run SQL
DB_INDICATORS = [
    "psql", "mysql", "sqlite3", "snowsql", "sqlplus",
    "isql", "bq ", "dbcli", "pgcli", "mycli",
    "python3 -c", "python -c",   # inline scripts that might run SQL
]

SCRIPTS_DIR = pathlib.Path(__file__).parent


def _emit_guard_block(label: str, command: str) -> None:
    """Write unconditional audit entry and fire emit-violation — never raises."""
    # 1. Unconditional local audit (always writes, no local_fallback gate required)
    try:
        audit_dir = pathlib.Path(".raven/audit")
        audit_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = json.dumps({
            "ts":      datetime.now(timezone.utc).isoformat(),
            "event":   "guard_block",
            "guard":   "schema-guard",
            "rule":    label,
            "command": command[:300],
            "action":  "blocked",
            "dev":     os.environ.get("GIT_AUTHOR_EMAIL", os.environ.get("USER", "unknown")),
            "session": os.environ.get("CLAUDE_SESSION_ID", ""),
            "project": os.path.basename(os.getcwd()),
        })
        with open(audit_dir / f"{date_str}.log", "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass

    # 2. Fire emit-violation.py async — does not block the hook response
    try:
        emit = SCRIPTS_DIR / "emit-violation.py"
        if emit.exists():
            subprocess.Popen(
                [
                    "python3", str(emit),
                    "--type",     "schema_guard_block",
                    "--severity", "P1",
                    "--detail",   f"{label}: {command[:150]}",
                    "--blocked",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def main() -> None:
    """Read hook input, check for dangerous SQL, output block decision."""
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command: str = hook_input.get("tool_input", {}).get("command", "")
    if not command:
        sys.exit(0)

    # Only inspect commands that interact with databases or contain raw SQL
    cmd_lower = command.lower()
    has_db = any(ind in cmd_lower for ind in DB_INDICATORS)
    has_sql = any(
        kw in command.upper()
        for kw in ("DROP ", "DELETE ", "TRUNCATE ", "ALTER TABLE")
    )

    if not (has_db or has_sql):
        sys.exit(0)

    for pattern, label in DANGER_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE | re.MULTILINE):
            # Audit + notify BEFORE returning the block decision
            _emit_guard_block(label, command)

            result = {
                "continue": False,
                "stopReason": (
                    f"⛔  RAVEN SCHEMA GUARD — {label} detected\n\n"
                    f"Command:\n  {command[:300]}\n\n"
                    f"This operation can cause irreversible data loss.\n\n"
                    f"To proceed intentionally:\n"
                    f"  • Run the SQL directly in your DB client with explicit confirmation\n"
                    f"  • Or add [GUARD:ALLOW-SCHEMA-DROP] to your next commit message\n\n"
                    f"Block recorded in .raven/audit/. Raven blocked this to protect your data."
                ),
            }
            print(json.dumps(result))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
