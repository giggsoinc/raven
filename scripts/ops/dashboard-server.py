#!/usr/bin/env python3
"""
dashboard-server.py — Local HTTP server for live dashboard refresh.
Runs on 127.0.0.1:9787 (local-only, no auth required).
Endpoints:
  GET /           → serve dashboard.html
  GET /refresh    → regenerate metrics, respond with new HTML fragment or JSON
  GET /metrics.json → raw metrics dict
Usage: python3 dashboard-server.py [--port 9787]
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
from io import StringIO

_SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
DASHBOARD_SCRIPT = _SCRIPTS / "dashboard.py"
XRAY_SCRIPT = _SCRIPTS / "code-xray.py"
REPO_ROOT = _SCRIPTS.parent
DASHBOARD_HTML = pathlib.Path.home() / "RavenVault" / "dashboard" / "raven-dashboard.html"
PORT = 9787


def _live_head(repo: pathlib.Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _baked_head(repo: pathlib.Path) -> str:
    path = repo / ".raven" / "code-xray.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return str((data.get("okf") or {}).get("git_head") or "")
    except Exception:
        return ""


def rebake_xray_if_drifted(repo: pathlib.Path | None = None) -> dict:
    """Force xray --html when live HEAD ≠ baked okf.git_head."""
    root = repo or REPO_ROOT
    live = _live_head(root)
    baked = _baked_head(root)
    drifted = bool(live) and (not baked or baked != live)
    if not drifted:
        return {"ok": True, "rebaked": False, "live_head": live, "baked_head": baked}
    if not XRAY_SCRIPT.is_file():
        return {"ok": False, "rebaked": False, "error": "code-xray.py missing", "live_head": live}
    env = dict(os.environ)
    env["RAVEN_DASHBOARD_NO_OPEN"] = "1"
    env["CLAUDE_PROJECT_DIR"] = str(root)
    try:
        result = subprocess.run(
            [sys.executable, str(XRAY_SCRIPT), "--html"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(root),
            env=env,
        )
        if result.returncode != 0:
            return {
                "ok": False,
                "rebaked": False,
                "error": (result.stderr or result.stdout or "")[-800],
                "live_head": live,
            }
        return {"ok": True, "rebaked": True, "live_head": live, "baked_head": live}
    except Exception as e:
        return {"ok": False, "rebaked": False, "error": str(e), "live_head": live}


def run_dashboard_script() -> dict:
    """Rebuild raven-dashboard.html; rebake OKF when HEAD drifted."""
    env = dict(os.environ)
    env["RAVEN_DASHBOARD_NO_OPEN"] = "1"
    env.setdefault("CLAUDE_PROJECT_DIR", str(REPO_ROOT))
    xray_info = rebake_xray_if_drifted(REPO_ROOT)
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
            return {
                "ok": False,
                "error": (result.stderr or result.stdout or "")[-800],
                "xray": xray_info,
            }
        return {
            "ok": True,
            "html_generated": True,
            "xray": xray_info,
            "live_head": xray_info.get("live_head") or _live_head(REPO_ROOT),
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "xray": xray_info}


def render_html_with_refresh() -> str:
    """Serve the dashboard HTML with a refresh bar injected."""
    if not DASHBOARD_HTML.exists():
        return "<h1>Dashboard not found</h1>"

    html = DASHBOARD_HTML.read_text(errors="ignore")

    # Inject refresh bar at the top
    refresh_bar = """
    <div style="background: #2d3748; color: #white; padding: 12px 20px;
                display: flex; justify-content: space-between; align-items: center;
                font-family: monospace; font-size: 14px;">
        <span>🔄 Dashboard Server (auto-refresh available)</span>
        <button onclick="location.reload()" style="padding: 6px 12px; background: #4299e1;
                color: white; border: none; border-radius: 4px; cursor: pointer;">
            Refresh
        </button>
    </div>
    <script>
    // Auto-refresh every 30 seconds if enabled
    if (localStorage.getItem('auto-refresh') === 'true') {
        setInterval(() => location.reload(), 30000);
    }
    </script>
    """

    # Insert after opening body tag
    html = html.replace("<body>", f"<body>{refresh_bar}", 1)
    return html


VAULT_DASH = pathlib.Path.home() / "RavenVault" / "dashboard"
if str(_SCRIPTS / "dashboard") not in sys.path:
    sys.path.insert(0, str(_SCRIPTS / "dashboard"))


def safe_repo_file(root: str, rel: str):
    """Absolute file under home + git root. None if escape or missing."""
    if not root or not rel:
        return None
    try:
        root_p = pathlib.Path(root).expanduser().resolve()
        home = pathlib.Path.home().resolve()
        if not str(root_p).startswith(str(home)):
            return None
        if not root_p.is_dir():
            return None
        rel_p = pathlib.Path(str(rel).replace("\\", "/").lstrip("/"))
        if ".." in rel_p.parts or rel_p.is_absolute():
            return None
        dest = (root_p / rel_p).resolve()
        prefix = str(root_p) + os.sep
        if not (str(dest).startswith(prefix) or dest == root_p):
            return None
        if not dest.is_file():
            return None
        return dest
    except (OSError, RuntimeError, ValueError):
        return None


def open_local_file(dest: pathlib.Path, app: str = "") -> dict:
    """macOS `open` so the file leaves the browser sandbox."""
    try:
        if app in ("code", "vscode"):
            cmd = ["open", "-a", "Visual Studio Code", str(dest)]
        elif app in ("cursor",):
            cmd = ["open", "-a", "Cursor", str(dest)]
        else:
            cmd = ["open", str(dest)]
        subprocess.run(cmd, check=False, capture_output=True, timeout=8)
        return {"ok": True, "path": str(dest)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler for dashboard server."""

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_POST(self) -> None:
        path = urllib.parse.urlparse(self.path).path
        if path != "/api/settings":
            self.send_response(404)
            self.end_headers()
            return
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            patch = json.loads(raw.decode() or "{}")
            from dash_settings import save
            out = save(patch)
            body = json.dumps({"ok": True, "settings": out}).encode()
            self.send_response(200)
        except Exception as e:
            body = json.dumps({"ok": False, "error": str(e)}).encode()
            self.send_response(400)
        self.send_header("Content-type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Handle GET requests."""
        path = urllib.parse.urlparse(self.path).path

        if path in ("/", "/raven-dashboard.html"):
            target = VAULT_DASH / "raven-dashboard.html"
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(target.read_bytes() if target.is_file() else b"missing raven-dashboard.html")
            return

        if path == "/api/settings":
            from dash_settings import public_view
            body = json.dumps(public_view()).encode()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/open":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            dest = safe_repo_file((qs.get("root") or [""])[0], (qs.get("rel") or [""])[0])
            if not dest:
                data = {"ok": False, "error": "file not found or path not allowed"}
                self.send_response(400)
            else:
                data = open_local_file(dest, (qs.get("app") or [""])[0])
                self.send_response(200 if data.get("ok") else 400)
            body = json.dumps(data).encode()
            self.send_header("Content-type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/file":
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            dest = safe_repo_file((qs.get("root") or [""])[0], (qs.get("rel") or [""])[0])
            if not dest:
                data = {"ok": False, "error": "file not found or path not allowed"}
                code = 400
            else:
                try:
                    text = dest.read_text(encoding="utf-8", errors="replace")
                    lines = text.splitlines()
                    data = {
                        "ok": True,
                        "path": str(dest),
                        "text": "\n".join(lines[:200]),
                        "truncated": len(lines) > 200,
                    }
                    code = 200
                except OSError as e:
                    data = {"ok": False, "error": str(e)}
                    code = 400
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/api/run-costs":
            script = pathlib.Path(__file__).resolve().parents[1] / "session" / "run_costs.py"
            try:
                subprocess.run(
                    [sys.executable, str(script)],
                    timeout=12,
                    capture_output=True,
                    env=dict(os.environ),
                )
                data = {"ok": True}
            except Exception as e:
                data = {"ok": False, "error": str(e)}
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/refresh":
            data = run_dashboard_script()
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._cors()
            self.end_headers()
            self.wfile.write(json.dumps(data).encode())
            return

        rel = path.lstrip("/")
        fpath = (VAULT_DASH / rel).resolve()
        if str(fpath).startswith(str(VAULT_DASH.resolve())) and fpath.is_file():
            self.send_response(200)
            self._cors()
            self.end_headers()
            self.wfile.write(fpath.read_bytes())
            return
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not found")

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging."""
        pass


def main() -> None:
    """Start the dashboard server."""
    parser = argparse.ArgumentParser(description="Raven Dashboard Server")
    parser.add_argument("--port", type=int, default=9787, help="Port to listen on")
    args = parser.parse_args()

    server_address = ("127.0.0.1", args.port)
    httpd = http.server.HTTPServer(server_address, DashboardRequestHandler)

    print(f"🚀 Dashboard server running on http://127.0.0.1:{args.port}")
    print(f"   Endpoints:")
    print(f"   • GET /           → serve dashboard.html with refresh bar")
    print(f"   • GET /refresh    → regenerate + return JSON")
    print(f"   • GET /metrics.json → raw metrics")
    print(f"")
    print(f"   Press Ctrl+C to stop")
    print(f"")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ Server stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
