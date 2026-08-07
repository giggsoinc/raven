#!/usr/bin/env python3
"""push-approve.py — UserPromptSubmit hook for the Educated Push Contract.

Watches the user's message for:
  'guided' / 'auto'  → sets session mode in .raven/.push-mode
  go-ahead words     → creates .raven/.push-approved (opens push-gate for a turn)
  'Lucky'            → existing opt-out keyword, also opens the gate

Any other message clears a leftover approval flag so each change cycle starts
clean. This script is the ONLY flag cleaner — a Stop-hook rm was removed after
it raced prompt submission and deleted fresh approvals. Mode persists until
SessionStart resets it. Fail-soft: any internal error exits 0.
"""

import json
import os
import re
import sys

APPROVAL_PATTERN = re.compile(
    r"(?:\bgo[- ]?ahead\b|\bapproved?\b|\bproceed\b|\bship it\b|\blgtm\b"
    r"|\bdo it\b|\bbuild it\b|^\s*go\s*$|^\s*yes\s*$|\bLucky\b)",
    re.IGNORECASE,
)
GUIDED_PATTERN = re.compile(r"^\s*guided\b|\bguided mode\b", re.IGNORECASE)
AUTO_PATTERN = re.compile(r"^\s*auto\b|\bauto mode\b", re.IGNORECASE)


def raven_path(*parts: str) -> str:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.join(root, ".raven", *parts)


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def main() -> None:
    payload = json.load(sys.stdin)
    prompt = payload.get("prompt", "") or ""

    if GUIDED_PATTERN.search(prompt):
        write_file(raven_path(".push-mode"), "guided")
        print("🎓 EDUCATED PUSH: GUIDED mode set for this session — every change "
              "needs a 200-word briefing and the user's go-ahead first.")
        return
    if AUTO_PATTERN.search(prompt):
        write_file(raven_path(".push-mode"), "auto")
        print("⚡ EDUCATED PUSH: AUTO mode set for this session — write gate open, "
              "no briefings required. User owns risk.")
        return

    if APPROVAL_PATTERN.search(prompt):
        write_file(raven_path(".push-approved"), prompt[:200])
        print("✅ EDUCATED PUSH: approval detected — write gate OPEN for this turn. "
              "Execute the approved briefing, then confirm in max 150 words "
              "(bullets + changed files).")
    else:
        try:
            os.remove(raven_path(".push-approved"))
        except OSError:
            pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
