#!/usr/bin/env python3
"""
Tier-Aware PreCommit Hook

Fires before git commit. Uses tier-aware-guard.py to determine:
1. Should guards run? (based on model tier)
2. Which model should guards use?
3. Are there safe commit patterns that skip validation?

Token optimization:
- Safe commits (docs:, chore:, test:): 0 tokens
- SIMPLE tier: 0 tokens (skip all guards)
- MEDIUM tier: batch guards with Haiku → 0.8K tokens
- COMPLEX tier: full guards with Sonnet → 3K tokens
"""

import json
import sys
from pathlib import Path

# Add scripts directory to path for tier-aware-guard import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

try:
    from tier_aware_guard import (
        get_model_tier,
        should_run_guards,
        get_guard_model,
        should_batch_guards,
        should_cache_guard_result,
        get_guard_cache_ttl
    )
except ImportError:
    # Fallback if script not found
    def get_model_tier():
        return "MEDIUM"
    def should_run_guards(tier, op):
        return True
    def get_guard_model(tier):
        return "haiku"
    def should_batch_guards(tier):
        return True
    def should_cache_guard_result(tier):
        return True
    def get_guard_cache_ttl(tier):
        return 604800


# Commit patterns safe to commit without guards
SAFE_COMMIT_PATTERNS = [
    "docs:",      # Documentation changes
    "test:",      # Test additions
    "chore:",     # Maintenance
    "fix typo",   # Typo fixes
    "update README",
    "update changelog",
]


def matches_safe_commit_pattern(commit_msg: str) -> bool:
    """Check if commit message matches a safe pattern."""
    commit_msg_lower = commit_msg.lower()
    for pattern in SAFE_COMMIT_PATTERNS:
        if commit_msg_lower.startswith(pattern.lower()):
            return True
    return False


def main():
    """PreCommit hook entry point."""
    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    commit_msg = hook_input.get("commit_message", "")
    if not commit_msg:
        sys.exit(0)

    # Get current model tier
    tier = get_model_tier()

    # Check: is this a safe commit pattern?
    if matches_safe_commit_pattern(commit_msg):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreCommit",
                "additionalContext": {
                    "model_tier": tier,
                    "commit_message": commit_msg,
                    "skip_reason": "safe_commit_pattern",
                    "guards_executed": False,
                    "token_cost": "0"
                }
            }
        }
        print(json.dumps(output))
        return

    # Check: should guards run based on tier?
    if not should_run_guards(tier, "commit"):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreCommit",
                "additionalContext": {
                    "model_tier": tier,
                    "commit_message": commit_msg,
                    "skip_reason": f"tier_{tier.lower()}_skips_guards",
                    "guards_executed": False,
                    "token_cost": "0"
                }
            }
        }
        print(json.dumps(output))
        return

    # Guards should run
    guard_model = get_guard_model(tier)
    batch = should_batch_guards(tier)
    cache_results = should_cache_guard_result(tier)
    cache_ttl = get_guard_cache_ttl(tier)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreCommit",
            "additionalContext": {
                "model_tier": tier,
                "commit_message": commit_msg,
                "guards_enabled": True,
                "guard_model": guard_model,
                "batch_guards": batch,
                "cache_results": cache_results,
                "cache_ttl_seconds": cache_ttl,
                "checks": [
                    "secrets_scan",
                    "style_violations",
                    "breaking_changes",
                    "manifest_impact"
                ],
                "token_estimate": {
                    "SIMPLE": "0",
                    "MEDIUM": "0.8K",
                    "COMPLEX": "3K"
                }.get(tier, "1K")
            }
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
