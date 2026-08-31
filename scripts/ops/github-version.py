#!/usr/bin/env python3
"""Session-start GitHub version banner. Fail-soft. No auto-upgrade.

Prints: current vs GitHub latest, ask to upgrade if behind, up to 5 bullets.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path

REPO = "giggsoinc/raven"
TIMEOUT = 2.5
UA = "raven-version-check/5.5.6"


def _root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()


def installed_version(root: Path | None = None) -> str:
    root = root or _root()
    for p in (
        root / ".raven" / "raven_version",
        root / "raven-core" / "VERSION",
    ):
        if p.is_file():
            v = p.read_text(encoding="utf-8").strip().split()[0]
            if v:
                return v
    man = root / ".raven" / "manifest.json"
    if man.is_file():
        try:
            data = json.loads(man.read_text(encoding="utf-8"))
            v = str(data.get("raven_version") or data.get("version") or "").strip()
            if v:
                return v
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return "unknown"


def _get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def github_latest_tag() -> str:
    raw = _get(f"https://api.github.com/repos/{REPO}/tags?per_page=5")
    tags = json.loads(raw)
    if not isinstance(tags, list) or not tags:
        raise RuntimeError("no tags")
    name = str(tags[0].get("name") or "")
    return name[1:] if name.startswith("v") else name


def _bullets_from_log(text: str, version: str, limit: int = 5) -> list[str]:
    marker = f"## v{version}"
    idx = text.find(marker)
    if idx < 0:
        idx = 0
    chunk = text[idx:]
    nxt = chunk.find("\n## v", 1)
    if nxt > 0:
        chunk = chunk[:nxt]
    out: list[str] = []
    for ln in chunk.splitlines():
        s = ln.strip()
        if s.startswith("- "):
            out.append(s[2:].strip())
        if len(out) >= limit:
            break
    if len(out) >= limit:
        return out[:limit]
    body = re.sub(r"^#.*$", "", chunk, flags=re.M)
    for sent in re.split(r"(?<=[.!?])\s+", body.replace("\n", " ")):
        sent = sent.strip(" -#")
        if len(sent) > 20:
            out.append(sent[:140])
        if len(out) >= limit:
            break
    return out[:limit]


def github_bullets(version: str) -> list[str]:
    text = _get(f"https://raw.githubusercontent.com/{REPO}/main/VERSIONLOG.md")
    return _bullets_from_log(text, version)


def _tuple(v: str) -> tuple[int, ...]:
    parts = []
    for p in re.split(r"[^\d]+", v):
        if p.isdigit():
            parts.append(int(p))
    return tuple(parts or [0])


def format_banner(installed: str, latest: str, bullets: list[str]) -> str:
    lines = []
    if installed == "unknown":
        lines.append(f"🪶 Raven version unknown locally · GitHub latest v{latest} — install/upgrade?")
    elif _tuple(latest) > _tuple(installed):
        lines.append(
            f"🪶 Raven v{installed} installed · GitHub v{latest} available — "
            "say upgrade to pull tag/plugin zip."
        )
    else:
        lines.append(f"🪶 Raven v{installed} — current (github.com/{REPO})")
    show = bullets[:5]
    if not show:
        show = [f"See VERSIONLOG.md / tag v{latest}"]
    while len(show) < min(5, len(show)):
        pass
    for b in show[:5]:
        lines.append(f"  • {b}")
    return "\n".join(lines)


def banner(root: Path | None = None) -> str:
    inst = installed_version(root)
    try:
        latest = github_latest_tag()
    except Exception:
        return f"🪶 Raven v{inst} — GitHub version check skipped (offline or rate limit)."
    ver_for_log = latest if _tuple(latest) > _tuple(inst) else inst
    try:
        bullets = github_bullets(ver_for_log)
    except Exception:
        bullets = []
    return format_banner(inst, latest, bullets)


def maybe_print_once(root: Path | None = None, *, always: bool = False) -> None:
    import time

    root = root or _root()
    stamp = root / ".raven" / ".version-banner"
    if not always and stamp.is_file():
        try:
            if time.time() - stamp.stat().st_mtime < 4 * 3600:
                return
        except OSError:
            pass
    text = banner(root)
    print(text)
    try:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(installed_version(root) + "\n", encoding="utf-8")
    except OSError:
        pass


if __name__ == "__main__":
    print(banner())
