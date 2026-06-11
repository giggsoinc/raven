#!/usr/bin/env python3
"""
Raven — Triage Router (v4.2)

Deterministic routing: brownfield default = Andie-jr, greenfield default = Andie.

Precedence (mutually exclusive with architect-router — no double-fire):
  1. Force overrides: /andie, /andie-jr always win (T3.1)
  2. Data-only question (explicit keywords, no code change) → direct answer
  3. Architecture-class prompt (decision intent, no symptom) → SILENT here;
     architect-router owns it and routes to Andie
  4. Brownfield (git exists + commits > 1) → Andie-jr
  5. Greenfield (no .git OR ≤1 commit) → Andie (planning first)

Repo state is the signal for 4/5. If we have code history, we debug with
Andie-jr; mid-session escalation to Andie when a bug turns out architectural
is Andie-jr's skill-level handoff contract.

Local-only. No telemetry.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Trivial bounded edits — no debug panel needed (matches docs/ROUTING.md
# "rename this variable → neither"). Symptom language still overrides.
_TRIVIAL = re.compile(
    r"^\s*(?:rename|fix\s+(?:a\s+)?typo|typo|reformat|re-?indent|sort\s+imports?|"
    r"bump\s+(?:the\s+)?version|add\s+a\s+comment)\b", re.IGNORECASE)

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from router_common import force_intent, semantic_fallback, log_overhead
except Exception:  # fail-soft: routing still works without the shared helper
    def force_intent(_p): return None
    def semantic_fallback(_p, _k): return False
    def log_overhead(_s, _t): return None


def is_brownfield() -> bool:
    """Return True if repo has git history (existing codebase)."""
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            cwd=".", capture_output=True, timeout=1, text=True
        )
        if result.returncode == 0:
            count = int(result.stdout.strip())
            return count > 1  # more than one commit = brownfield
    except Exception:
        pass
    return False


def is_data_question(prompt: str) -> bool:
    """Return True if this is a pure data/question (no code change expected).

    Keywords: read, explain, show, count, list, how does, what is, find, grep, etc.
    Must NOT mention: build, create, write, fix, change, refactor, implement, deploy.
    """
    if not prompt or len(prompt) < 10:
        return False

    data_keywords = {
        "read", "explain", "show", "count", "list", "what", "where", "when",
        "how does", "find", "grep", "search", "query", "describe", "summarize",
        "tell me", "give me", "what is", "why", "how do i", "can you", "help me understand"
    }
    change_keywords = {
        "build", "create", "write", "fix", "change", "refactor", "implement",
        "deploy", "add", "remove", "delete", "update", "modify", "rewrite"
    }

    prompt_lower = prompt.lower()
    has_data_keyword = any(kw in prompt_lower for kw in data_keywords)
    has_change_keyword = any(kw in prompt_lower for kw in change_keywords)

    return has_data_keyword and not has_change_keyword


_ARCHITECT_MOD = None


def _architect_mod():
    """Load architect-router.py once so its decision/symptom regexes have ONE
    source of truth. Fail-soft: any load error → None (triage keeps its
    repo-state default; worst case is the pre-v4.2 double-fire, never a missed
    route)."""
    global _ARCHITECT_MOD
    if _ARCHITECT_MOD is None:
        try:
            import importlib.util
            path = Path(__file__).resolve().parent / "architect-router.py"
            spec = importlib.util.spec_from_file_location("_architect_router", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _ARCHITECT_MOD = mod
        except Exception:
            _ARCHITECT_MOD = False
    return _ARCHITECT_MOD or None


def is_symptom(prompt: str) -> bool:
    """True if the prompt carries symptom language (broken/failing/timeout...)."""
    mod = _architect_mod()
    return bool(mod and mod.SYMPTOM_NEGATE.search(prompt))


def is_architecture_class(prompt: str) -> bool:
    """True if architect-router would claim this prompt (decision intent, no
    symptom language)."""
    mod = _architect_mod()
    return bool(mod and mod.classify(prompt))


def classify(prompt: str) -> Optional[str]:
    """Return 'andie-jr' for brownfield, 'andie' for greenfield, None when
    triage should stay silent (data-only, or architect-router owns it)."""
    symptom = is_symptom(prompt)

    if not symptom and _TRIVIAL.match(prompt) and len(prompt.split()) <= 8:
        return None  # trivial bounded edit — no panel needed

    if is_data_question(prompt) and not symptom:
        return None  # direct answer — but symptom language overrides ("why is X failing")

    if is_architecture_class(prompt):
        return None  # decision/architecture intent → architect-router routes to Andie

    if is_brownfield():
        return "andie-jr"  # existing code = debug/fix mode
    else:
        return "andie"  # new project = planning mode


def main() -> None:
    """Route based on repo state (brownfield → Andie-jr, greenfield → Andie).

    Order: explicit force (T3.1) → repo state classify → opt-in semantic fallback (T3.2).
    """
    prompt = os.environ.get("PROMPT", "")
    if not prompt:
        try:
            prompt = sys.stdin.read()
        except Exception:
            return

    # T3.1: explicit force always wins
    forced = force_intent(prompt)
    if forced == "andie":
        return  # architect-router owns the andie force path
    if forced == "andie-jr":
        _emit_andie_jr(reason="forced via /andie-jr")
        return

    # Deterministic routing by repo state
    routed_to = classify(prompt)
    if routed_to == "andie-jr":
        _emit_andie_jr()
    elif routed_to == "andie":
        _emit_andie()
    # else: None → data question, or architect-router owns it (no emission)


def _emit_andie_jr(reason: str = "brownfield repo detected") -> None:
    """Emit [ANDIE-JR REQUIRED] injection + user-visible toaster."""
    emission = (
        "[ANDIE-JR REQUIRED] Brownfield repo detected. MANDATORY: invoke "
        "`andie-jr` skill BEFORE any diagnosis, file read, bash command, or "
        "response. Andie-jr structures the debug flow: problem → root cause → "
        "fix → why → audit note.\n"
    )
    _emit(emission, f"🪶 Raven → andie-jr · {reason} · debug flow: triage → root cause → fix")
    log_overhead("triage-router", emission)


def _emit_andie(reason: str = "greenfield project detected") -> None:
    """Emit [ANDIE REQUIRED] injection + user-visible toaster."""
    emission = (
        "[ANDIE REQUIRED] Greenfield project detected. MANDATORY: invoke "
        "`andie` skill BEFORE any coding. Andie structures planning: problem → "
        "angles → decisions → plan. Then /andie-jr for implementation.\n"
    )
    _emit(emission, f"🪶 Raven → andie · {reason} · planning flow: problem → angles → plan")
    log_overhead("triage-router", emission)


def _emit(context: str, toast: str) -> None:
    """Write hook JSON: additionalContext for the model + systemMessage toaster
    the user actually sees. The toaster is the visibility contract — Raven never
    routes silently."""
    sys.stdout.write(json.dumps({
        "systemMessage": toast,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        },
    }) + "\n")


if __name__ == "__main__":
    main()
