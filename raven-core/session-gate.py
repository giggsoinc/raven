#!/usr/bin/env python3
"""
session-gate.py — Raven Stop hook v1.0
Fires at every session end (Stop event).
Shows: uncommitted git changes, recent commits, open Raven observations.
Non-blocking — systemMessage only.
"""
import sys
import json
import subprocess
import pathlib
import os


def git_summary() -> list[str]:
    """Return git status and recent log lines, empty list if not a git repo."""
    parts: list[str] = []
    cwd = os.getcwd()
    try:
        status = subprocess.check_output(
            ["git", "status", "--short"],
            stderr=subprocess.DEVNULL,
            cwd=cwd,
        ).decode().strip()
        if status:
            parts.append(f"📂 Uncommitted changes:\n{status}")

        log = subprocess.check_output(
            ["git", "log", "--oneline", "-5"],
            stderr=subprocess.DEVNULL,
            cwd=cwd,
        ).decode().strip()
        if log:
            parts.append(f"📋 Recent commits:\n{log}")
    except Exception:
        pass
    return parts


def open_observations() -> list[str]:
    """Count open Raven memory items in .raven/memory/."""
    parts: list[str] = []
    try:
        memory_dir = pathlib.Path(os.getcwd()) / ".raven" / "memory"
        if memory_dir.exists():
            count = sum(
                1
                for f in memory_dir.glob("*.md")
                if "status: open" in f.read_text(errors="ignore")
            )
            if count > 0:
                parts.append(
                    f"📋 {count} open observation(s) in .raven/memory/ "
                    f"— run /raven-harden when ready"
                )
    except Exception:
        pass
    return parts


def metrics_summary() -> list[str]:
    """Read session metrics and format summary line."""
    parts: list[str] = []
    try:
        session_file = pathlib.Path(os.getcwd()) / ".raven" / ".model-session.json"
        if session_file.exists():
            metrics = json.loads(session_file.read_text())
            total = metrics.get("total", {})
            raven_calls = metrics.get("raven_code", {}).get("calls", 0)
            user_calls = metrics.get("user_work", {}).get("calls", 0)
            tokens = total.get("tokens", 0)
            cost = total.get("cost_usd", 0)

            if tokens > 0:
                # Format token count with commas
                token_str = f"{tokens:,}" if tokens > 999 else str(tokens)
                cost_str = f"${cost:.2f}"
                calls_str = f"{raven_calls} raven / {user_calls} user"
                parts.append(
                    f"📊 Session: {token_str} tok · {cost_str} · {calls_str} calls"
                )
                dashboard_path = pathlib.Path.home() / "RavenVault" / "dashboard.html"
                if dashboard_path.exists():
                    parts.append(
                        f"   📈 Dashboard: {dashboard_path} "
                        f"(refresh with `raven dashboard --refresh`)"
                    )
    except Exception:
        pass
    return parts


def main() -> None:
    """Collect session-end signals and emit systemMessage if anything to report."""
    sections: list[str] = []
    sections.extend(metrics_summary())
    sections.extend(git_summary())
    sections.extend(open_observations())

    if sections:
        message = "🪶 Raven — Session Gate\n\n" + "\n\n".join(sections)
        print(json.dumps({"systemMessage": message}))

    sys.exit(0)


if __name__ == "__main__":
    main()
