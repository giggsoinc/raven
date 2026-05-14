#!/usr/bin/env python3
# Raven — Tool Guard (PreToolUse hook)
# Fires before every Claude tool call
# Checks against manifest allowed_tools
# Blocks unapproved MCPs, APIs, URLs
#
# Claude Code passes tool info via stdin as JSON:
# {"tool_name": "WebFetch", "tool_input": {"url": "https://..."}}
# Exit 0 = allow, Exit 1 = block (Claude sees the error message)

import json, sys, os, re

def load_manifest():
    try:
        return json.load(open(".raven/manifest.json"))
    except:
        return {}

def load_input():
    try:
        return json.load(sys.stdin)
    except:
        return {}

def check_web_fetch(url: str, policy: dict) -> tuple[bool, str]:
    """Check if a URL is allowed."""
    blocked_patterns = policy.get("blocked_url_patterns", [
        r"notebooklm\.google\.com",   # personal NotebookLM
        r"api\.openai\.com",           # personal OpenAI
        r"platform\.openai\.com",
        r"chat\.openai\.com",
    ])
    allowed_domains = policy.get("allowed_domains", [])

    for pattern in blocked_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False, f"❌ URL blocked by Raven policy: {url}\n   Add to manifest.allowed_tools to permit."

    if allowed_domains:
        domain = re.sub(r"https?://([^/]+).*", r"\1", url)
        if not any(domain.endswith(d) for d in allowed_domains):
            return False, f"⚠️  URL not in allowed_domains: {url}\n   Add domain to manifest.allowed_tools.web.allowed_domains"

    return True, ""

def check_mcp(tool_name: str, policy: dict) -> tuple[bool, str]:
    """Check if an MCP server call is allowed."""
    # tool_name for MCP looks like: mcp__github__create_issue
    parts = tool_name.split("__")
    if len(parts) < 2:
        return True, ""

    server_name = parts[1].lower()
    approved_mcps = [m.get("name","").lower() for m in policy.get("mcps", [])]

    if approved_mcps and server_name not in approved_mcps:
        return False, f"❌ MCP server '{server_name}' not in manifest.allowed_tools.mcps\n   Add it to manifest to permit."

    return True, ""

def check_bash(command: str, policy: dict) -> tuple[bool, str]:
    """Check bash commands for unapproved API calls."""
    blocked_patterns = policy.get("blocked_bash_patterns", [
        r"openai\.com",
        r"OPENAI_API_KEY",
        r"sk-[A-Za-z0-9]{20,}",       # personal OpenAI key pattern
    ])

    for pattern in blocked_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"❌ Bash command blocked — unapproved API pattern detected.\n   Use enterprise credentials via manifest.allowed_tools."

    return True, ""

def main():
    manifest = load_manifest()
    policy = manifest.get("allowed_tools", {})
    data = load_input()

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    allowed = True
    message = ""

    if tool_name == "WebFetch":
        url = tool_input.get("url", "")
        allowed, message = check_web_fetch(url, policy)

    elif tool_name.startswith("mcp__"):
        allowed, message = check_mcp(tool_name, policy)

    elif tool_name == "Bash":
        command = tool_input.get("command", "")
        allowed, message = check_bash(command, policy)

    if not allowed:
        print(message, file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
