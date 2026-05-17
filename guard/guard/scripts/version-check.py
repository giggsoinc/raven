#!/usr/bin/env python3
"""
raven version-check.py
Runs at every session boot (referenced from CLAUDE.md).

Rules:
  - Reads project's installed version from .raven/manifest.json → raven_version
  - Compares against RAVEN_LATEST (canonical release list, updated each release)
  - 0 behind   → silent, no output
  - 1-2 behind → warn in session opener, offer on-demand sync
  - 3+ behind  → auto-sync without asking, log the action

Exit codes:
  0 = up to date
  1 = 1-2 releases behind (warn)
  2 = 3+ releases behind (auto-sync triggered)
  3 = manifest missing / version unreadable (treat as unknown, warn)
"""

import json
import os
import sys
import subprocess
from pathlib import Path

# ─── Canonical release history ────────────────────────────────────────────────
# Add each new release to the END of this list.
# Distance = index(latest) - index(installed)
RAVEN_RELEASES = [
    "2.0.0",
    "2.1.0",
    "2.2.0",
    "2.3.0",
    "2.4.0",
    "2.5.0",
    "2.6.0",
    "2.7.0",
    "2.8.0",
    "2.9.0",
    "2.9.1",
    "3.0.0",
]

RAVEN_LATEST = RAVEN_RELEASES[-1]
AUTO_SYNC_THRESHOLD = 3   # releases behind → auto-sync
WARN_THRESHOLD = 1        # releases behind → warn

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "."))
MANIFEST_PATH = PROJECT_ROOT / ".raven" / "manifest.json"


def read_installed_version() -> str | None:
    """Read raven_version from project manifest."""
    if not MANIFEST_PATH.exists():
        return None
    try:
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        return manifest.get("raven_version") or manifest.get("version")
    except (json.JSONDecodeError, OSError):
        return None


def release_distance(installed: str, latest: str) -> int:
    """
    Return how many releases installed is behind latest.
    Returns -1 if installed version not found in release list (unknown/custom).
    """
    try:
        idx_installed = RAVEN_RELEASES.index(installed)
        idx_latest = RAVEN_RELEASES.index(latest)
        return max(0, idx_latest - idx_installed)
    except ValueError:
        return -1


def trigger_auto_sync():
    """
    Trigger raven-sync by writing a flag file that CLAUDE.md picks up.
    The actual sync is performed by the raven-sync skill/command.
    """
    flag_path = PROJECT_ROOT / ".raven" / ".auto-sync-needed"
    flag_path.parent.mkdir(parents=True, exist_ok=True)
    flag_path.write_text(f"auto-sync triggered: installed version was {installed_version}\n")


def main():
    installed = read_installed_version()

    # ── Manifest missing ───────────────────────────────────────────────────────
    if installed is None:
        print(json.dumps({
            "status": "unknown",
            "message": "⚠️  Raven version unknown — manifest missing or has no raven_version field.",
            "installed": None,
            "latest": RAVEN_LATEST,
            "distance": -1,
            "action": "warn",
        }))
        sys.exit(3)

    distance = release_distance(installed, RAVEN_LATEST)

    # ── Up to date ─────────────────────────────────────────────────────────────
    if distance == 0:
        print(json.dumps({
            "status": "ok",
            "installed": installed,
            "latest": RAVEN_LATEST,
            "distance": 0,
            "action": "none",
        }))
        sys.exit(0)

    # ── Unknown version (custom / dev build) ───────────────────────────────────
    if distance == -1:
        print(json.dumps({
            "status": "unknown",
            "message": f"⚠️  Raven version '{installed}' not in known release list. Cannot determine staleness.",
            "installed": installed,
            "latest": RAVEN_LATEST,
            "distance": -1,
            "action": "warn",
        }))
        sys.exit(3)

    # ── 3+ releases behind → auto-sync ────────────────────────────────────────
    if distance >= AUTO_SYNC_THRESHOLD:
        trigger_auto_sync()
        print(json.dumps({
            "status": "auto-sync",
            "message": (
                f"🔄 Raven is {distance} releases behind (installed: {installed} → latest: {RAVEN_LATEST}). "
                f"AUTO-SYNC triggered — updating now."
            ),
            "installed": installed,
            "latest": RAVEN_LATEST,
            "distance": distance,
            "action": "auto-sync",
        }))
        sys.exit(2)

    # ── 1-2 releases behind → warn, offer on-demand sync ──────────────────────
    print(json.dumps({
        "status": "stale",
        "message": (
            f"⚠️  Raven is {distance} release{'s' if distance > 1 else ''} behind "
            f"(installed: {installed} → latest: {RAVEN_LATEST}). "
            f"Say 'update raven' or run /raven-sync to update."
        ),
        "installed": installed,
        "latest": RAVEN_LATEST,
        "distance": distance,
        "action": "warn",
    }))
    sys.exit(1)


if __name__ == "__main__":
    installed_version = read_installed_version()
    main()
