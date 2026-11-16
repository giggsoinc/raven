#!/usr/bin/env python3
"""push-approve.py — UserPromptSubmit for Educate.

  educate off | auto | Lucky  → persist .raven/educate.json mode=off
  educate on | guided         → persist mode=guided
  go ahead / approved / GO    → .raven/.push-approved (one turn)

Any other message clears leftover .push-approved.
Does not delete educate.json. Fail-soft.
"""

import json
import os
import re
import sys

APPROVAL_PATTERN = re.compile(
    r"(?:\bgo[- ]?ahead\b|\bapproved?\b|\bproceed\b|\bship it\b|\blgtm\b"
    r"|\bdo it\b|\bbuild it\b|^\s*go\s*$|^\s*yes\s*$)",
    re.IGNORECASE,
)
OFF_PATTERN = re.compile(
    r"(?:\beducate\s+off\b|\bauto mode\b|^\s*auto\s*$|\bLucky\b)",
    re.IGNORECASE,
)
ON_PATTERN = re.compile(
    r"(?:\beducate\s+on\b|\bguided mode\b|^\s*guided\s*$|^\s*educate\s*$)",
    re.IGNORECASE,
)


def raven_path(*parts: str) -> str:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.join(root, ".raven", *parts)


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def set_educate(mode: str) -> None:
    write_file(raven_path("educate.json"), json.dumps({"mode": mode}, indent=2) + "\n")


def main() -> None:
    payload = json.load(sys.stdin)
    prompt = payload.get("prompt", "") or ""

    if OFF_PATTERN.search(prompt):
        set_educate("off")
        write_file(raven_path(".push-approved"), prompt[:200])
        print("⚡ EDUCATE: off (Lucky/auto). Writes allowed. User owns risk. "
              "Persists in .raven/educate.json until educate on.")
        return
    if ON_PATTERN.search(prompt):
        set_educate("guided")
        try:
            os.remove(raven_path(".push-approved"))
        except OSError:
            pass
        print("🎓 EDUCATE: guided. Briefing then go-ahead before writes. "
              "Persists in .raven/educate.json.")
        return

    if APPROVAL_PATTERN.search(prompt):
        write_file(raven_path(".push-approved"), prompt[:200])
        print("✅ EDUCATE: go-ahead — write gate OPEN this turn. "
              "Execute the briefing, then confirm in max 150 words.")
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
