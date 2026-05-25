#!/usr/bin/env python3
"""
Raven Model Router — UserPromptSubmit Hook

Fires AFTER raven-skill-reminder.py (hook sequence)
Classifies user query into model tier (SIMPLE/MEDIUM/COMPLEX/LOCAL_ONLY)
Writes classification to .raven/.model-session.json
Outputs routing decision to additionalContext for downstream skills

Token cost: ~10 tok per message (classification overhead)
"""

import json
import sys
import subprocess
from pathlib import Path


def _run_classifier(prompt: str, context: str = "") -> dict:
    """
    Call model-router.py to classify the query.

    Returns:
        {tier, score, reasons, model}
    """
    router_script = Path(__file__).parent / "model-router.py"

    if not router_script.exists():
        # Fallback to default if script not found
        return {
            "tier": "MEDIUM",
            "score": 0,
            "reasons": ["classifier_not_found"],
            "model": "ollama/dolphin-mistral"
        }

    try:
        # Build command with proper argument list
        cmd = ["python3", str(router_script), "--prompt", prompt]
        if context:
            cmd.extend(["--context", context])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            # Fall back to default on error
            print(f"Classifier error: {result.stderr}", file=sys.stderr)
            return {
                "tier": "MEDIUM",
                "score": 0,
                "reasons": ["classifier_error"],
                "model": "ollama/dolphin-mistral"
            }
    except Exception as e:
        print(f"Failed to run classifier: {e}", file=sys.stderr)
        return {
            "tier": "MEDIUM",
            "score": 0,
            "reasons": ["classifier_exception"],
            "model": "ollama/dolphin-mistral"
        }


def _write_session_json(tier: str, score: int, reasons: list, model: str, prompt: str) -> None:
    """
    Write classification to .raven/.model-session.json
    """
    import hashlib
    from datetime import datetime

    raven_dir = Path.cwd() / ".raven"
    raven_dir.mkdir(exist_ok=True)

    session_file = raven_dir / ".model-session.json"

    output = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "user_query_hash": hashlib.sha256(prompt.encode()).hexdigest()[:16],
        "tier": tier,
        "score": score,
        "reasons": reasons,
        "model_for_tier": model,
        "env_var_value": f"RAVEN_MODEL_TIER={tier}",
        "note": "Classification for this UserPromptSubmit cycle. Skills can override per-Agent() if needed."
    }

    try:
        session_file.write_text(json.dumps(output, indent=2))
    except Exception as e:
        print(f"Warning: Failed to write {session_file}: {e}", file=sys.stderr)


def is_raven_project(cwd: Path) -> bool:
    """Check if this is a Raven-managed project."""
    if (cwd / ".raven" / "manifest.json").exists():
        return True
    if (cwd / ".model.env").exists():
        return True
    return False


def should_spawn_specialist_agent(tier: str) -> bool:
    """
    Determine if specialist agent should be spawned based on tier.

    SIMPLE: skip specialist (save tokens)
    MEDIUM: skip specialist (save tokens)
    COMPLEX: spawn specialist (full power)
    LOCAL_ONLY: skip specialist (local-only mode)
    """
    return tier == "COMPLEX"


def main():
    """
    UserPromptSubmit hook entry point.

    Reads stdin (user context), extracts prompt, classifies it, writes session JSON.
    Decides whether downstream specialist agents should spawn based on tier.
    """
    cwd = Path.cwd()

    # Skip if not a Raven project
    if not is_raven_project(cwd):
        sys.exit(0)

    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    # Extract user prompt from hook context
    prompt = hook_input.get("userMessage", "")
    if not prompt:
        # Fallback: try to extract from additionalContext
        context_obj = hook_input.get("additionalContext", {})
        if isinstance(context_obj, dict):
            prompt = context_obj.get("prompt", "")
        elif isinstance(context_obj, str):
            prompt = context_obj

    # If no prompt found, skip
    if not prompt:
        sys.exit(0)

    # Classify the query
    context_str = json.dumps(hook_input.get("additionalContext", {}), default=str)
    classification = _run_classifier(prompt, context_str)

    # Write session JSON
    _write_session_json(
        classification["tier"],
        classification["score"],
        classification["reasons"],
        classification["model"],
        prompt
    )

    # Determine if specialist should spawn based on tier
    spawn_specialist = should_spawn_specialist_agent(classification["tier"])

    # Output to hook interface
    output = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": {
                "model_tier": classification["tier"],
                "model_for_tier": classification["model"],
                "classification_reasons": classification["reasons"],
                "env_var": f"RAVEN_MODEL_TIER={classification['tier']}",
                "spawn_specialist_agent": spawn_specialist,
                "token_estimate": {
                    "SIMPLE": "0.3K",
                    "MEDIUM": "0.8K",
                    "COMPLEX": "3K"
                }.get(classification["tier"], "1K")
            }
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
