#!/usr/bin/env python3
"""
Raven — Overhead Logger

Any Raven hook/script that contributes to context overhead calls this to
record its token contribution to .raven/.model-session.json.

Usage:
  python3 log-overhead.py --source triage-router --tokens 80
  python3 log-overhead.py --source session-start --tokens 2100
  python3 log-overhead.py --source skill-load:andie --tokens 3100

Tokens default to len(stdin) // 4 if --tokens not given (rough estimate).

Atomic write via temp file + rename. Local-only. No telemetry.
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Empty/init schema — two buckets locked
EMPTY_SCHEMA = {
    "session_started_at": None,
    "raven_overhead": {
        "tokens": 0,
        "cost_usd": 0.0,
        "calls": 0,
        "by_source": {},
    },
    "user_work": {
        "tokens": 0,
        "cost_usd": 0.0,
        "calls": 0,
        "tier_counts": {"SIMPLE": 0, "MEDIUM": 0, "COMPLEX": 0, "LOCAL_ONLY": 0},
    },
    "providers": {},
}

# Rough cost estimates per 1M tokens (Claude pricing — adjust as needed)
COST_PER_1M = {
    "claude-haiku-4-5":  {"in": 0.25, "out": 1.25},
    "claude-sonnet-4-6": {"in": 3.00, "out": 15.00},
    "claude-opus-4-7":   {"in": 15.00, "out": 75.00},
    "ollama":            {"in": 0.00, "out": 0.00},
    "default-overhead":  {"in": 0.25, "out": 0.25},  # overhead enters as input
}


def load_session(path: Path) -> dict:
    """Load existing session JSON or init fresh schema."""
    if not path.exists():
        data = dict(EMPTY_SCHEMA)
        data["raven_overhead"] = dict(EMPTY_SCHEMA["raven_overhead"])
        data["raven_overhead"]["by_source"] = {}
        data["user_work"] = dict(EMPTY_SCHEMA["user_work"])
        data["user_work"]["tier_counts"] = dict(EMPTY_SCHEMA["user_work"]["tier_counts"])
        data["providers"] = {}
        data["session_started_at"] = datetime.now(timezone.utc).isoformat()
        return data
    try:
        data = json.loads(path.read_text())
        # Migrate flat-schema legacy to two-bucket if needed
        if "raven_overhead" not in data:
            legacy_tokens = data.get("session_tokens", 0)
            legacy_cost = data.get("session_cost_usd", 0.0)
            legacy_tiers = data.get("tier_counts", {})
            data = {
                "session_started_at": data.get("session_started_at") or datetime.now(timezone.utc).isoformat(),
                "raven_overhead": {"tokens": 0, "cost_usd": 0.0, "calls": 0, "by_source": {}},
                "user_work": {
                    "tokens": legacy_tokens,
                    "cost_usd": legacy_cost,
                    "calls": data.get("session_calls", 0),
                    "tier_counts": legacy_tiers or {"SIMPLE": 0, "MEDIUM": 0, "COMPLEX": 0, "LOCAL_ONLY": 0},
                },
                "providers": {},
            }
        return data
    except Exception:
        return dict(EMPTY_SCHEMA)


def atomic_write(path: Path, data: dict) -> None:
    """Atomic write via temp file + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


def estimate_cost(tokens: int, model: str = "default-overhead") -> float:
    """Rough cost estimate — overhead is input-token-class."""
    pricing = COST_PER_1M.get(model, COST_PER_1M["default-overhead"])
    return (tokens / 1_000_000) * pricing["in"]


def main():
    parser = argparse.ArgumentParser(description="Log Raven overhead to session JSON")
    parser.add_argument("--source", required=True, help="Source identifier (script name or skill-load:NAME)")
    parser.add_argument("--tokens", type=int, default=0, help="Token count contributed")
    parser.add_argument("--model", default="default-overhead", help="Model class for cost estimate")
    parser.add_argument("--provider", default=None, help="Provider for attribution (anthropic/openai/ollama)")
    args = parser.parse_args()

    # If no tokens given, read stdin and estimate
    tokens = args.tokens
    if tokens == 0:
        try:
            stdin_text = sys.stdin.read()
            tokens = max(1, len(stdin_text) // 4)
        except Exception:
            tokens = 0

    if tokens == 0:
        return  # nothing to log

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    session_path = project_dir / ".raven" / ".model-session.json"

    data = load_session(session_path)
    cost = estimate_cost(tokens, args.model)

    # Update raven_overhead bucket
    overhead = data["raven_overhead"]
    overhead["tokens"] += tokens
    overhead["cost_usd"] = round(overhead["cost_usd"] + cost, 6)
    overhead["calls"] += 1
    src = overhead["by_source"].setdefault(args.source, {"tokens": 0, "calls": 0, "cost_usd": 0.0})
    src["tokens"] += tokens
    src["calls"] += 1
    src["cost_usd"] = round(src["cost_usd"] + cost, 6)

    # Update provider attribution if given
    if args.provider:
        prov = data["providers"].setdefault(args.provider, {"tokens": 0, "cost_usd": 0.0})
        prov["tokens"] += tokens
        prov["cost_usd"] = round(prov["cost_usd"] + cost, 6)

    atomic_write(session_path, data)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Fail-soft — never block the hook chain
        sys.exit(0)
