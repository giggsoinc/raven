#!/usr/bin/env python3
"""
token-meter-write.py — Raven Stop hook v1.0
Reads session transcript JSONL, extracts token usage, calculates costs.
Writes metrics to three files: session JSON, monthly rollup, audit log.
Non-blocking — logs errors but never crashes the session.
"""
import json
import sys
import os
import pathlib
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any

PRICING_FILE = pathlib.Path(__file__).parent / "model-pricing.json"
RAVEN_DIR = pathlib.Path.cwd() / ".raven"
VAULT_DIR = pathlib.Path.home() / "RavenVault"
AUDIT_DIR = RAVEN_DIR / "audit"


def load_pricing() -> Dict[str, Dict[str, float]]:
    """Load model pricing from config file."""
    try:
        if PRICING_FILE.exists():
            return json.loads(PRICING_FILE.read_text())["models"]
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to load pricing config: {e}\n")
    return {}


def get_cost(model: str, tokens_in: int, tokens_out: int, pricing: Dict) -> float:
    """Calculate cost in USD for a model + token counts."""
    model_price = pricing.get(model, pricing.get("gpt-4o", {}))
    if not model_price:
        model_price = pricing.get("default", {"input_per_1m": 1, "output_per_1m": 5})

    in_cost = (tokens_in / 1_000_000) * model_price.get("input_per_1m", 1)
    out_cost = (tokens_out / 1_000_000) * model_price.get("output_per_1m", 5)
    return round(in_cost + out_cost, 6)


def is_raven_code(tool_uses: list, skill_uses: list) -> bool:
    """Detect if a message is from Raven infrastructure vs user work."""
    # Check tool_uses for raven-related paths/commands
    for tool in tool_uses:
        if isinstance(tool, dict):
            # Check if bash command references raven
            if "bash" in str(tool).lower():
                cmd = tool.get("input", {}).get("command", "")
                if any(x in cmd for x in [".raven/", "raven-", ".claude/scripts/"]):
                    return True
            # Check file paths
            path = tool.get("input", {}).get("path", "")
            if any(x in path for x in [".raven/", ".claude/scripts/"]):
                return True

    # Check skill_uses for raven skills
    for skill in skill_uses:
        if isinstance(skill, dict):
            name = skill.get("name", "")
            if name.startswith("raven-") or "raven" in name.lower():
                return True

    return False


