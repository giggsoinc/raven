#!/usr/bin/env python3
"""
Raven — MCP Server (platform-agnostic)
Exposes Raven as an MCP plugin for Claude Code, OpenAI Codex, or any MCP-compatible agent.

Claude Code:  claude mcp add raven -- python3 ~/.raven/mcp/server.py
Codex:        Settings → MCP Servers → python3 ~/.raven-codex/mcp/server.py

Tools exposed:
  raven_status        — check manifest, version, mode
  raven_cve_check     — run CVE check on a library
  raven_sync_libs     — sync libraries from requirements.txt
  raven_debug         — full project health check
  raven_violation     — emit a violation to audit log
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
    """Find Raven scripts — checks .raven/scripts, then .claude/scripts for backwards compat."""
    cwd = Path(os.getcwd())
    for candidate in [
        cwd / ".raven" / "scripts",
        cwd / ".claude" / "scripts",
        Path(os.path.dirname(__file__)),           # same dir as this server.py
        Path.home() / ".raven-codex" / "scripts",
        Path.home() / ".raven" / "scripts",
    ]:
        if candidate.exists() and (candidate / "cve-check.py").exists():
            return candidate
    return None

def run_script(script: str, args: list[str] = []) -> dict:
    scripts = find_scripts_dir()
    if not scripts:
        return {"error": "Raven not installed in this project. Run raven-setup.sh first."}
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
        "name":        "raven_status",
        "description": "Check Raven manifest, version, mode, and project health",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name":        "raven_cve_check",
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
        "name":        "raven_sync_libs",
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
        "name":        "raven_debug",
        "description": "Full Raven health check — manifest, agents, skills, hooks",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name":        "raven_violation",
        "description": "Emit a violation event to the Raven audit log",
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
            "serverInfo":      {"name": "raven", "version": "2.8.0"}
        }

    if method == "tools/list":
        return {"tools": TOOLS}

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})

        if name == "raven_status":
            manifest_path = Path(os.getcwd()) / ".raven" / "manifest.json"
            if not manifest_path.exists():
                return {"content": [{"type":"text","text":"❌ manifest.json not found — run raven-setup.sh"}]}
            m = json.loads(manifest_path.read_text())
            out = (f"✅ Raven {m.get('standards','')}\n"
                   f"Project: {m.get('project')} | Mode: {m.get('mode')} | "
                   f"GitHub: {m.get('github_id','')} | Tag: {m.get('audit_tag','')}\n"
                   f"Stack: {m.get('stack',{}).get('language')} | "
                   f"Cloud: {m.get('stack',{}).get('cloud')}")
            return {"content": [{"type":"text","text":out}]}

        if name == "raven_cve_check":
            r = run_script("cve-check.py", ["--library", args.get("library","")])
            return {"content": [{"type":"text","text": r.get("stdout","") + r.get("stderr","")}]}

        if name == "raven_sync_libs":
            extra = ["--dry-run"] if args.get("dry_run") else []
            r = run_script("sync-libraries.py", extra)
            return {"content": [{"type":"text","text": r.get("stdout","")}]}

        if name == "raven_debug":
            checks = []
            cwd = Path(os.getcwd())
            scripts = find_scripts_dir()
            for f, label in [
                (".raven/manifest.json",   "manifest.json"),
                (".gitignore",             ".gitignore"),
                (".git/hooks/pre-commit",  "pre-commit hook"),
            ]:
                icon = "✅" if (cwd/f).exists() else "❌"
                checks.append(f"{icon} {label}")
            checks.append(f"{'✅' if scripts else '❌'} raven scripts ({scripts or 'not found'})")
            checks.append(f"{'✅' if (cwd/'CLAUDE.md').exists() else '⚠️ '} CLAUDE.md (Claude Code only)")
            return {"content": [{"type":"text","text": "\n".join(checks)}]}

        if name == "raven_violation":
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
