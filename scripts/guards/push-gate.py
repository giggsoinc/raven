#!/usr/bin/env python3
"""push-gate.py — PreToolUse: Educate is compulsory when mode=guided.

Default (missing .raven/educate.json) = guided. Mutating Write/Edit/Bash
is denied until .raven/.push-approved exists (UserPromptSubmit go-ahead).
mode=off (educate off / Lucky) allows writes. Read-only Bash always allowed.

SessionStart must NOT delete educate.json (preference persists).
Fail-soft: parse errors exit 0 (do not brick the session).
"""

import json
import os
import re
import sys
import time

NOTICE = (
    "🪶 Educate (guided): briefing first (WHAT/HOW/files, ≤200 words), then stop. "
    "User says go ahead / approved / proceed — then write. "
    "Turn off: educate off or Lucky (persists in .raven/educate.json). "
    "This write was DENIED."
)

READ_ONLY_HEADS = {
    "ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "pwd", "which",
    "file", "stat", "tree", "du", "echo", "env", "uname", "date", "diff",
    "sort", "uniq", "cut", "column", "basename", "dirname",
    "true", "false", "test", "[",
}
READ_ONLY_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "show", "branch", "remote", "rev-parse",
    "ls-files", "blame", "shortlog", "describe", "tag",
}
PY_HEADS = {"python", "python3"}
# Research / classify / tests — not a repo write.
PY_READ_FLAGS = {
    "--status", "--help", "-h", "--version", "--json", "--digest",
    "--cli", "--query-type", "--gaps", "--prompt",
}
PY_WRITE_FLAGS = {
    "--set", "--enable", "--disable", "--session-start", "--html",
    "--write-json", "--build", "--open", "--all", "--obsidian", "--hook",
}
APPROVAL_TTL_SEC = 3600


def repo_root() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def _basename(head: str) -> str:
    return os.path.basename(head.rstrip("\"'"))


def python_is_read_only(tokens: list) -> bool:
    """python3 --status / -m unittest / educate.py (no --set) are research."""
    rest = tokens[1:]
    joined = " ".join(rest)
    if "-c" in rest:
        return False
    if any(f in rest for f in PY_WRITE_FLAGS):
        return False
    if any(t in ("unittest", "pytest") for t in rest) or "-m" in rest:
        return True
    if any(f in rest for f in PY_READ_FLAGS):
        return True
    # Bare script: python3 scripts/memory/educate.py  (prints mode)
    if rest and rest[0].endswith(".py") and not any(a.startswith("-") and a in PY_WRITE_FLAGS for a in rest):
        if not any(a in PY_WRITE_FLAGS for a in rest):
            return True
    if not rest:
        return True
    if "--status" in joined:
        return True
    return False


def bash_is_read_only(command: str) -> bool:
    stripped = re.sub(r"2>>?\S*", "", command)
    if re.search(r"[><]", stripped):
        return False
    for seg in re.split(r"&&|\|\||;|\|", command):
        tokens = seg.strip().split()
        if not tokens:
            continue
        head = _basename(tokens[0])
        if head == "git":
            if len(tokens) < 2 or tokens[1] not in READ_ONLY_GIT_SUBCOMMANDS:
                return False
        elif head in PY_HEADS:
            if not python_is_read_only(tokens):
                return False
        elif head not in READ_ONLY_HEADS:
            return False
    return True


def educate_mode(root: str) -> str:
    path = os.path.join(root, ".raven", "educate.json")
    if not os.path.isfile(path):
        return "guided"
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError, TypeError):
        return "guided"
    if isinstance(data, str):
        mode = data.strip().lower()
    elif isinstance(data, dict):
        mode = str(data.get("mode") or "guided").strip().lower()
    else:
        return "guided"
    if mode in ("auto", "lucky", "off"):
        return "off"
    return "guided"


def approval_ok(root: str) -> bool:
    path = os.path.join(root, ".raven", ".push-approved")
    if not os.path.isfile(path):
        return False
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False
    return age <= APPROVAL_TTL_SEC


def emit(decision, reason, message=None):
    out = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
    }
    if message:
        out["systemMessage"] = message
    print(json.dumps(out))


def main() -> None:
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name", "")
    root = repo_root()

    if tool == "Bash":
        command = (payload.get("tool_input") or {}).get("command", "")
        mutating = not bash_is_read_only(command)
    else:
        mutating = tool in ("Write", "Edit", "MultiEdit", "NotebookEdit")

    if not mutating:
        sys.exit(0)

    if educate_mode(root) == "off":
        sys.exit(0)

    if approval_ok(root):
        sys.exit(0)

    emit("deny", "Educate guided — no go-ahead", NOTICE)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
