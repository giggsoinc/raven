#!/usr/bin/env python3
"""Ask for the TypeSafe Jev API key and store it outside git.

The key is written to .raven/manifest.secrets.json as typesafe_api_key.
That file is gitignored. This script never prints the key.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    path = secrets_path()
    if "--file" in args:
        i = args.index("--file")
        path = Path(args[i + 1])
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