def parse_transcript(transcript_path: str) -> Dict[str, Any]:
    """Parse JSONL transcript and extract metrics."""
    metrics = {
        "session_id": "",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model": "unknown",
        "raven_code": {
            "tokens": 0,
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_creation": 0,
            "cost_usd": 0.0,
            "calls": 0,
        },
        "user_work": {
            "tokens": 0,
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_creation": 0,
            "cost_usd": 0.0,
            "calls": 0,
        },
    }
    pricing = load_pricing()
    total_in, total_out, total_cache_read, total_cache_creation = 0, 0, 0, 0

    try:
        with open(transcript_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                try:
                    # Extract usage from assistant messages
                    if msg.get("role") == "assistant":
                        usage = msg.get("message", {}).get("usage", {})
                        if not usage:
                            continue

                        model = msg.get("message", {}).get("model", "unknown")
                        metrics["model"] = model
                        if msg.get("session_id"):
                            metrics["session_id"] = msg["session_id"]

                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        cache_read = usage.get("cache_read_input_tokens", 0)
                        cache_creation = usage.get("cache_creation_input_tokens", 0)

                        # Categorize
                        is_raven = is_raven_code(
                            msg.get("message", {}).get("tool_uses", []),
                            msg.get("message", {}).get("skill_uses", []),
                        )
                        bucket = metrics["raven_code"] if is_raven else metrics["user_work"]

                        # Update totals
                        bucket["calls"] += 1
                        bucket["input"] += input_tokens
                        bucket["output"] += output_tokens
                        bucket["cache_read"] += cache_read
                        bucket["cache_creation"] += cache_creation
                        total_in += input_tokens
                        total_out += output_tokens
                        total_cache_read += cache_read
                        total_cache_creation += cache_creation

                        # Calculate cost (cache_read is 0.1x input, cache_creation is 1.25x input)
                        cost = get_cost(model, input_tokens, output_tokens, pricing)
                        cache_read_cost = (cache_read / 1_000_000) * (
                            pricing.get(model, {}).get("input_per_1m", 1) * 0.1
                        )
                        cache_creation_cost = (cache_creation / 1_000_000) * (
                            pricing.get(model, {}).get("input_per_1m", 1) * 1.25
                        )
                        bucket["cost_usd"] += cost + cache_read_cost + cache_creation_cost

                except Exception as e:
                    sys.stderr.write(f"Warning: Failed to parse message: {e}\n")
                    continue

        # Calculate totals
        metrics["tokens"] = total_in + total_out
        metrics["total"] = {
            "tokens": total_in + total_out,
            "input": total_in,
            "output": total_out,
            "cache_read": total_cache_read,
            "cache_creation": total_cache_creation,
            "cost_usd": metrics["raven_code"]["cost_usd"]
            + metrics["user_work"]["cost_usd"],
            "calls": metrics["raven_code"]["calls"] + metrics["user_work"]["calls"],
        }

    except Exception as e:
        sys.stderr.write(f"Warning: Failed to read transcript {transcript_path}: {e}\n")

    return metrics


def write_session_json(metrics: Dict[str, Any]) -> bool:
    """Write .raven/.model-session.json atomically."""
    try:
        RAVEN_DIR.mkdir(parents=True, exist_ok=True)
        session_file = RAVEN_DIR / ".model-session.json"
        session_file.write_text(json.dumps(metrics, indent=2))
        return True
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to write session JSON: {e}\n")
        return False


def write_monthly_rollup(metrics: Dict[str, Any]) -> bool:
    """Append/merge into ~/RavenVault/.metrics/YYYY-MM.json."""
    try:
        VAULT_DIR.mkdir(parents=True, exist_ok=True)
        metrics_dir = VAULT_DIR / ".metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Extract YYYY-MM from timestamp
        ts = datetime.fromisoformat(metrics["timestamp"].replace("Z", "+00:00"))
        month_file = metrics_dir / f"{ts.strftime('%Y-%m')}.json"

        # Load existing or init
        if month_file.exists():
            try:
                data = json.loads(month_file.read_text())
            except json.JSONDecodeError:
                data = {"sessions": 0, "total": {}, "by_day": {}}
        else:
            data = {"sessions": 0, "total": {}, "by_day": {}}

        # Increment counts
        data["sessions"] += 1
        day_key = ts.strftime("%Y-%m-%d")
        if day_key not in data["by_day"]:
            data["by_day"][day_key] = {
                "sessions": 0,
                "tokens": 0,
                "cost_usd": 0,
            }

        data["by_day"][day_key]["sessions"] += 1
        data["by_day"][day_key]["tokens"] += metrics["total"].get("tokens", 0)
        data["by_day"][day_key]["cost_usd"] += metrics["total"].get("cost_usd", 0)

        # Update monthly totals
        data["total"]["tokens"] = data["total"].get("tokens", 0) + metrics["total"].get(
            "tokens", 0
        )
        data["total"]["cost_usd"] = data["total"].get("cost_usd", 0) + metrics[
            "total"
        ].get("cost_usd", 0)

        month_file.write_text(json.dumps(data, indent=2))
        return True
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to write monthly rollup: {e}\n")
        return False


def write_audit_log(metrics: Dict[str, Any]) -> bool:
    """Append to .raven/audit/YYYY-MM-DD.log."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        ts = datetime.fromisoformat(metrics["timestamp"].replace("Z", "+00:00"))
        log_file = AUDIT_DIR / f"{ts.strftime('%Y-%m-%d')}.log"

        entry = {
            "timestamp": metrics["timestamp"],
            "session_id": metrics.get("session_id", ""),
            "model": metrics.get("model", "unknown"),
            "tokens": metrics["total"].get("tokens", 0),
            "cost_usd": round(metrics["total"].get("cost_usd", 0), 4),
            "raven_calls": metrics["raven_code"].get("calls", 0),
            "user_calls": metrics["user_work"].get("calls", 0),
        }

        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return True
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to write audit log: {e}\n")
        return False


def main() -> None:
    """Read Stop hook stdin, parse transcript, write metrics."""
    try:
        # Read hook input from stdin
        hook_input = json.load(sys.stdin) if not sys.stdin.isatty() else {}
    except Exception:
        hook_input = {}

    transcript_path = hook_input.get("transcript_path", "")
    if not transcript_path:
        sys.stderr.write("No transcript_path in hook input; skipping metrics\n")
        return

    # Parse transcript
    metrics = parse_transcript(transcript_path)

    # Write all three atomically
    write_session_json(metrics)
    write_monthly_rollup(metrics)
    write_audit_log(metrics)

    # Silent on success (hook should be non-blocking)


if __name__ == "__main__":
    main()
