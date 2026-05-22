#!/usr/bin/env python3
"""
schema-guard.py — Raven PreToolUse hook v1.0
Blocks dangerous SQL operations run via Bash:
  DROP TABLE / DATABASE / SCHEMA
  TRUNCATE
  DELETE FROM without WHERE clause

Returns JSON to Claude Code to block tool execution.
Exit 0 always — blocking is via JSON output, not exit code.
"""
import sys
import json
import re

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
            result = {
                "continue": False,
                "stopReason": (
                    f"⛔  RAVEN SCHEMA GUARD — {label} detected\n\n"
                    f"Command:\n  {command[:300]}\n\n"
                    f"This operation can cause irreversible data loss.\n\n"
                    f"To proceed intentionally:\n"
                    f"  • Run the SQL directly in your DB client with explicit confirmation\n"
                    f"  • Or add [GUARD:ALLOW-SCHEMA-DROP] to your next commit message\n\n"
                    f"Raven blocked this to protect your data."
                ),
            }
            print(json.dumps(result))
            sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
