#!/usr/bin/env python3
"""Ask for the TypeSafe Jev API key and store it outside git.

The key is written to .raven/manifest.secrets.json as typesafe_api_key.
That file is gitignored. This script never prints the key.
"""
from __future__ import annotations

import getpass
import json
import os
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

KEY_URL = "https://console.typesafe.ai/keys"
FIELD = "typesafe_api_key"
PLACEHOLDERS = {"", "REPLACE_WITH_TYPESAFE_API_KEY"}


def secrets_path(root: Path | None = None) -> Path:
    root = root or Path(os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    return root / ".raven" / "manifest.secrets.json"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def stored_key(path: Path) -> str:
    value = _load(path).get(FIELD)
    if not isinstance(value, str):
        return ""
    return "" if value.strip() in PLACEHOLDERS else value.strip()


def instructions() -> str:
    return "\n".join(
        [
            "Jev API key is required before Raven can route with System 1.",
            "- Open https://console.typesafe.ai/keys",
            "- Sign in to the TypeSafe console (create an account if you do not have one).",
            "- Create an API key and copy it. TypeSafe calls this TYPESAFE_API_KEY.",
            "- Paste it into the local prompt. It is saved in .raven/manifest.secrets.json and is not committed.",
            "- Run: python3 scripts/ops/jev-key.py --set",
            f"- Key page: {KEY_URL}",
        ]
    )


def save_key(path: Path, key: str) -> None:
    cleaned = key.strip()
    if cleaned in PLACEHOLDERS or len(cleaned) < 8:
        raise SystemExit("jev-key: that value is empty or too short; nothing saved")
    data = _load(path)
    data[FIELD] = cleaned
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    print(f"jev-key: saved {FIELD} in {path} (gitignored, chmod 600)")


def ensure_secrets_file(path: Path) -> None:
    """Create the gitignored secrets file from the template if it is missing."""
    if path.is_file():
        return
    template = path.with_name("manifest.secrets.json.template")
    path.parent.mkdir(parents=True, exist_ok=True)
    if template.is_file():
        path.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        path.write_text(
            json.dumps({FIELD: "REPLACE_WITH_TYPESAFE_API_KEY"}, indent=2) + "\n",
            encoding="utf-8",
        )
    os.chmod(path, 0o600)


def _page_html(token: str, path: Path) -> bytes:
    shown = path
    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Raven — Jev API key</title>
<style>
  body {{ font: 16px/1.45 system-ui, sans-serif; margin: 2.5rem auto; max-width: 38rem; color: #1c1c1c; }}
  code {{ background: #f2f2f2; padding: 0.1rem 0.3rem; }}
  input[type=password] {{ width: 100%; font: inherit; padding: 0.5rem; box-sizing: border-box; }}
  button {{ margin-top: 0.8rem; font: inherit; padding: 0.45rem 0.9rem; }}
  .ok {{ color: #0b6b2a; }}
</style>
</head>
<body>
<h1>Jev API key</h1>
<p>Raven needs this key before System 1 can route. It stays in the secrets file on this machine and is not committed.</p>
<ul>
  <li>Open <a href="{KEY_URL}">{KEY_URL}</a></li>
  <li>Sign in to the TypeSafe console, or create an account.</li>
  <li>Create an API key and copy it. TypeSafe calls it <code>TYPESAFE_API_KEY</code>.</li>
  <li>Paste it below, or into the file named further down. Do not paste it into chat.</li>
</ul>
<h2>Save here</h2>
<form method="post" action="/save">
  <input type="hidden" name="token" value="{token}">
  <label for="key">API key</label>
  <input id="key" name="key" type="password" autocomplete="off" autofocus>
  <button type="submit">Save</button>
</form>
<h2>Or edit the file</h2>
<ul>
  <li>File: <code>{shown}</code></li>
  <li>Field: <code>{FIELD}</code></li>
  <li>Replace <code>REPLACE_WITH_TYPESAFE_API_KEY</code> with the key, then save the file.</li>
</ul>
</body>
</html>
"""
    return body.encode("utf-8")


def serve_page(path: Path, open_browser: bool = True) -> int:
    """Local page on 127.0.0.1. Stops after a successful save. Never logs the key."""
    ensure_secrets_file(path)
    token = secrets.token_urlsafe(24)
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:
            return

        def _send(self, code: int, content: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self) -> None:
            if self.path.split("?", 1)[0] != "/":
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            self._send(200, _page_html(token, path), "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path.split("?", 1)[0] != "/save":
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > 8192:
                self._send(400, b"bad request", "text/plain; charset=utf-8")
                return
            form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
            if (form.get("token") or [""])[0] != token:
                self._send(403, b"forbidden", "text/plain; charset=utf-8")
                return
            try:
                save_key(path, (form.get("key") or [""])[0])
            except SystemExit:
                self._send(400, b"That value is empty or too short. Nothing was saved.", "text/plain; charset=utf-8")
                return
            self._send(
                200,
                b"<!DOCTYPE html><html><body><p class='ok'>Saved. You can close this tab.</p></body></html>",
                "text/html; charset=utf-8",
            )
            done.set()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    host, port = server.server_address
    url = f"http://{host}:{port}/"
    print(f"jev-key: open {url}", flush=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if open_browser:
        webbrowser.open(url)
    done.wait(timeout=600)
    server.shutdown()
    if not done.is_set():
        print("jev-key: page closed before a key was saved", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = secrets_path()
    if "--file" in args:
        i = args.index("--file")
        path = Path(args[i + 1])
    if "--page" in args:
        return serve_page(path, open_browser="--no-open" not in args)
    if "--set" in args:
        typed = getpass.getpass("Paste the Jev API key (input hidden): ")
        save_key(path, typed)
        return 0
    if "--save-env" in args:
        save_key(path, os.environ.get("TYPESAFE_API_KEY") or "")
        return 0
    if stored_key(path) or (os.environ.get("TYPESAFE_API_KEY") or "").strip():
        if not stored_key(path):
            print(
                "Jev API key is in the environment only. "
                "Run: python3 scripts/ops/jev-key.py --save-env"
            )
        return 0
    print(instructions())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
