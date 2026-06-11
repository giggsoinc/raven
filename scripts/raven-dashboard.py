#!/usr/bin/env python3
"""
raven-dashboard.py — CLI wrapper for dashboard visualization.
Regenerates metrics from .raven/ and ~/RavenVault/ sources, renders HTML.
Subcommands:
  raven dashboard           → regenerate + print path
  raven dashboard --open    → regenerate + open browser
  raven dashboard --json    → regenerate + dump JSON
  raven dashboard --refresh → regenerate + print summary
  raven dashboard --serve   → launch local HTTP server on 127.0.0.1:9787
"""
import subprocess
import sys
import pathlib
import json
import argparse
import webbrowser
import os

DASHBOARD_SCRIPT = pathlib.Path(__file__).parent / "dashboard.py"
DASHBOARD_HTML = pathlib.Path.home() / "RavenVault" / "dashboard.html"


def run_dashboard(mode: str = "default") -> dict:
    """Run dashboard.py and capture output."""
    try:
        result = subprocess.run(
            ["python3", str(DASHBOARD_SCRIPT), "--html"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            print(f"Error: dashboard.py failed: {result.stderr}", file=sys.stderr)
            return {}

        # Try to parse JSON from stdout if it contains it
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            # dashboard.py might not output JSON, just the HTML
            return {"html_generated": True}
    except Exception as e:
        print(f"Error: Failed to run dashboard.py: {e}", file=sys.stderr)
        return {}


def print_summary(data: dict) -> None:
    """Print a nicely formatted summary."""
    if not data:
        print("❌ No metrics available yet")
        return

    # Extract from metrics
    sessions = data.get("sessions", 0)
    tokens = data.get("tokens", 0)
    cost = data.get("cost_usd", 0)

    print(
        f"📊 Raven Metrics (last 30 days)\n"
        f"   Sessions: {sessions}\n"
        f"   Tokens: {tokens:,}\n"
        f"   Cost: ${cost:.2f}\n"
        f"   Avg/session: ${cost/sessions:.3f}" if sessions > 0 else "   Avg/session: $0.000"
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Raven Dashboard — view metrics and usage")
    parser.add_argument(
        "--open", action="store_true", help="Open HTML in default browser"
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON metrics")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh and print console summary",
    )
    parser.add_argument("--serve", action="store_true", help="Start local HTTP server")
    args = parser.parse_args()

    # Run dashboard to regenerate
    data = run_dashboard()

    if args.json:
        print(json.dumps(data, indent=2))
    elif args.serve:
        # Launch dashboard server
        dashboard_server = pathlib.Path(__file__).parent / "dashboard-server.py"
        if dashboard_server.exists():
            print(f"🚀 Launching dashboard server on 127.0.0.1:9787...")
            print(f"   Open: http://127.0.0.1:9787")
            print(f"   Press Ctrl+C to stop")
            subprocess.run(["python3", str(dashboard_server)])
        else:
            print("Error: dashboard-server.py not found", file=sys.stderr)
            sys.exit(1)
    elif args.open:
        if DASHBOARD_HTML.exists():
            print(f"📖 Opening dashboard: {DASHBOARD_HTML}")
            webbrowser.open(f"file://{DASHBOARD_HTML}")
        else:
            print(f"❌ Dashboard not found: {DASHBOARD_HTML}", file=sys.stderr)
            sys.exit(1)
    elif args.refresh:
        print_summary(data)
        if DASHBOARD_HTML.exists():
            print(f"📈 Dashboard: {DASHBOARD_HTML}")
    else:
        # Default: just print the path
        if DASHBOARD_HTML.exists():
            print(f"📊 Dashboard: {DASHBOARD_HTML}")
            print_summary(data)
        else:
            print(f"⚠️  Dashboard not found yet. Run a Claude session first.")


if __name__ == "__main__":
    main()
