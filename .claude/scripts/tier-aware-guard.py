#!/usr/bin/env python3
"""
Tier-Aware Guard Dispatcher

Hooks use this to determine:
1. Should this guard execute? (based on model tier)
2. Which model should the guard use?
3. Should we skip this operation entirely?

Token efficiency rules:
- SIMPLE tier: skip guards, skip agent spawning, return immediately
- MEDIUM tier: run lightweight checks (Haiku), batch guards
- COMPLEX tier: run full guards (Sonnet), spawn specialist agents
- LOCAL_ONLY: use local models only, no API calls
"""

import json
from pathlib import Path
from typing import Tuple, Optional


def get_model_tier() -> str:
    """
    Read current model tier from .raven/.model-session.json
    Returns: tier string (SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY)
    Fallback: MEDIUM if file doesn't exist
    """
    session_file = Path.cwd() / ".raven" / ".model-session.json"

    if not session_file.exists():
        return "MEDIUM"  # Safe default

    try:
        with open(session_file) as f:
            data = json.load(f)
            return data.get("tier", "MEDIUM")
    except Exception:
        return "MEDIUM"


def should_run_guards(tier: str, operation_type: str) -> bool:
    """
    Determine if guards should execute based on tier and operation.

    Args:
        tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY
        operation_type: "question", "edit", "commit", "bash"

    Returns:
        True if guards should run, False to skip
    """
    # SIMPLE tier: skip all guards for any operation
    if tier == "SIMPLE":
        return False

    # LOCAL_ONLY: run guards only for edits/commits (not questions/bash)
    if tier == "LOCAL_ONLY":
        return operation_type in ["edit", "commit"]

    # MEDIUM/COMPLEX: run guards for all operations
    return True


def should_spawn_specialist_agent(tier: str, operation_type: str) -> bool:
    """
    Determine if specialist agent should be spawned.

    Args:
        tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY
        operation_type: "question", "code_review", "debug", etc.

    Returns:
        True if specialist should spawn, False to skip
    """
    # SIMPLE/MEDIUM: never spawn specialist
    if tier in ["SIMPLE", "MEDIUM"]:
        return False

    # COMPLEX: spawn specialist for complex operations
    if tier == "COMPLEX":
        return operation_type in ["code_review", "debug", "architecture", "refactor"]

    # LOCAL_ONLY: never spawn remote specialist
    return False


def get_guard_model(tier: str) -> str:
    """
    Return the model to use for guard execution.

    Args:
        tier: SIMPLE, MEDIUM, COMPLEX

    Returns:
        Model identifier (open-source Raven: haiku or sonnet)
    """
    model_map = {
        "SIMPLE": "haiku",           # Fast, cheap
        "MEDIUM": "sonnet",          # Balanced
        "COMPLEX": "sonnet",         # Full power
    }
    return model_map.get(tier, "sonnet")


def should_cache_guard_result(tier: str) -> bool:
    """
    Determine if guard results should be cached and reused.

    Args:
        tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY

    Returns:
        True if caching is recommended (SIMPLE/MEDIUM), False if fresh run (COMPLEX)
    """
    # SIMPLE/MEDIUM: aggressive caching (7 days)
    if tier in ["SIMPLE", "MEDIUM"]:
        return True

    # COMPLEX: fresh checks (no cache)
    return False


def get_guard_cache_ttl(tier: str) -> int:
    """
    Return cache TTL in seconds for guard results.

    Args:
        tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY

    Returns:
        TTL in seconds
    """
    ttl_map = {
        "SIMPLE": 604800,          # 7 days
        "MEDIUM": 604800,          # 7 days
        "COMPLEX": 0,              # No cache (fresh checks)
        "LOCAL_ONLY": 604800       # 7 days
    }
    return ttl_map.get(tier, 604800)


def should_batch_guards(tier: str) -> bool:
    """
    Determine if guards should be batched (single agent checking all criteria)
    vs. individual spawning (separate agent per guard).

    Args:
        tier: SIMPLE, MEDIUM, COMPLEX, LOCAL_ONLY

    Returns:
        True if should batch, False if should run individually
    """
    # SIMPLE/MEDIUM: always batch (save tokens)
    if tier in ["SIMPLE", "MEDIUM"]:
        return True

    # COMPLEX: can afford individual guards
    return False


def explain_tier_decision(tier: str) -> dict:
    """
    Return human-readable explanation of tier-based decisions.

    Returns:
        Dict with explanation of what will/won't run
    """
    return {
        "SIMPLE": {
            "description": "Quick question or read-only operation",
            "runs_guards": False,
            "spawns_specialist": False,
            "guard_model": "haiku",
            "cache_ttl": "7 days",
            "estimated_tokens": "0.3K",
            "estimated_cost": "$0.0005"
        },
        "MEDIUM": {
            "description": "Moderate complexity, some code changes",
            "runs_guards": True,
            "guard_model": "gpt-4o-mini",
            "batches_guards": True,
            "spawns_specialist": False,
            "cache_ttl": "7 days",
            "estimated_tokens": "1K",
            "estimated_cost": "$0.02"
        },
        "COMPLEX": {
            "description": "Complex work, major changes, security-critical",
            "runs_guards": True,
            "guard_model": "sonnet",
            "batches_guards": False,
            "spawns_specialist": True,
            "cache_ttl": "none (fresh)",
            "estimated_tokens": "3K",
            "estimated_cost": "$0.10"
        },
        "LOCAL_ONLY": {
            "description": "Secrets detected, offline mode",
            "runs_guards": True,
            "guard_model": "ollama/dolphin-mistral",
            "spawns_specialist": False,
            "location": "local only",
            "estimated_tokens": "0 (local compute)",
            "estimated_cost": "$0"
        }
    }.get(tier, {})


def main():
    """CLI interface for testing."""
    tier = get_model_tier()
    print(f"Current tier: {tier}")
    print(f"Should run guards: {should_run_guards(tier, 'edit')}")
    print(f"Should spawn specialist: {should_spawn_specialist_agent(tier, 'code_review')}")
    print(f"Guard model: {get_guard_model(tier)}")
    print(f"Cache results: {should_cache_guard_result(tier)}")
    print(f"Cache TTL: {get_guard_cache_ttl(tier)} seconds")
    print(f"\nDecision explanation:")
    print(json.dumps(explain_tier_decision(tier), indent=2))


if __name__ == "__main__":
    main()
