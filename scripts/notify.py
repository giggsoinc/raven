#!/usr/bin/env python3
"""
Raven — Notification Sender
SMTP email + Slack webhook delivery for governance events.

Triggers (from CLI):
  --event=commit         Pre-commit gate passed
  --event=block          Pre-commit gate blocked (secret/CVE/schema)
  --event=override       Guard override invoked
  --event=token-warning  Token threshold crossed (75/90)
  --event=incident       P1/P2 escalation

Config: .raven/manifest.secrets.json (gitignored).
If secrets file missing → dry-run mode (prints what would have sent).
Never raises — always exit 0 so pre-commit hook is not blocked.

Local-only. No telemetry.
"""
import argparse
import json
import os
import smtplib
import socket
import ssl
import sys
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime, timezone

SECRETS_PATH = Path(".raven/manifest.secrets.json")
AUDIT_DIR = Path(".raven/audit")


def load_secrets() -> dict:
    """Load SMTP + Slack config. Returns {} if missing or invalid."""
    if not SECRETS_PATH.exists():
        return {}
    try:
        return json.loads(SECRETS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def audit(event: str, channel: str, status: str, detail: str = "") -> None:
    """Append a record of every send attempt — never raises."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "event":   "notify",
            "trigger": event,
            "channel": channel,
            "status":  status,
            "detail":  detail[:300],
            "host":    socket.gethostname(),
            "user":    os.environ.get("USER", "unknown"),
            "project": Path.cwd().name,
        }
        with open(AUDIT_DIR / f"{date_str}.log", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def render_subject(event: str, project: str) -> str:
    icons = {
        "commit":        "✅",
        "block":         "🚨",
        "override":      "⚠️",
        "token-warning": "💰",
        "incident":      "🔥",
    }
    icon = icons.get(event, "🪶")
    return f"{icon} Raven [{project}] — {event}"


def render_body(event: str, payload: dict) -> str:
    lines = [
        f"Raven governance event: {event}",
        f"Timestamp:  {datetime.now(timezone.utc).isoformat()}",
        f"Project:    {payload.get('project', 'unknown')}",
        f"User:       {payload.get('user', 'unknown')}",
        f"Branch:     {payload.get('branch', 'unknown')}",
        "",
        "--- Detail ---",
        payload.get("detail", "(no detail provided)"),
        "",
        "--- Files ---",
        payload.get("files", "(none)"),
        "",
        "Sent by Raven notify.py — local-only, no telemetry.",
    ]
    return "\n".join(lines)


def send_email(secrets: dict, event: str, payload: dict) -> tuple[bool, str]:
    """Returns (success, message). Never raises."""
    smtp = secrets.get("smtp") or {}
    recipients_map = secrets.get("recipients") or {}
    recipients = recipients_map.get(event) or recipients_map.get("default") or []

    if not (smtp.get("host") and smtp.get("user") and smtp.get("pass") and recipients):
        return (False, "SMTP config or recipients missing")

    msg = MIMEMultipart()
    msg["From"]    = smtp.get("from", smtp["user"])
    msg["To"]      = ", ".join(recipients)
    msg["Subject"] = render_subject(event, payload.get("project", "raven"))
    msg.attach(MIMEText(render_body(event, payload), "plain"))

    try:
        port = int(smtp.get("port", 587))
        ctx  = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(smtp["host"], port, context=ctx, timeout=10) as s:
                s.login(smtp["user"], smtp["pass"])
                s.send_message(msg)
        else:
            with smtplib.SMTP(smtp["host"], port, timeout=10) as s:
                s.starttls(context=ctx)
                s.login(smtp["user"], smtp["pass"])
                s.send_message(msg)
        return (True, f"sent to {len(recipients)} recipient(s)")
    except Exception as e:
        return (False, f"SMTP error: {type(e).__name__}: {e}")


def send_slack(secrets: dict, event: str, payload: dict) -> tuple[bool, str]:
    """Returns (success, message). Never raises."""
    webhook = secrets.get("slack_webhook")
    if not webhook:
        return (False, "no slack_webhook configured")

    body = {
        "text": f"{render_subject(event, payload.get('project', 'raven'))}\n```\n{render_body(event, payload)}\n```"
    }
    try:
        req = urllib.request.Request(
            webhook,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return (r.status == 200, f"slack status {r.status}")
    except Exception as e:
        return (False, f"slack error: {type(e).__name__}: {e}")


def dry_run(event: str, payload: dict) -> None:
    """Print what would have been sent when secrets are missing."""
    print("─" * 60, file=sys.stderr)
    print(f"🪶 Raven notify — DRY RUN (no .raven/manifest.secrets.json)", file=sys.stderr)
    print("─" * 60, file=sys.stderr)
    print(f"Subject: {render_subject(event, payload.get('project', 'raven'))}", file=sys.stderr)
    print("Body:", file=sys.stderr)
    print(render_body(event, payload), file=sys.stderr)
    print("─" * 60, file=sys.stderr)
    print("To enable real sending: create .raven/manifest.secrets.json", file=sys.stderr)
    print("See .raven/manifest.secrets.json.template", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Raven notification sender")
    parser.add_argument("--event", required=True,
                        choices=["commit", "block", "override", "token-warning", "incident"])
    parser.add_argument("--detail",  default="", help="Free-text detail line")
    parser.add_argument("--files",   default="", help="Affected files (newline-joined)")
    parser.add_argument("--project", default=Path.cwd().name)
    parser.add_argument("--branch",  default=os.environ.get("GIT_BRANCH", ""))
    parser.add_argument("--user",    default=os.environ.get("USER", "unknown"))
    parser.add_argument("--test",    action="store_true",
                        help="Force a test send (override event-based recipient routing)")
    args = parser.parse_args()

    payload = {
        "project": args.project,
        "branch":  args.branch,
        "user":    args.user,
        "detail":  args.detail or ("Test notification — verifying SMTP + Slack work." if args.test else ""),
        "files":   args.files,
    }

    # Resolve git branch if not provided
    if not payload["branch"]:
        try:
            import subprocess
            r = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                               capture_output=True, text=True, timeout=2)
            payload["branch"] = r.stdout.strip() or "unknown"
        except Exception:
            payload["branch"] = "unknown"

    secrets = load_secrets()
    if not secrets:
        dry_run(args.event, payload)
        audit(args.event, "dry-run", "no-secrets", "manifest.secrets.json missing")
        return

    # Email
    ok_email, msg_email = send_email(secrets, args.event, payload)
    audit(args.event, "email", "sent" if ok_email else "failed", msg_email)
    print(f"📧 email: {'✓' if ok_email else '✗'} {msg_email}", file=sys.stderr)

    # Slack
    ok_slack, msg_slack = send_slack(secrets, args.event, payload)
    audit(args.event, "slack", "sent" if ok_slack else "failed", msg_slack)
    print(f"💬 slack: {'✓' if ok_slack else '✗'} {msg_slack}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Never block the caller — log and exit clean
        audit("unknown", "fatal", "exception", f"{type(e).__name__}: {e}")
        sys.stderr.write(f"notify.py error (suppressed): {e}\n")
    sys.exit(0)
