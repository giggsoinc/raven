#!/usr/bin/env python3
# Shay-Rolls — Token Guard v2.0
# CORRECT implementation based on actual Claude Code hook capabilities.
#
# Hook events do NOT receive token usage data.
# This script handles TWO triggers:
#   1. PreCompact event — Claude Code is about to compact context (nearly full)
#   2. Notification event — surface warnings as macOS notifications
#
# Called by:
#   PreCompact hook → saves session state before compaction
#   Notification hook → shows desktop toaster warnings

import json, os, sys, subprocess
from datetime import datetime, timezone
from pathlib import Path

STATE_FILE  = ".shay-rolls/.cache/token-guard-state.json"
BACKUP_DIR  = ".shay-rolls/session-backups"

def safe(fn):
    try: return fn()
    except: return None

def notify_macos(title: str, msg: str, subtitle: str = "Shay-Rolls"):
    """Fire a macOS notification toaster."""
    safe(lambda: subprocess.run([
        "osascript", "-e",
        f'display notification "{msg}" with title "{title}" subtitle "{subtitle}"'
    ], timeout=3, capture_output=True))

def save_state(state: dict):
    safe(lambda: (
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True),
        open(STATE_FILE, "w").write(json.dumps(state, indent=2))
    ))

def load_state() -> dict:
    return safe(lambda: json.load(open(STATE_FILE))) or {}

def handle_precompact(data: dict):
    """
    PreCompact fires when Claude Code is about to compact context.
    This means we're near the token limit.
    Save session state and warn the developer.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M")
    backup_file = f"{BACKUP_DIR}/session-{ts}.md"

    # Build session summary
    summary_lines = [
        f"# Session Backup — {ts}",
        f"## Auto-saved by Shay-Rolls Token Guard (PreCompact)",
        f"",
        f"Context window reached compaction threshold.",
        f"",
        f"## Context Being Compacted",
    ]

    # Include what's about to be compacted if available
    summary_hint = data.get("summary_hint", "")
    if summary_hint:
        summary_lines.append(summary_hint)

    summary_lines += [
        "",
        "## Next Steps",
        "- Review what was being worked on",
        "- Run /shay-mem to restore context in new session",
        "- Check git status for uncommitted changes",
    ]

    # Write backup
    with open(backup_file, "w") as f:
        f.write("\n".join(summary_lines))

    # Update state
    state = load_state()
    state["last_compact"] = ts
    state["last_backup"]  = backup_file
    save_state(state)

    # macOS toaster notification
    notify_macos(
        "🔴 Shay-Rolls — Context Nearly Full",
        "Session compacting. Context saved to .shay-rolls/session-backups/",
        f"Run /shay-mem to preserve session"
    )

    # Print to stderr — shows in Claude Code terminal
    print(f"\n{'━'*52}", file=sys.stderr)
    print(f"  Shay-Rolls Token Guard — PreCompact", file=sys.stderr)
    print(f"{'━'*52}", file=sys.stderr)
    print(f"  🔴 Context window reaching limit", file=sys.stderr)
    print(f"  Session backup saved: {backup_file}", file=sys.stderr)
    print(f"  Run /shay-mem to preserve key decisions", file=sys.stderr)
    print(f"{'━'*52}\n", file=sys.stderr)

    # Return additionalContext to inject into Claude's context
    output = {
        "additionalContext": (
            f"⚠️ SHAY-ROLLS TOKEN GUARD: Context window is nearly full and about to compact. "
            f"Session backup saved to {backup_file}. "
            f"Please run /shay-mem to save key decisions and file changes before context resets."
        )
    }
    print(json.dumps(output))

def handle_notification(data: dict):
    """
    Notification hook — fire macOS toaster for important alerts.
    """
    msg = data.get("message", "")
    if not msg:
        sys.exit(0)

    # Only surface important ones
    keywords = ["error", "fail", "blocked", "denied", "warning", "critical"]
    if any(k in msg.lower() for k in keywords):
        notify_macos("Shay-Rolls Alert", msg[:100])

    sys.exit(0)

def main():
    data  = safe(lambda: json.load(sys.stdin)) or {}
    event = data.get("hook_event_name", os.environ.get("CLAUDE_HOOK_EVENT", ""))

    if event == "PreCompact":
        handle_precompact(data)
    elif event == "Notification":
        handle_notification(data)
    else:
        # Called directly — check state and advise
        state = load_state()
        if state.get("last_compact"):
            print(f"Last compact: {state['last_compact']}", file=sys.stderr)
            print(f"Backup at: {state.get('last_backup','')}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
