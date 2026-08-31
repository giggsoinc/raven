#!/usr/bin/env python3
"""Ensure host glue + working python wrapper + engine script trees.

Called from raven-first /raven-init /raven-debug so public users get AGENTS.md,
.agents/agents.md, raven-python.sh, routing/memory/session/ops, and a dashboard.

  python3 scripts/ops/host-ensure.py --open
  RAVEN_ENGINE=/path/to/plugin python3 …/host-ensure.py --no-open
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

_ENV_ENGINE = (os.environ.get("RAVEN_ENGINE") or "").strip()
ENGINE = Path(_ENV_ENGINE).resolve() if _ENV_ENGINE else Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd()).resolve()
_TREES = ("routing", "memory", "session", "ops")
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")


def _copy(src: Path, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    return str(dest.relative_to(TARGET))


def _copy_tree_missing(src: Path, dest: Path) -> str | None:
    """Copy engine script subtree into TARGET when missing or incomplete."""
    if not src.is_dir():
        return None
    marker_name = {
        "routing": "model-router.py",
        "memory": "ide-boot.py",
        "session": "cost_calc.py",
        "ops": "raven-first.py",
    }.get(dest.name)
    if dest.is_dir() and marker_name and (dest / marker_name).is_file():
        return None
    if dest.resolve() == src.resolve():
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copytree(src, dest, ignore=_IGNORE)
    else:
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in ("__pycache__",)]
            rel = Path(root).relative_to(src)
            out = dest / rel
            out.mkdir(parents=True, exist_ok=True)
            for name in files:
                if name.endswith(".pyc") or name == ".DS_Store":
                    continue
                s, d = Path(root) / name, out / name
                if not d.is_file():
                    shutil.copy2(s, d)
    return str(dest.relative_to(TARGET)) + "/"


def ensure() -> list[str]:
    done: list[str] = []
    py = ENGINE / "scripts" / "raven-python.sh"
    dest_py = TARGET / "scripts" / "raven-python.sh"
    if py.is_file():
        _copy(py, dest_py)
        dest_py.chmod(dest_py.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        done.append("scripts/raven-python.sh")
    for name in _TREES:
        rel = _copy_tree_missing(ENGINE / "scripts" / name, TARGET / "scripts" / name)
        if rel:
            done.append(rel)
    always = [
        (ENGINE / ".agents" / "agents.md", TARGET / ".agents" / "agents.md"),
        (ENGINE / "AGENTS.md", TARGET / "AGENTS.md"),
        (ENGINE / "AGENTS.override.md", TARGET / "AGENTS.override.md"),
        (ENGINE / ".cursor" / "rules" / "raven-router.mdc", TARGET / ".cursor" / "rules" / "raven-router.mdc"),
        (ENGINE / ".windsurf" / "rules" / "ide-boot.md", TARGET / ".windsurf" / "rules" / "ide-boot.md"),
        (ENGINE / ".vscode" / "raven-router.md", TARGET / ".vscode" / "raven-router.md"),
        (ENGINE / ".github" / "copilot-instructions.md", TARGET / ".github" / "copilot-instructions.md"),
    ]
    for src, dest in always:
        if src.is_file():
            done.append(_copy(src, dest))
    boot_src = ENGINE / ".raven" / "boot.json"
    boot_dst = TARGET / ".raven" / "boot.json"
    if boot_src.is_file() and not boot_dst.is_file():
        done.append(_copy(boot_src, boot_dst))
    edu = TARGET / ".raven" / "educate.json"
    if not edu.is_file():
        edu.parent.mkdir(parents=True, exist_ok=True)
        edu.write_text('{"mode": "guided"}\n', encoding="utf-8")
        done.append(".raven/educate.json")
    return done


def open_dashboard() -> None:
    boot = ENGINE / "scripts" / "memory" / "ide-boot.py"
    if not boot.is_file():
        boot = TARGET / "scripts" / "memory" / "ide-boot.py"
    if not boot.is_file():
        print("host-ensure: ide-boot.py missing — skip dashboard open", file=sys.stderr)
        return
    wrap = TARGET / "scripts" / "raven-python.sh"
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(TARGET)
    if wrap.is_file():
        cmd = ["bash", str(wrap), str(boot), "--open"]
    else:
        cmd = [sys.executable, str(boot), "--open"]
    subprocess.run(cmd, cwd=str(TARGET), env=env, timeout=180)


def main() -> int:
    done = ensure()
    print("host-ensure: " + (", ".join(done) if done else "already present"))
    print('Router: python3 scripts/ops/raven-first.py --prompt "…"')
    if "--no-open" not in sys.argv:
        open_dashboard()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
