#!/usr/bin/env python3
# Raven Guard — Notifier
# PagerDuty (P1) + Prism7 email (P1/P2/P3) + weekly digest
# NEVER errors. NEVER blocks. Silent if not configured.
# Usage: python3 guard-notify.py --severity P1 --detail "Force push on main"

import argparse, json, os, sys, urllib.request
from datetime import datetime, timezone

def safe(fn):
    try: return fn()
    except: return None

def load_secrets():
    return safe(lambda: json.load(open(".raven/manifest.secrets.json"))) or {}

def notify_pagerduty(detail, secrets):
    """P1 only. Silent if not configured."""
    def _notify():
        key = secrets.get("guard", {}).get("pagerduty_key", "")
        if not key:
            return
        payload = json.dumps({
            "routing_key":  key,
            "event_action": "trigger",
            "payload": {
                "summary":   f"[Raven Guard P1] {detail}",
                "severity":  "critical",
                "source":    os.path.basename(os.getcwd()),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }).encode()
        req = urllib.request.Request(
            "https://events.pagerduty.com/v2/enqueue",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        urllib.request.urlopen(req, timeout=5)
    safe(_notify)

def notify_prism7(severity, detail, secrets):
    """Email Prism7 via webhook or SMTP. Silent if not configured."""
    def _notify():
        webhook = secrets.get("guard", {}).get("webhook_url", "")
        inbox   = secrets.get("approvals", {}).get("shared_inbox", "")
        if not webhook and not inbox:
            return

        subject = f"[{severity}-RAVEN-GUARD] {detail[:80]}"
        payload = json.dumps({
            "severity": severity,
            "detail":   detail,
            "project":  os.path.basename(os.getcwd()),
            "ts":       datetime.now(timezone.utc).isoformat(),
            "subject":  subject,
            "to":       inbox
        }).encode()

        if webhook:
            req = urllib.request.Request(
                webhook, data=payload,
                headers={"Content-Type": "application/json",
                         "X-Source": "raven-guard"}
            )
            urllib.request.urlopen(req, timeout=5)
    safe(_notify)

def append_digest(severity, detail, secrets):
    """Append to weekly digest file. Silent if not configured."""
    def _append():
        if not secrets.get("guard", {}).get("weekly_digest", False):
            return
        os.makedirs(".raven/guard", exist_ok=True)
        with open(".raven/guard/digest.log", "a") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "severity": severity, "detail": detail,
                "project": os.path.basename(os.getcwd())
            }) + "\n")
    safe(_append)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--severity", required=True)
    p.add_argument("--detail",   required=True)
    args = p.parse_args()

    secrets = load_secrets()

    if args.severity == "P1":
        notify_pagerduty(args.detail, secrets)
        notify_prism7("P1", args.detail, secrets)

    elif args.severity == "P2":
        notify_prism7("P2", args.detail, secrets)
        append_digest("P2", args.detail, secrets)

    else:
        append_digest("P3", args.detail, secrets)

    sys.exit(0)

if __name__ == "__main__":
    main()
