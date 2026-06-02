#!/usr/bin/env python3
"""
Raven Enterprise — Token Guard (PreCompact)
Fires before context compaction. Backs up session state and alerts
if context is growing faster than expected (possible runaway loop).

Writes a backup stub to .raven/.cache/pre-compact-{timestamp}.json
Warns locally if token estimate exceeds session budget. No Hub.
"""

import json, os, sys
from pathlib import Path
from datetime import datetime, timezone

CACHE_DIR  = Path(".raven/.cache")
SIGNAL_Q   = CACHE_DIR / "signal-queue.json"
STATS_FILE = CACHE_DIR / "session-stats.json"

HIGH_TOKEN_THRESHOLD = 150_000  # alert when context exceeds this


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text()) if path.exists() else (default or {})
    except Exception:
        return default or {}


def main():
    # PreCompact hook receives the compaction type on stdin
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    compact_type = payload.get("compaction_type", "auto")  # "manual" | "auto"
    now = datetime.now(timezone.utc).isoformat()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Write pre-compact marker
    marker = {
        "event":          "pre-compact",
        "compact_type":   compact_type,
        "timestamp":      now,
    }

    ts_short = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    marker_path = CACHE_DIR / f"pre-compact-{ts_short}.json"
    marker_path.write_text(json.dumps(marker, indent=2))

    # Check session stats for high token usage
    stats = load_json(STATS_FILE)
    tokens_est = stats.get("tokens_estimated", 0)

    if tokens_est > HIGH_TOKEN_THRESHOLD:
        # Local warning only — no Hub telemetry
        queue = load_json(SIGNAL_Q, {"events": []})
        queue.setdefault("events", []).append({
            "type":      "token_alert",
            "tokens":    tokens_est,
            "threshold": HIGH_TOKEN_THRESHOLD,
            "ts":        now,
        })
        SIGNAL_Q.write_text(json.dumps(queue, indent=2))

    # Pass through — never block compaction
    sys.exit(0)


if __name__ == "__main__":
    main()
