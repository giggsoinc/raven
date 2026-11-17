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


# Text the user pasted or quoted is not the user's own instruction. A report
# that happens to contain "go ahead" or "Lucky" must not open the gate or
# switch Educate off.
QUOTED_PATTERN = re.compile(
    r"<pasted_content\b[^>]*>.*?</pasted_content[^>]*>"
    r"|<pasted_content\b.*\Z"
    r"|```.*?```"
    r"|`[^`\n]*`"
    r"|\"[^\"\n]*\""
    r"|“[^”\n]*”"
    r"|(?m:^[ \t]*>[^\n]*)",
    re.DOTALL,
)
LONG_MESSAGE = 400  # beyond this, a keyword only counts at the start or end
WINDOW = 120


def own_words(prompt: str) -> str:
    """The prompt minus pasted blocks, code, quotes and blockquote lines."""
    return QUOTED_PATTERN.sub(" ", prompt).strip()


def matches(pattern: "re.Pattern", text: str) -> bool:
    """Short messages match anywhere. Long ones only at the start or end."""
    if len(text) <= LONG_MESSAGE:
        return bool(pattern.search(text))
    return bool(pattern.search(text[:WINDOW]) or pattern.search(text[-WINDOW:]))


def raven_path(*parts: str) -> str:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return os.path.join(root, ".raven", *parts)


def write_file(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(content)


def set_educate(mode: str) -> None:
    write_file(raven_path("educate.json"), json.dumps({"mode": mode}, indent=2) + "\n")


def current_mode() -> str:
    """'off' when .raven/educate.json says off/auto/lucky, else 'guided' (the default)."""
    try:
        with open(raven_path("educate.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        mode = str(data.get("mode") if isinstance(data, dict) else data).strip().lower()
    except (OSError, ValueError):
        return "guided"
    return "off" if mode in ("off", "auto", "lucky") else "guided"


def main() -> None:
    payload = json.load(sys.stdin)
    prompt = payload.get("prompt", "") or ""
    text = own_words(prompt)

    if matches(OFF_PATTERN, text):
        set_educate("off")
        write_file(raven_path(".push-approved"), prompt[:200])
        print("⚡ EDUCATE: off (Lucky/auto). Writes allowed. User owns risk. "
              "Persists in .raven/educate.json until educate on.")
        return
    if matches(ON_PATTERN, text):
        set_educate("guided")
        try:
            os.remove(raven_path(".push-approved"))
        except OSError:
            pass
        print("🎓 EDUCATE: guided. Briefing then go-ahead before writes. "
              "Persists in .raven/educate.json.")
        return

    if matches(APPROVAL_PATTERN, text):
        write_file(raven_path(".push-approved"), prompt[:200])
        # When educate is off the gate is always open, so a "go-ahead" banner is noise.
        if current_mode() == "guided":
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
