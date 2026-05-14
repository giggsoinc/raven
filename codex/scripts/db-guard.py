#!/usr/bin/env python3
"""
db-guard.py — PostEdit hook: detect inline SQL in non-SQL source files.
Reads Claude's tool use input from stdin (JSON), checks the file written.
Emits additionalContext JSON if a violation is found.
"""

import json
import re
import sys
from pathlib import Path

SQL_EXTENSIONS = {".sql"}
APP_EXTENSIONS = {".py", ".java", ".go", ".cs", ".ts", ".js", ".rb", ".php", ".kt", ".swift"}

SQL_PATTERNS = [
    r"\bSELECT\s+.{1,200}\s+FROM\b",
    r"\bINSERT\s+INTO\b",
    r"\bUPDATE\s+\w+\s+SET\b",
    r"\bDELETE\s+FROM\b",
    r"\bCREATE\s+TABLE\b",
    r"\bALTER\s+TABLE\b",
    r"\bDROP\s+TABLE\b",
    r"cursor\.execute\s*\(",
    r"db\.execute\s*\(",
    r"\.query\s*\(\s*[\"']SELECT",
    r"db\.raw\s*\(",
    r"knex\.raw\s*\(",
    r"text\s*=\s*[\"'`]SELECT",
]

LOADER_PATTERNS = {
    ".py":   'Path("queries/your_query.sql").read_text()',
    ".go":   'os.ReadFile("queries/your_query.sql")',
    ".java": 'Files.readString(Path.of("queries/your_query.sql"))',
    ".ts":   'fs.readFileSync("queries/your_query.sql", "utf8")',
    ".js":   'fs.readFileSync("queries/your_query.sql", "utf8")',
    ".cs":   'File.ReadAllText("queries/your_query.sql")',
    ".rb":   'File.read("queries/your_query.sql")',
    ".php":  'file_get_contents("queries/your_query.sql")',
}


def check_file(file_path: str, content: str) -> list[str]:
    """Return list of violation messages for a given file and content."""
    ext = Path(file_path).suffix.lower()
    if ext not in APP_EXTENSIONS:
        return []

    violations = []
    lines = content.splitlines()
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "*", "/*")):
            continue
        for pattern in SQL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append(f"  Line {i}: {stripped[:80]}")
                break

    return violations


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    file_path = tool_input.get("file_path", "")
    content = tool_input.get("content", "") or tool_input.get("new_string", "")

    if not file_path or not content:
        sys.exit(0)

    violations = check_file(file_path, content)
    if not violations:
        sys.exit(0)

    ext = Path(file_path).suffix.lower()
    loader = LOADER_PATTERNS.get(ext, 'read your_query.sql from disk')

    msg_lines = [
        "❌ DB GUARD — Inline SQL detected",
        f"   File: {file_path}",
        "   Violations:",
    ] + violations + [
        "",
        "   Raven rule: SQL must live in .sql files only — never inline in source.",
        f"   Extract to: queries/<name>.sql",
        f"   Load in {ext}: {loader}",
    ]

    out = {"additionalContext": "\n".join(msg_lines)}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
