#!/usr/bin/env python3
"""Ask for the TypeSafe Jev API key and store it outside git.

The key is written to .raven/manifest.secrets.json as typesafe_api_key.
That file is gitignored. This script never prints the key.
"""
from __future__ import annotations

import datetime
import getpass
import json
import os
import re
import secrets
import sys
import threading
import urllib.error
import urllib.request
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


def project_root(path: Path) -> Path:
    """Secrets file lives in <root>/.raven/. Return that root."""
    if path.name == "manifest.secrets.json" and path.parent.name == ".raven":
        return path.parent.parent
    return path


def where_stored(root: Path) -> str:
    secrets_file = root / ".raven" / "manifest.secrets.json"
    models_file = root / ".model.env"
    return "\n".join(
        [
            f"API keys are stored in {secrets_file}",
            "That file is gitignored and saved as mode 600. The key value is never printed.",
            f"Model names, not keys, are stored in {models_file} (gitignored).",
        ]
    )


def setup_marker(root: Path) -> Path:
    return root / ".raven" / "setup-choice.json"


def setup_done(root: Path) -> bool:
    return setup_marker(root).is_file()


def log_jev(event: str, typesafe: str = "", preference: str = "") -> None:
    """Append one Jev event. The API key is never included."""
    vault = Path(os.environ.get("RAVEN_VAULT", str(Path.home() / "RavenVault")))
    path = vault / "jev-calls.jsonl"
    rec = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "typesafe": typesafe,
        "preference": preference,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError:
        return


def mark_setup(root: Path, typesafe: str, preference: str) -> None:
    path = setup_marker(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"typesafe": typesafe, "preference": preference}, indent=2) + "\n",
        encoding="utf-8",
    )


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=1.5) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data if isinstance(data, dict) else {}


def detect_ollama() -> list[str]:
    """Model names from a local Ollama server. Empty when it is not running."""
    try:
        data = _get_json("http://127.0.0.1:11434/api/tags")
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []
    names = []
    for item in data.get("models") or []:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return names


def detect_llamacpp() -> list[str]:
    """Model ids from a local LlamaCPP server on port 8080."""
    try:
        data = _get_json("http://127.0.0.1:8080/v1/models")
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []
    names = []
    for item in data.get("data") or []:
        if isinstance(item, dict) and item.get("id"):
            names.append(str(item["id"]))
    return names


def write_routing(root: Path, flash: str, thinking: str) -> Path:
    """Set SIMPLE to flash and MEDIUM/COMPLEX to thinking in .model.env."""
    path = root / ".model.env"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    block_lines = [
        "[routing]",
        f"SIMPLE={flash}",
        f"MEDIUM={thinking}",
        f"COMPLEX={thinking}",
    ]
    lines = existing.splitlines()
    start = None
    end = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "[routing]":
            start = i
            continue
        if start is not None and i > start and line.strip().startswith("["):
            end = i
            break
    if start is None:
        body = existing.rstrip()
        prefix = (body + "\n\n") if body else ""
        path.write_text(prefix + "\n".join(block_lines) + "\n", encoding="utf-8")
    else:
        lines[start:end] = block_lines
        path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def _ask_yn(question: str) -> bool:
    while True:
        answer = input(question + " [y/n] ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Enter y or n.")


def _preference() -> str:
    print("What do you prefer for models?")
    print("  1) Autodetect Ollama and LlamaCPP, then use them for flash and thinking")
    print("  2) Add another model and its API key")
    print("  3) Keep Raven's current default routing")
    while True:
        answer = input("Choose 1, 2, or 3: ").strip()
        if answer in {"1", "2", "3"}:
            return answer
        print("Enter 1, 2, or 3.")


def _apply_local(root: Path) -> str:
    ollama = detect_ollama()
    llamacpp = detect_llamacpp()
    print(f"Ollama at 127.0.0.1:11434: {', '.join(ollama) if ollama else 'not running'}")
    print(f"LlamaCPP at 127.0.0.1:8080: {', '.join(llamacpp) if llamacpp else 'not running'}")
    if ollama and llamacpp:
        flash = f"ollama/{ollama[0]}"
        thinking = f"llamacpp/{llamacpp[0]}"
    elif ollama:
        flash = thinking = f"ollama/{ollama[0]}"
    elif llamacpp:
        flash = thinking = f"llamacpp/{llamacpp[0]}"
    else:
        print("No local server found. Raven keeps its current default routing.")
        return "defaults"
    path = write_routing(root, flash, thinking)
    print(f"Flash (SIMPLE) = {flash}")
    print(f"Thinking (MEDIUM and COMPLEX) = {thinking}")
    print(f"Model names saved in {path}")
    return "local"


