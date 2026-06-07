#!/usr/bin/env python3
"""
Raven v4.1 — Triage Router (Deterministic Repo-State)

Routes prompts based on repository state + intent:

1. FORCE PATHS (always win):
   /andie, /andie-jr → route to that specialist directly

2. DATA QUESTIONS (read, explain, show, list, what):
   No change verbs → route direct, no skill

3. BROWNFIELD (git history > 1 commit):
   Change prompts → route to andie-jr for fast triage

4. GREENFIELD (≤1 commit or no git):
   Any prompt → route to Andie for architectural guidance

Local-only. No telemetry. ~70 LOC.
"""

import os
import re
import sys
import subprocess
from pathlib import Path


def get_prompt() -> str:
    """Fetch prompt from env or stdin."""
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            pass
    return prompt.strip()


def check_force_path(prompt: str) -> str:
    """Return skill name if prompt starts with /andie or /andie-jr, else ''."""
    match = re.match(r"^\s*(/andie-jr|/andie)\b", prompt, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return ""


def is_data_question(prompt: str) -> bool:
    """
    True if prompt is purely informational (read, explain, show, list, what).
    False if prompt contains any change verb (build, fix, create, update, delete, etc.)
    """
    # Change verbs — if present, NOT a data question
    change_verbs = re.compile(
        r"\b(?:"
        r"build|create|write|implement|add|fix|update|modify|change|delete|remove|"
        r"refactor|redesign|rewrite|migrate|deploy|run|execute|transform|convert|"
        r"generate|write|install|setup|configure|enable|disable|start|stop|restart"
        r")\b",
        re.IGNORECASE,
    )

    if change_verbs.search(prompt):
        return False

    # Data verbs — if present without change verbs, IS a data question
    data_verbs = re.compile(
        r"\b(?:"
        r"read|show|list|explain|describe|summarize|display|print|check|verify|"
        r"review|examine|look|find|search|what|how|why|where|when|which"
        r")\b",
        re.IGNORECASE,
    )

    return data_verbs.search(prompt) is not None


def get_git_commit_count() -> int:
    """Return commit count in current repo. 0 if no git or error."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--all", "--count"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except Exception:
        pass
    return 0


def is_brownfield() -> bool:
    """True if repo has >1 commit, False otherwise."""
    return get_git_commit_count() > 1


def classify(prompt: str) -> str:
    """
    Return routing decision:
    - "/andie" or "/andie-jr" → force path wins
    - "data question" (no change verbs) → "direct" (no skill)
    - brownfield (>1 commit) → "andie-jr"
    - greenfield (≤1 commit) → "andie"
    """
    if not prompt:
        return "andie"  # default

    # 1. Force paths always win
    force = check_force_path(prompt)
    if force:
        return force

    # 2. Data questions route direct (no skill)
    if is_data_question(prompt):
        return "direct"

    # 3. Brownfield vs. greenfield routing
    if is_brownfield():
        return "andie-jr"
    else:
        return "andie"


def main():
    # RAVEN_DISABLED opt-out
    if os.environ.get("RAVEN_DISABLED") == "1":
        _log_overhead("triage-router", "RAVEN_DISABLED=1 — skipped")
        return

    prompt = get_prompt()
    if not prompt:
        return

    routing = classify(prompt)

    if routing == "direct":
        # Data question — no skill needed
        _log_overhead("triage-router", f"Data question routed direct")
        return

    if routing == "andie-jr":
        emission = (
            "[ANDIE-JR REQUIRED] Brownfield repository detected (>1 commit). "
            "MANDATORY: invoke `andie-jr` skill BEFORE any response, diagnosis, or file read. "
            "Andie-jr structures: problem → root cause → fix → why → audit.\n"
        )
        sys.stdout.write(emission)
        _log_overhead("triage-router", f"Brownfield → andie-jr")
    elif routing == "andie":
        emission = (
            "[ANDIE REQUIRED] Greenfield or force-path detected. "
            "MANDATORY: invoke `andie` skill for architectural guidance before proceeding.\n"
        )
        sys.stdout.write(emission)
        _log_overhead("triage-router", f"Greenfield/force → andie")
    elif routing in ("/andie", "/andie-jr"):
        emission = f"[FORCE-PATH] User requested {routing}. Route directly.\n"
        sys.stdout.write(emission)
        _log_overhead("triage-router", f"Force-path: {routing}")


def _log_overhead(source: str, text: str) -> None:
    """Fire log-overhead.py in fail-soft mode."""
    try:
        script_dir = Path(__file__).parent
        log_path = script_dir / "log-overhead.py"
        if not log_path.exists():
            return
        tokens = max(1, len(text) // 4)
        subprocess.Popen(
            ["python3", str(log_path), "--source", source, "--tokens", str(tokens)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
