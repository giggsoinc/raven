#!/usr/bin/env python3
"""
export-hook-configs.py — raven-config-canon-check (generator + CI check).

.claude/settings.json is the single canonical hook config (empirically live).
Three distribution copies are GENERATED from it — never hand-edited:

  hooks/hooks.json          plugin-marketplace format (${CLAUDE_PLUGIN_ROOT} paths)
  plugin/settings.json      plugin zip payload (same shape as canonical
                            + declared plugin-only extras below)
  core/hooks/settings.json  what setup/sr-02-install-files.sh deploys into
                            user projects (same shape as canonical)

The git pre-commit hook (core/hooks/pre-commit → ~/.patronai) is intentionally
external to Claude hook config and NOT managed here.

Usage:
  python3 scripts/ops/export-hook-configs.py            # regenerate all three
  python3 scripts/ops/export-hook-configs.py --check    # CI: exit 1 if any drifted
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANONICAL = REPO / ".claude" / "settings.json"

# Plugin-only hooks that do NOT exist in the canonical local config, kept by
# explicit decision (chain Prompt 3): the plugin ships skill-gating (see
# docs/SKILL-GATE.md); the local dev repo does not run it on itself.
PLUGIN_EXTRA_HOOKS = {
    "PreToolUse": [
        {
            "matcher": "Skill",
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/ops/hook-run.py\" scripts/ops/raven-skill-gate.py",
                }
            ],
        }
    ]
}

GEN_NOTE = (
    "GENERATED from .claude/settings.json by scripts/ops/export-hook-configs.py — "
    "do not hand-edit; run the exporter after changing the canonical file."
)


_PREFER = (
    "scripts/routing/",
    "scripts/session/",
    "scripts/memory/",
    "scripts/guards/",
    "scripts/ops/",
    "scripts/",
    ".claude/scripts/",
)


def _script_index() -> dict:
    """Basename → repo-relative path. Prefer the live subfolder over a stale flat path."""
    found: dict = {}
    for path in REPO.rglob("*.py"):
        if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
            continue
        rel = path.relative_to(REPO).as_posix()
        found.setdefault(path.name, []).append(rel)

    chosen = {}
    for name, rels in found.items():
        def rank(rel: str) -> tuple:
            for i, prefix in enumerate(_PREFER):
                if rel.startswith(prefix):
                    return (i, len(rel))
            return (len(_PREFER), len(rel))

        chosen[name] = sorted(rels, key=rank)[0]
    return chosen


def _unsilence(command: str) -> str:
    """Drop stderr dumps and trailing || true. hook-run exits 0 when the script is missing."""
    command = command.replace(" 2>/dev/null", "")
    command = re.sub(r"\s*\|\|\s*true\s*$", "", command.strip())
    return command


def _plugin_root_command(command: str, index: dict) -> str:
    """Rewrite the canonical command to plugin-root paths. No swallowed errors.

    A ``||`` fallback is dropped (the plugin has one tree). ``;`` keeps each call.
    Flags after the quoted script path are preserved.
    """
    command = _unsilence(command)
    rewritten = []
    for segment in re.split(r"\s*;\s*", command):
        primary = segment.split("||")[0].strip()
        match = re.search(r"([A-Za-z0-9_-]+\.py)\"?\s*(.*)$", primary)
        if not match or match.group(1) not in index:
            rewritten.append(primary)
            continue
        rel = index[match.group(1)]
        args = match.group(2).strip()
        piece = f'python3 "${{CLAUDE_PLUGIN_ROOT}}/{rel}"'
        if args:
            piece = f"{piece} {args}"
        rewritten.append(piece)
    return "; ".join(rewritten)


def _merge_hook_events(base: dict, extra: dict) -> dict:
    """Append plugin-only matchers. A dict merge would replace the whole event."""
    merged = {event: list(groups) for event, groups in base.items()}
    for event, groups in extra.items():
        merged.setdefault(event, [])
        merged[event] = list(merged[event]) + list(groups)
    return merged


def build_outputs(canonical: dict) -> dict:
    hooks = canonical["hooks"]
    index = _script_index()
    plugin_hooks = _merge_hook_events(hooks, PLUGIN_EXTRA_HOOKS)

    marketplace = {"hooks": {}}
    for event, groups in plugin_hooks.items():
        marketplace["hooks"][event] = [
            {
                "matcher": g.get("matcher", "*"),
                "hooks": [
                    {**{k: v for k, v in h.items() if k != "command"},
                     "command": _plugin_root_command(h["command"], index)}
                    for h in g["hooks"]
                ],
            }
            for g in groups
        ]

    plugin_settings = {
        "_generated": GEN_NOTE,
        "version": canonical.get("version", "1.0"),
        "description": canonical.get("description", ""),
        "hooks": plugin_hooks,
        "permissions": canonical.get("permissions", {}),
        "governance": canonical.get("governance", {}),
    }

    core_settings = {
        "_generated": GEN_NOTE,
        "version": canonical.get("version", "1.0"),
        "description": canonical.get("description", ""),
        "hooks": hooks,
        "permissions": canonical.get("permissions", {}),
        "governance": canonical.get("governance", {}),
    }

    marketplace["_generated"] = GEN_NOTE

    return {
        REPO / "hooks" / "hooks.json": marketplace,
        REPO / "plugin" / "settings.json": plugin_settings,
        REPO / "core" / "hooks" / "settings.json": core_settings,
    }


def main() -> int:
    check = "--check" in sys.argv
    canonical = json.loads(CANONICAL.read_text())
    outputs = build_outputs(canonical)

    failures = []
    for path, data in outputs.items():
        rendered = json.dumps(data, indent=2) + "\n"
        if check:
            on_disk = path.read_text() if path.exists() else ""
            if on_disk != rendered:
                failures.append(f"DRIFTED from canonical: {path.relative_to(REPO)}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered)
            print(f"generated: {path.relative_to(REPO)}")

    if check:
        if failures:
            print("raven-config-canon-check: FAIL")
            for f in failures:
                print(f"  {f}")
            print("  Fix: python3 scripts/ops/export-hook-configs.py  (then commit)")
            return 1
        print("raven-config-canon-check: PASS — all distribution configs match canonical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
