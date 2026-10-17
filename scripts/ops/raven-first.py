#!/usr/bin/env python3
"""Locate Raven engine, copy into the app repo if needed, then boot/router/cost.

Public Codex/Cursor often run from an app repo with no scripts/. The plugin
lives under CLAUDE_PLUGIN_ROOT / RAVEN_PLUGIN_ROOT (or ~/.claude|codex/plugins).

  python3 scripts/ops/raven-first.py --prompt "…"
  python3 scripts/ops/raven-first.py --session-start | --boot | --end
  Fallback: python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --prompt "…"
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_MARKER = Path("scripts") / "routing" / "model-router.py"
_HOME_CAP = 40


def _has_engine(root: Path) -> bool:
    return (root / _MARKER).is_file()


def _home_candidates(cap: int = _HOME_CAP) -> list[Path]:
    found: list[Path] = []
    for rel in (".codex/plugins", ".claude/plugins"):
        base = Path.home() / rel
        if not base.is_dir():
            continue
        for p in base.rglob("scripts/ops/raven-first.py"):
            eng = p.resolve().parents[2]
            if _has_engine(eng):
                found.append(eng)
            if len(found) >= cap:
                return found
    return found


def find_engine() -> Path:
    cwd = Path.cwd().resolve()
    if _has_engine(cwd):
        return cwd
    for key in ("CLAUDE_PLUGIN_ROOT", "RAVEN_PLUGIN_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            root = Path(raw).expanduser().resolve()
            if _has_engine(root):
                return root
    here = Path(__file__).resolve().parents[2]
    if _has_engine(here):
        return here
    cands = _home_candidates()
    if cands:
        return max(cands, key=lambda p: (p / _MARKER).stat().st_mtime)
    searched = (
        f"cwd={cwd}, CLAUDE_PLUGIN_ROOT, RAVEN_PLUGIN_ROOT, "
        f"__file__ engine={here}, ~/.codex/plugins, ~/.claude/plugins"
    )
    raise SystemExit(
        f"raven-first: no Raven engine with {_MARKER} found ({searched})"
    )


def _target() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()


def _ensure(engine: Path, target: Path) -> None:
    wrap = target / "scripts" / "raven-python.sh"
    router = target / _MARKER
    if wrap.is_file() and router.is_file():
        return
    he = engine / "scripts" / "ops" / "host-ensure.py"
    if not he.is_file():
        raise SystemExit(f"raven-first: host-ensure missing at {he}")
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(target)
    env["RAVEN_ENGINE"] = str(engine)
    r = subprocess.run(
        [sys.executable, str(he), "--no-open"],
        cwd=str(target),
        env=env,
        timeout=120,
    )
    if r.returncode != 0:
        raise SystemExit(f"raven-first: host-ensure failed (exit {r.returncode})")
    if not (target / _MARKER).is_file():
        raise SystemExit(
            f"raven-first: after host-ensure, still no {target / _MARKER}"
        )


def _run(target: Path, script: Path, argv: list[str]) -> int:
    wrap = target / "scripts" / "raven-python.sh"
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(target)
    if wrap.is_file():
        cmd = ["bash", str(wrap), str(script), *argv]
    else:
        cmd = [sys.executable, str(script), *argv]
    return subprocess.run(cmd, cwd=str(target), env=env).returncode


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    engine = find_engine()
    target = _target()
    _ensure(engine, target)
    jev_key = target / "scripts" / "ops" / "jev-key.py"
    if any(flag in args for flag in ("--boot", "--session-start", "--prompt")):
        _run(target, jev_key, ["--check"])
    boot = target / "scripts" / "memory" / "ide-boot.py"
    router = target / "scripts" / "routing" / "model-router.py"
    cost = target / "scripts" / "session" / "cost_calc.py"
    if "--boot" in args:
        return _run(target, boot, ["--no-open"] if "--open" not in args else ["--open"])
    if "--session-start" in args:
        return _run(target, router, ["--session-start"])
    hook = target / "scripts" / "memory" / "memory-card-hook.py"
    if "--end" in args:
        _run(target, hook, ["--event", "exit"])
        return _run(target, cost, ["--end"])
    if "--prompt" in args:
        i = args.index("--prompt")
        rest = args[i + 1 :]
        prompt = rest[0] if rest else ""
        _run(target, hook, ["--event", "turn"])
        return _run(target, router, ["--prompt", prompt])
    print(
        "usage: raven-first.py --prompt TEXT | --session-start | --boot | --end",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
