#!/usr/bin/env python3
"""
raven-dashboard.py — CLI wrapper for dashboard visualization.
Regenerates metrics from .raven/ and ~/RavenVault/ sources, renders HTML.
Subcommands:
  raven dashboard           → regenerate + print path
  raven dashboard --open    → regenerate + ensure server + open http://127.0.0.1:9787
  raven dashboard --json    → regenerate + dump JSON
  raven dashboard --refresh → regenerate + print summary
  raven dashboard --serve   → launch local HTTP server on 127.0.0.1:9787
"""
import argparse
import json
import os
import pathlib
import socket
import subprocess
import sys
import time
import webbrowser

_OPS = pathlib.Path(__file__).resolve().parent
_SCRIPTS = _OPS.parent
REPO_ROOT = _SCRIPTS.parent
DASHBOARD_SCRIPT = _SCRIPTS / "dashboard.py"
DASHBOARD_SERVER = _OPS / "dashboard-server.py"
DASHBOARD_HTML = pathlib.Path.home() / "RavenVault" / "dashboard" / "raven-dashboard.html"
PORT = 9787


def _project_name() -> str:
    man = REPO_ROOT / ".raven" / "manifest.json"
    try:
        name = json.loads(man.read_text(encoding="utf-8")).get("project")
        if name:
            return str(name)
    except (OSError, json.JSONDecodeError, TypeError):
        pass
    return REPO_ROOT.name


def live_url() -> str:
    return f"http://127.0.0.1:{PORT}#{_project_name()}"


def server_up(port: int = PORT) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return True
    except OSError:
        return False


def ensure_server(port: int = PORT) -> bool:
    if server_up(port):
        return True
    if not DASHBOARD_SERVER.is_file():
        return False
    try:
        subprocess.Popen(
            [sys.executable, str(DASHBOARD_SERVER), "--port", str(port)],
            cwd=str(REPO_ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        return False
    for _ in range(25):
        time.sleep(0.12)
        if server_up(port):
            return True
    return server_up(port)


def run_dashboard(mode: str = "default") -> dict:
    """Run dashboard.py and capture output."""
    env = dict(os.environ)
    env["RAVEN_DASHBOARD_NO_OPEN"] = "1"
    env.setdefault("CLAUDE_PROJECT_DIR", str(REPO_ROOT))
    try:
        result = subprocess.run(
            [sys.executable, str(DASHBOARD_SCRIPT), "--html"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
            env=env,
        )
        if result.returncode != 0:
            print(f"Error: dashboard.py failed: {result.stderr}", file=sys.stderr)
            return {}
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"html_generated": True}
    except Exception as e:
        print(f"Error: Failed to run dashboard.py: {e}", file=sys.stderr)
        return {}


def print_summary(data: dict) -> None:
    """Print a nicely formatted summary."""
    if not data:
        print("❌ No metrics available yet")
        return
    sessions = data.get("sessions", 0)
    tokens = data.get("tokens", 0)
    cost = data.get("cost_usd", 0)
    print(
        f"📊 Raven Metrics (last 30 days)\n"
        f"   Sessions: {sessions}\n"
        f"   Tokens: {tokens:,}\n"
        f"   Cost: ${cost:.2f}\n"
        + (f"   Avg/session: ${cost/sessions:.3f}" if sessions > 0 else "   Avg/session: $0.000")
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Raven Dashboard — view metrics and usage")
    parser.add_argument("--open", action="store_true", help="Open live dashboard in browser")
    parser.add_argument("--json", action="store_true", help="Output raw JSON metrics")
    parser.add_argument("--refresh", action="store_true", help="Refresh and print console summary")
    parser.add_argument("--serve", action="store_true", help="Start local HTTP server (foreground)")
    args = parser.parse_args()

    data = run_dashboard()

    if args.json:
        print(json.dumps(data, indent=2))
    elif args.serve:
        if not DASHBOARD_SERVER.is_file():
            print("Error: dashboard-server.py not found", file=sys.stderr)
            sys.exit(1)
        print(f"🚀 Launching dashboard server on 127.0.0.1:{PORT}...")
        print(f"   Open: {live_url()}")
        print("   Press Ctrl+C to stop")
        subprocess.run([sys.executable, str(DASHBOARD_SERVER), "--port", str(PORT)], cwd=str(REPO_ROOT))
    elif args.open:
        up = ensure_server()
        url = live_url() if up else (
            DASHBOARD_HTML.resolve().as_uri() if DASHBOARD_HTML.exists() else live_url()
        )
        print(f"📖 Opening dashboard: {url}")
        webbrowser.open(url)
        if not up:
            print("⚠️  Live server did not start — opened file:// (Refresh needs http://127.0.0.1:9787)")
    elif args.refresh:
        print_summary(data)
        print(f"📈 Live: {live_url()}")
        if DASHBOARD_HTML.exists():
            print(f"📈 File: {DASHBOARD_HTML}")
    else:
        if DASHBOARD_HTML.exists():
            print(f"📊 Dashboard: {DASHBOARD_HTML}")
            print(f"📈 Live: {live_url()}")
            print_summary(data)
        else:
            print("⚠️  Dashboard not found yet. Run a Claude session first.")


if __name__ == "__main__":
    main()
