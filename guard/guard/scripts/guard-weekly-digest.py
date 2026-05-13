#!/usr/bin/env python3
# Raven Guard — Weekly Digest Sender
# Reads digest.log, formats, sends to Prism7, clears log
# Run via cron: 0 8 * * 1 python3 .claude/scripts/guard-weekly-digest.py
# Silent if not configured or no events this week

import json, os, sys, urllib.request
from datetime import datetime, timezone

def safe(fn):
    try: return fn()
    except: return None

def load_secrets():
    return safe(lambda: json.load(open(".raven/manifest.secrets.json"))) or {}

def main():
    digest_path = ".raven/guard/digest.log"
    if not os.path.exists(digest_path):
        sys.exit(0)  # Nothing to send

    events = []
    safe(lambda: [events.append(json.loads(l)) for l in open(digest_path)])
    if not events:
        sys.exit(0)

    secrets = load_secrets()
    webhook = secrets.get("guard", {}).get("webhook_url", "")
    inbox   = secrets.get("approvals", {}).get("shared_inbox", "")
    if not webhook and not inbox:
        sys.exit(0)  # Not configured — skip silently

    p1 = [e for e in events if e.get("severity") == "P1"]
    p2 = [e for e in events if e.get("severity") == "P2"]
    p3 = [e for e in events if e.get("severity") == "P3"]

    def _send():
        payload = json.dumps({
            "type":    "weekly_digest",
            "week_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "project": os.path.basename(os.getcwd()),
            "summary": {"p1": len(p1), "p2": len(p2), "p3": len(p3), "total": len(events)},
            "events":  events,
            "to":      inbox,
            "subject": f"[WEEKLY] Raven Guard — {len(events)} events — {os.path.basename(os.getcwd())}"
        }).encode()
        if webhook:
            req = urllib.request.Request(
                webhook, data=payload,
                headers={"Content-Type":"application/json","X-Source":"raven-guard"}
            )
            urllib.request.urlopen(req, timeout=5)
    safe(_send)

    # Clear digest after sending
    safe(lambda: open(digest_path, "w").write(""))
    sys.exit(0)

if __name__ == "__main__":
    main()