def _field_for_model(model_id: str) -> str:
    provider = model_id.split("/", 1)[0].strip().lower()
    provider = re.sub(r"[^a-z0-9]+", "_", provider).strip("_") or "provider"
    if provider == "typesafe":
        return FIELD
    return f"{provider}_api_key"


def _apply_custom(root: Path, secrets_file: Path) -> str:
    model_id = input("Model id (example groq/llama-3.3-70b): ").strip()
    if not model_id:
        print("No model id. Raven keeps its current default routing.")
        return "defaults"
    field = _field_for_model(model_id)
    print("Before you paste the key:")
    print(where_stored(root))
    print(f"This key will be saved as {field}.")
    typed = getpass.getpass("Paste the API key (input hidden): ")
    save_field(secrets_file, field, typed)
    path = write_routing(root, model_id, model_id)
    print("After the save:")
    print(where_stored(root))
    print(f"{field} is in {secrets_file}. The value was not printed.")
    print(f"Flash and thinking both use {model_id}, recorded in {path}.")
    return "custom"


def save_field(path: Path, field: str, key: str) -> None:
    cleaned = key.strip()
    if cleaned in PLACEHOLDERS or len(cleaned) < 8:
        raise SystemExit("jev-key: that value is empty or too short; nothing saved")
    if not re.fullmatch(r"[A-Za-z0-9_]+", field):
        raise SystemExit("jev-key: key field name must be letters, numbers, and underscore")
    data = _load(path)
    data[field] = cleaned
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    print(f"jev-key: saved {field} in {path} (gitignored, chmod 600)")


def offer(root: Path) -> int:
    """Ask for a TypeSafe key, then local or custom models. Routing still runs if they say no."""
    secrets_file = secrets_path(root)
    if not sys.stdin.isatty():
        return 0
    print("Before you enter a key:")
    print(where_stored(root))
    has_key = _ask_yn("Do you have a Jev TypeSafe key?")
    if has_key:
        print("Before you paste the TypeSafe key:")
        print(where_stored(root))
        print(f"Create one at {KEY_URL} if you need a new key. TypeSafe calls it TYPESAFE_API_KEY.")
        typed = getpass.getpass("Paste the Jev TypeSafe key (input hidden): ")
        save_field(secrets_file, FIELD, typed)
        print("After the save:")
        print(where_stored(root))
        print(f"{FIELD} is in {secrets_file}. The value was not printed.")
        typesafe = "yes"
    else:
        print("No TypeSafe key. Raven keeps its default routing.")
        typesafe = "no"
    choice = _preference()
    if choice == "1":
        preference = _apply_local(root)
    elif choice == "2":
        preference = _apply_custom(root, secrets_file)
    else:
        print("Raven keeps its current default routing.")
        preference = "defaults"
    mark_setup(root, typesafe, preference)
    log_jev("setup", typesafe, preference)
    print("After this step:")
    print(where_stored(root))
    return 0


def save_key(path: Path, key: str) -> None:
    save_field(path, FIELD, key)


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
    root = project_root(path)
    if "--page" in args:
        return serve_page(path, open_browser="--no-open" not in args)
    if "--set" in args:
        print("Before you paste the key:")
        print(where_stored(root))
        typed = getpass.getpass("Paste the Jev TypeSafe key (input hidden): ")
        save_key(path, typed)
        log_jev("set", "yes", "")
        print("After the save:")
        print(where_stored(root))
        return 0
    if "--save-env" in args:
        print("Before the save:")
        print(where_stored(root))
        save_key(path, os.environ.get("TYPESAFE_API_KEY") or "")
        log_jev("save-env", "yes", "")
        print("After the save:")
        print(where_stored(root))
        return 0
    if "--check" in args:
        if setup_done(root) or not sys.stdin.isatty():
            return 0
        return offer(root)
    if setup_done(root):
        return 0
    return offer(root)


if __name__ == "__main__":
    raise SystemExit(main())
