#!/usr/bin/env python3
"""
Shay-Rolls Claude — MCP Server
Exposes Shay-Rolls as a Claude Code plugin via Model Context Protocol.
Install: claude mcp add shay-rolls -- python3 /path/to/server.py

Tools exposed:
  shay_status        — check manifest, version, mode
  shay_cve_check     — run CVE check on a library
  shay_sync_libs     — sync libraries from requirements.txt
  shay_debug         — full project health check
  shay_violation     — emit a violation to audit log
"""

import json, os, subprocess, sys
from pathlib import Path

# MCP protocol over stdio
def send(obj):
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()

def read():
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line.strip())

def find_scripts_dir() -> Path:
    """Find .claude/scripts in current working directory."""
    cwd = Path(os.getcwd())
    scripts = cwd / ".claude" / "scripts"
    if scripts.exists():
        return scripts
    return None

def run_script(script: str, args: list[str] = []) -> dict:
    scripts = find_scripts_dir()
    if not scripts:
        return {"error": "Shay-Rolls not installed in this project. Run shay-rolls-setup.sh first."}
    path = scripts / script
    if not path.exists():
        return {"error": f"{script} not found in {scripts}"}
    result = subprocess.run(
        ["python3", str(path)] + args,
        capture_output=True, text=True, cwd=os.getcwd()
    )
    return {
        "stdout":      result.stdout,
        "stderr":      result.stderr,
        "returncode":  result.returncode
    }

# Tool definitions
TOOLS = [
    {
        "name":        "shay_status",
        "description": "Check Shay-Rolls manifest, version, mode, and project health",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name":        "shay_cve_check",
        "description": "Run CVE security check on a Python library using gpt-5.5",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library": {"type": "string", "description": "Library name e.g. fastapi"}
            },
            "required": ["library"]
        }
    },
    {
        "name":        "shay_sync_libs",
        "description": "Sync all libraries from requirements.txt/pyproject.toml into manifest",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dry_run": {"type": "boolean", "description": "Preview only, don't write"}
            },
            "required": []
        }
    },
    {
        "name":        "shay_debug",
        "description": "Full Shay-Rolls health check — manifest, agents, skills, hooks",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name":        "shay_violation",
        "description": "Emit a violation event to the Shay-Rolls audit log",
        "inputSchema": {
            "type": "object",
            "properties": {
                "type":     {"type": "string"},
                "severity": {"type": "string", "enum": ["P1","P2","P3"]},
                "detail":   {"type": "string"}
            },
            "required": ["type","severity","detail"]
        }
    }
]

def handle(method: str, params: dict) -> dict:
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities":    {"tools": {}},
            "serverInfo":      {"name": "shay-rolls", "version": "2.8.0"}
        }

    if method == "tools/list":
        return {"tools": TOOLS}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})

        if name == "shay_status":
            manifest_path = Path(os.getcwd()) / ".shay-rolls" / "manifest.json"
            if not manifest_path.exists():
                return {"content": [{"type":"text","text":"❌ manifest.json not found — run shay-rolls-setup.sh"}]}
            m = json.loads(manifest_path.read_text())
            out = (f"✅ Shay-Rolls {m.get('standards','')}\n"
                   f"Project: {m.get('project')} | Mode: {m.get('mode')} | "
                   f"GitHub: {m.get('github_id','')} | Tag: {m.get('audit_tag','')}\n"
                   f"Stack: {m.get('stack',{}).get('language')} | "
                   f"Cloud: {m.get('stack',{}).get('cloud')}")
            return {"content": [{"type":"text","text":out}]}

        if name == "shay_cve_check":
            r = run_script("cve-check.py", ["--library", args.get("library","")])
            return {"content": [{"type":"text","text": r.get("stdout","") + r.get("stderr","")}]}

        if name == "shay_sync_libs":
            extra = ["--dry-run"] if args.get("dry_run") else []
            r = run_script("sync-libraries.py", extra)
            return {"content": [{"type":"text","text": r.get("stdout","")}]}

        if name == "shay_debug":
            checks = []
            cwd = Path(os.getcwd())
            for f, label in [
                (".shay-rolls/manifest.json",       "manifest.json"),
                ("CLAUDE.md",                        "CLAUDE.md"),
                (".gitignore",                       ".gitignore"),
                (".claude/agents/manifest-checker.md","manifest-checker agent"),
                (".claude/scripts/cve-check.py",     "cve-check.py"),
                (".git/hooks/pre-commit",             "pre-commit hook"),
            ]:
                icon = "✅" if (cwd/f).exists() else "❌"
                checks.append(f"{icon} {label}")
            return {"content": [{"type":"text","text": "\n".join(checks)}]}

        if name == "shay_violation":
            r = run_script("emit-violation.py", [
                "--type",     args.get("type","unknown"),
                "--severity", args.get("severity","P3"),
                "--detail",   args.get("detail",""),
            ])
            return {"content": [{"type":"text","text": "Violation emitted" if r.get("returncode")==0 else r.get("stderr","")}]}

        return {"content": [{"type":"text","text":f"Unknown tool: {name}"}]}

    return {}

def main():
    while True:
        req = read()
        if req is None:
            break
        msg_id = req.get("id")
        method = req.get("method","")
        params = req.get("params", {})
        try:
            result = handle(method, params)
            send({"jsonrpc":"2.0","id":msg_id,"result":result})
        except Exception as e:
            send({"jsonrpc":"2.0","id":msg_id,"error":{"code":-32603,"message":str(e)}})

if __name__ == "__main__":
    main()
