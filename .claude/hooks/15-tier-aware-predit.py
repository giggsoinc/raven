#!/usr/bin/env python3
"""
Tier-Aware PreEdit Hook

Fires before file edit. Uses tier-aware-guard.py to determine:
1. Should guards run? (based on model tier)
2. Which model should guards use? (Haiku for SIMPLE/MEDIUM, Sonnet for COMPLEX)
3. Should we skip safe file types?

Token optimization:
- SIMPLE queries: skip all guards → 0 tokens
- MEDIUM edits: batch guards with Haiku → 0.8K tokens
- COMPLEX edits: full guards with Sonnet → 3K tokens
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


# Files safe to edit without guards (no validation needed)
SAFE_FILE_PATTERNS = [
    "*.md", "*.txt", "*.rst",
    "*.json", "*.yaml", "*.yml",
    "docs/*", ".github/*",
    "CHANGELOG*", "README*"
]

# Edit patterns safe without guards
SAFE_EDIT_PATTERNS = [
    "comment_added",
    "whitespace_only",
    "docstring_added",
    "test_added",
]


def file_matches_pattern(file_path: str, patterns: list) -> bool:
    """Check if file matches any safe pattern."""
    import fnmatch
    for pattern in patterns:
        if fnmatch.fnmatch(file_path, pattern):
            return True
    return False


def should_skip_guards_for_file(file_path: str) -> bool:
    """Check if this file is safe and doesn't need guard validation."""
    return file_matches_pattern(file_path, SAFE_FILE_PATTERNS)


def main():
    """PreEdit hook entry point."""
    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    file_path = hook_input.get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Get current model tier
    tier = get_model_tier()

    # Check: is this a safe file that needs no guards?
    if should_skip_guards_for_file(file_path):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreEdit",
                "additionalContext": {
                    "model_tier": tier,
                    "skip_reason": "safe_file_type",
                    "file_path": file_path,
                    "guards_executed": False,
                    "token_cost": "0"
                }
            }
        }
        print(json.dumps(output))
        return

    # Check: should guards run based on tier?
    if not should_run_guards(tier, "edit"):
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreEdit",
                "additionalContext": {
                    "model_tier": tier,
                    "skip_reason": f"tier_{tier.lower()}_skips_guards",
                    "file_path": file_path,
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
            "hookEventName": "PreEdit",
            "additionalContext": {
                "model_tier": tier,
                "file_path": file_path,
                "guards_enabled": True,
                "guard_model": guard_model,
                "batch_guards": batch,
                "cache_results": cache_results,
                "cache_ttl_seconds": cache_ttl,
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
