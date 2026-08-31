#!/usr/bin/env python3
"""MCP tool dispatch — subprocess into Raven scripts."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from catalog import TOOLS


def find_scripts_dir() -> Path | None:
    cwd = Path(os.getcwd())
    here = Path(__file__).resolve().parent
    for candidate in [
        cwd / "scripts",
        cwd / ".raven" / "scripts",
        cwd / ".claude" / "scripts",
        here.parent / "scripts",
        here,
        Path.home() / ".raven-codex" / "scripts",
        Path.home() / ".raven" / "scripts",
    ]:
        if (candidate / "code-xray.py").exists() or (candidate / "cve-check.py").exists():
            return candidate
    return None


def run_script(script: str, args: list[str] | None = None) -> dict:
    scripts = find_scripts_dir()
    if not scripts:
        return {"error": "Raven not installed. Run raven-setup.sh first."}
    path = scripts / script
    if not path.exists():
        return {"error": f"{script} not found in {scripts}"}
    result = subprocess.run(
        ["python3", str(path)] + (args or []),
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


def _text(msg: str) -> dict:
    return {"content": [{"type": "text", "text": msg}]}


def _xray(args: list[str]) -> dict:
    r = run_script("code-xray.py", args)
    return _text(r.get("stdout") or r.get("stderr") or "")


def call_tool(name: str, args: dict) -> dict:
    args = args or {}
    if name == "raven_status":
        p = Path(os.getcwd()) / ".raven" / "manifest.json"
        if not p.exists():
            return _text("❌ manifest.json not found — run raven-setup.sh")
        m = json.loads(p.read_text())
        st = m.get("stack") or {}
        return _text(
            f"✅ Raven {m.get('standards', '')}\n"
            f"Project: {m.get('project')} | Mode: {m.get('mode')} | "
            f"GitHub: {m.get('github_id', '')} | Tag: {m.get('audit_tag', '')}\n"
            f"Stack: {st.get('language')} | Cloud: {st.get('cloud')}"
        )
    if name == "raven_cve_check":
        r = run_script("cve-check.py", ["--library", args.get("library", "")])
        return _text((r.get("stdout") or "") + (r.get("stderr") or ""))
    if name == "raven_sync_libs":
        extra = ["--dry-run"] if args.get("dry_run") else []
        r = run_script("sync-libraries.py", extra)
        return _text(r.get("stdout") or "")
    if name == "raven_debug":
        cwd = Path(os.getcwd())
        scripts = find_scripts_dir()
        rows = []
        for rel, label in [
            (".raven/manifest.json", "manifest.json"),
            (".gitignore", ".gitignore"),
            (".git/hooks/pre-commit", "pre-commit hook"),
        ]:
            rows.append(f"{'✅' if (cwd / rel).exists() else '❌'} {label}")
        rows.append(f"{'✅' if scripts else '❌'} raven scripts ({scripts or 'not found'})")
        md = (cwd / "CLAUDE.md").exists()
        rows.append(f"{'✅' if md else 'ℹ️ '} CLAUDE.md {'(present)' if md else '(optional)'}")
        return _text("\n".join(rows))
    if name == "query_graph":
        extra = ["--query-type", args.get("type") or "file"]
        if args.get("commit") or args.get("sha"):
            extra += ["--commit", args.get("commit") or args.get("sha")]
        return _xray(extra)
    if name == "get_node":
        return _xray(["--node", args.get("id", "")])
    if name == "get_neighbors":
        return _xray(["--neighbors", args.get("id", "")])
    if name == "shortest_path":
        return _xray(["--path-from", args.get("from_id", ""), "--path-to", args.get("to_id", "")])
    if name == "commit_impact":
        return _xray(["--impact", args.get("sha", "HEAD")])
    if name == "find_gaps":
        return _xray(["--gaps"])
    if name == "raven_violation":
        r = run_script("emit-violation.py", [
            "--type", args.get("type", "unknown"),
            "--severity", args.get("severity", "P3"),
            "--detail", args.get("detail", ""),
        ])
        return _text("Violation emitted" if r.get("returncode") == 0 else (r.get("stderr") or ""))
    return _text(f"Unknown tool: {name}")


def handle(method: str, params: dict) -> dict:
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "raven", "version": "5.5.5"},
        }
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        return call_tool(params.get("name") or "", params.get("arguments") or {})
    return {}
