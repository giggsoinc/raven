#!/usr/bin/env python3
"""Shared helpers for Raven's UserPromptSubmit routers (triage + architect).

Provides three things the routers reuse:
  - force_intent(): T3.1 — explicit user override ("/andie", "use andie-jr", ...)
    so a user can force-invoke a skill when the regex heuristics miss.
  - semantic_fallback(): T3.2 — OPT-IN local-model classifier that catches false
    negatives the regex misses. Off by default (zero latency); enable via
    .raven/router-config.json {"semantic_fallback": true}. Strict timeout,
    fail-soft — on any error it behaves exactly like "no fallback".
  - log_overhead(): single shared overhead logger (was duplicated in both routers).

Local-only. No telemetry.
"""
import json
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional

# Explicit force-invoke phrases. Order matters: check the more specific andie-jr
# first so "/andie-jr" doesn't match the generic andie pattern.
_FORCE_JR = re.compile(
    r"(?:^|\s)/andie-jr\b|\b(?:force|use|invoke|run)\s+andie-jr\b|\bandie-jr\s*:", re.I)
_FORCE_ANDIE = re.compile(
    r"(?:^|\s)/andie\b|\b(?:force|use|invoke|run)\s+andie\b|\bandie\s*:", re.I)


def force_intent(prompt: str) -> Optional[str]:
    """Return 'andie-jr' or 'andie' if the user explicitly forced it, else None."""
    if not prompt:
        return None
    if _FORCE_JR.search(prompt):
        return "andie-jr"
    if _FORCE_ANDIE.search(prompt):
        return "andie"
    return None


def _config() -> dict:
    """Read .raven/router-config.json (best-effort); empty dict if absent/bad."""
    p = Path(".raven/router-config.json")
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def semantic_fallback(prompt: str, kind: str) -> bool:
    """OPT-IN local-model classifier. Returns True if the prompt matches `kind`.

    `kind` is a short natural-language description of the target class. Disabled
    unless config has semantic_fallback=true. Pre-filters trivial prompts to avoid
    needless model calls. Any error/timeout → False (fail-soft = no false block).
    """
    cfg = _config()
    if not cfg.get("semantic_fallback"):
        return False
    if not prompt or len(prompt.split()) < 12:  # skip trivial prompts
        return False
    model = cfg.get("semantic_model", "dolphin-mistral:latest")
    timeout = float(cfg.get("semantic_timeout_s", 2.5))
    ask = (f"Answer with only YES or NO. Is the following user message {kind}?\n\n"
           f"Message: {prompt[:600]}\n\nAnswer:")
    try:
        body = json.dumps({
            "model": model, "prompt": ask, "stream": False,
            "options": {"num_predict": 3, "temperature": 0},
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate", data=body,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            answer = json.loads(resp.read()).get("response", "")
        return answer.strip().upper().startswith("YES")
    except Exception:
        return False


def log_overhead(source: str, text: str) -> None:
    """Fire log-overhead.py (fail-soft) to record this injection's token cost."""
    try:
        log_path = Path(__file__).parent / "log-overhead.py"
        if not log_path.exists():
            return
        tokens = max(1, len(text) // 4)
        subprocess.Popen(
            ["python3", str(log_path), "--source", source, "--tokens", str(tokens)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass  # never block
