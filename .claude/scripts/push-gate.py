#!/usr/bin/env python3
"""push-gate.py — PreToolUse hook enforcing the Educated Push Contract.

Modes (stored in .raven/.push-mode, reset every SessionStart):
  unset   → first mutating action asks the user: guided or auto? (5-line sample)
  guided  → Edit/Write/MultiEdit/mutating Bash denied until .raven/.push-approved
            exists (created by push-approve.py on a go-ahead; cleared by
            push-approve.py on any non-approval message — NOT by a Stop hook,
            which races prompt submission and deletes fresh approvals)
  auto    → gate stays open all session; user owns risk

Read-only Bash always passes so briefings can be researched.
Fail-soft: any internal error exits 0 (never bricks the session).
"""

import json
import os
import re
import sys
import time

FLAG_TTL_SECONDS = 3600  # stale flags expire after 1h

# Bash commands allowed without approval (read-only research)
READ_ONLY_HEADS = {
    "ls", "cat", "head", "tail", "grep", "rg", "find", "wc", "pwd", "which",
    "file", "stat", "tree", "du", "echo", "env", "uname", "date", "diff",
    "sort", "uniq", "cut", "awk", "sed", "jq", "column", "basename", "dirname",
}
READ_ONLY_GIT_SUBCOMMANDS = {
    "status", "log", "diff", "show", "branch", "remote", "rev-parse",
    "ls-files", "blame", "shortlog", "describe", "tag", "stash",
}

ASK_MODE_MESSAGE = (
    "EDUCATED PUSH GATE: first change of this session — ask the user to pick a "
    "mode before doing anything else. Show them EXACTLY this sample:\n"
    "  You:   add rate limiting to the API\n"
    "  Raven: 📋 Briefing — what/how/files affected (200 words max)… say 'go ahead'\n"
    "  You:   go ahead\n"
    "  Raven: ✅ Done — bullets + changed files (150 words max)\n"
    "Then ask: reply 'guided' to work this way, or 'auto' to skip briefings "
    "this session. STOP and wait for their answer."
)

DENY_MESSAGE = (
    "EDUCATED PUSH GATE: blocked — no go-ahead from the human yet. "
    "Before any change, present an educated push briefing (max 200 words): "
    "bullets covering WHAT will be done, HOW it works, and WHAT will change "
    "(files, db, config). Then STOP and wait. The user unlocks this gate by "
    "replying 'go ahead' / 'approved' / 'GO'. After execution, confirm in max "
    "150 words: bullets + changed files. Do not retry this tool call until "
    "approval is given."
)


def repo_root() -> str:
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def current_mode() -> str:
    """Returns 'guided', 'auto', or '' (unset)."""
    try:
        with open(os.path.join(repo_root(), ".raven", ".push-mode")) as fh:
            mode = fh.read().strip().lower()
        return mode if mode in ("guided", "auto") else ""
    except OSError:
        return ""


def flag_is_valid() -> bool:
    flag = os.path.join(repo_root(), ".raven", ".push-approved")
    try:
        age = time.time() - os.path.getmtime(flag)
    except OSError:
        return False
    return age < FLAG_TTL_SECONDS


def bash_is_read_only(command: str) -> bool:
    """True only if every segment of a compound command is read-only."""
    if re.search(r"[><]", command):  # any redirection writes
        return False
    segments = re.split(r"&&|\|\||;|\|", command)
    for seg in segments:
        tokens = seg.strip().split()
        if not tokens:
            continue
        head = tokens[0]
        if head == "git":
            if len(tokens) < 2 or tokens[1] not in READ_ONLY_GIT_SUBCOMMANDS:
                return False
            if tokens[1] == "stash" and len(tokens) > 2 and tokens[2] != "list":
                return False
        elif head not in READ_ONLY_HEADS:
            return False
    return True


def deny(message: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }
    }))
    sys.exit(0)


def main() -> None:
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name", "")
    mode = current_mode()
    if mode == "auto" or flag_is_valid():
        sys.exit(0)
    if tool == "Bash":
        command = (payload.get("tool_input") or {}).get("command", "")
        if bash_is_read_only(command):
            sys.exit(0)
    elif tool not in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        sys.exit(0)
    deny(DENY_MESSAGE if mode == "guided" else ASK_MODE_MESSAGE)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
