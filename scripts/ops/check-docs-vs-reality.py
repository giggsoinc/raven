#!/usr/bin/env python3
"""
check-docs-vs-reality.py — raven-docs-reality-check (CI + local).

Rule 5 enforcement: CLAUDE.md's "Hook Reality" table must claim exactly the
hooks that .claude/settings.json actually wires — no more, no less. Compares
the set of *.py script names per hook event on both sides.

Exit 0 = docs match reality. Exit 1 = mismatch (each listed).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLAUDE_MD = REPO / "CLAUDE.md"
SETTINGS = REPO / ".claude" / "settings.json"

HOOK_EVENTS = ("SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop")


def claimed_hooks() -> dict:
    """Parse CLAUDE.md's Hook Reality table: event -> set of script names."""
    text = CLAUDE_MD.read_text()
    claims = {}
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        for event in HOOK_EVENTS:
            # Match the event name in the first table cell (backtick-wrapped)
            if re.match(rf"\|\s*`{event}`", line):
                claims[event] = set(re.findall(r"([a-z0-9_-]+\.py)", line))
    return claims


def actual_hooks() -> dict:
    settings = json.loads(SETTINGS.read_text())
    actual = {}
    for event, groups in settings.get("hooks", {}).items():
        scripts = set()
        for g in groups:
            for h in g.get("hooks", []):
                scripts |= set(re.findall(r"([a-z0-9_-]+\.py)", h.get("command", "")))
        actual[event] = scripts
    return actual


def main() -> int:
    claims = claimed_hooks()
    actual = actual_hooks()
    failures = []

    for event in sorted(set(claims) | set(actual)):
        c = claims.get(event, set())
        a = actual.get(event, set())
        if event not in claims:
            failures.append(f"{event}: wired in settings.json but absent from CLAUDE.md table ({sorted(a)})")
            continue
        if event not in actual:
            failures.append(f"{event}: claimed in CLAUDE.md but not wired in settings.json ({sorted(c)})")
            continue
        over = c - a
        under = a - c
        if over:
            failures.append(f"{event}: CLAUDE.md claims scripts not wired: {sorted(over)}")
        if under:
            failures.append(f"{event}: settings.json wires scripts not documented: {sorted(under)}")

    if failures:
        print("raven-docs-reality-check: FAIL (Rule 5 — docs must match wiring)")
        for f in failures:
            print(f"  {f}")
        return 1
    print("raven-docs-reality-check: PASS — CLAUDE.md hook claims match settings.json exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
