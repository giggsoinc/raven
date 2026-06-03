#!/usr/bin/env python3
"""
Raven — Triage Router

Single classifier that runs on every UserPromptSubmit BEFORE any skill loads.
Asks one question: "Is the user reporting a symptom of an existing system?"

Rule (both must match):
  (a) prompt references an EXISTING system/service/component
  (b) prompt contains DEVIATION language (timeout/slow/fail/broken/hang/etc.)

If both → print [ANDIE-JR REQUIRED] to stdout. Claude Code injects it as
additionalContext and the model loads andie-jr first.

If not → silent passthrough. Other skills route normally.

Local-only. No telemetry. ~40 LOC.
"""

import os
import re
import sys

# ── DEVIATION language — any one match triggers (b) ────────────────────────────
DEVIATION = re.compile(
    r"(?:"
    r"\bnot\s+(?:working|responding|loading|firing|starting|connecting|booting)\b"
    r"|\btiming?\s*out\b|\btimed?\s*out\b|\btimeout\b"
    r"|\bslow\b|\bsluggish\b|\blaggy\b|\bdegraded\b|\bflaky\b|\bintermittent\b"
    r"|\bfail(?:ing|ed|s|ure)?\b|\bcrash(?:ing|ed|es)?\b|\bhang(?:ing|s)?\b"
    r"|\bstuck\b|\bfrozen\b|\bunresponsive\b"
    r"|\bbroken\b|\bborked\b|\bbusted\b"
    r"|\berror\b|\bexception\b|\btraceback\b|\bstack\s*trace\b"
    r"|\bregression\b|\bused\s+to\s+\w+|\bworked\s+(?:yesterday|before|earlier|fine)\b"
    r"|\bwrong\s+(?:output|result|behavior|behaviour|answer|value)\b"
    r"|\bunexpected\b|\bweird\b|\bweird\s+behavior\b"
    r"|\bwhy\s+(?:is|isn'?t|did|does|won'?t)\s+(?:my|the|this)\b"
    r"|\bdoesn'?t\s+(?:work|run|fire|return|load|start)\b"
    r"|\bcan'?t\s+(?:connect|reach|access|find|load)\b"
    r")",
    re.IGNORECASE,
)

# ── EXISTING SYSTEM signals — any one match triggers (a) ───────────────────────
EXISTING_SYSTEM = re.compile(
    r"\b(?:"
    r"servers?|services?|apis?|endpoints?|databases?|dbs?|tables?|queries|migrations?"
    r"|mcp|hooks?|skills?|plugins?|agents?|guards?|routers?|pipelines?|queues?|workers?|jobs?|cron"
    r"|tests?|builds?|deploys?|deployments?|prod(?:uction)?|staging|env(?:ironment)?s?"
    r"|containers?|pods?|nodes?|clusters?|instances?|processes|daemons?"
    r"|modules?|packages?|libraries|dependenc(?:y|ies)|imports?|components?"
    r"|integrations?|webhooks?|callbacks?|triggers?|listeners?"
    r"|connections?|sessions?|requests?|responses?|streams?"
    r"|files?|configs?|settings?|env\s*vars?|secrets?"
    r"|the\s+(?:app|application|system|tool|script|repo|code|setup|build|test)"
    r"|my\s+(?:app|application|system|tool|script|repo|project|code|setup|build|test)"
    r")\b",
    re.IGNORECASE,
)

# ── NEW-WORK negation — only matches when verb is followed by article+noun ─────
# Tight: "build me a", "build a", "create the", etc. — NOT "the build is failing"
NEW_WORK = re.compile(
    r"(?:"
    r"\bbuild\s+(?:me\s+)?(?:a|an|the|new)\s+\w"
    r"|\bcreate\s+(?:me\s+)?(?:a|an|the|new)\s+\w"
    r"|\bset\s*up\s+(?:a|an|the|new)\s+\w"
    r"|\bscaffold\b|\bbootstrap\b|\binitialize\b"
    r"|\bstart\s+(?:a|an)\s+new\b"
    r"|\bdesign\s+(?:a|an|the|new)\s+\w"
    r"|\bplan\s+(?:a|an|the|new)\s+\w"
    r"|\bhow\s+do\s+i\s+(?:build|create|design|implement|add|write|set\s*up)\b"
    r"|\bimplement\s+(?:a|an|the|new)\s+\w"
    r"|\badd\s+(?:a|an|the|new)\s+\w"
    r")",
    re.IGNORECASE,
)


def classify(prompt: str) -> bool:
    """Return True if prompt is a symptom report (andie-jr required)."""
    if not prompt or not prompt.strip():
        return False
    has_deviation = bool(DEVIATION.search(prompt))
    has_system   = bool(EXISTING_SYSTEM.search(prompt))
    is_new_work  = bool(NEW_WORK.search(prompt))
    # Symptom report = existing system + deviation, NOT new build
    return has_deviation and has_system and not is_new_work


def main():
    # RAVEN_DISABLED opt-out — auditable session-level kill switch
    if os.environ.get("RAVEN_DISABLED") == "1":
        _log_overhead("raven-disabled", "RAVEN_DISABLED=1 — triage-router skipped")
        return
    # Claude Code passes the prompt via $PROMPT env or stdin
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            return
    if classify(prompt):
        # additionalContext injection — Claude Code reads stdout on UserPromptSubmit
        emission = (
            "[ANDIE-JR REQUIRED] This prompt reports a symptom on an existing "
            "system. MANDATORY: invoke `andie-jr` skill BEFORE any diagnosis, "
            "file read, bash command, or response. Andie-jr structures the "
            "debug flow: problem → root cause → fix → why → audit note.\n"
        )
        sys.stdout.write(emission)
        # Log as raven_overhead — this injection contributes to context
        _log_overhead("triage-router", emission)


def _log_overhead(source: str, text: str) -> None:
    """Fire log-overhead.py in fail-soft mode to record contribution."""
    try:
        import subprocess
        from pathlib import Path
        script_dir = Path(__file__).parent
        log_path = script_dir / "log-overhead.py"
        if not log_path.exists():
            return
        tokens = max(1, len(text) // 4)
        subprocess.Popen(
            ["python3", str(log_path), "--source", source, "--tokens", str(tokens)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # never block


if __name__ == "__main__":
    main()
