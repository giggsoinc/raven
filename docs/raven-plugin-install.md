# Raven — Plugin Install Guide
## Claude Code · VS Code · Cursor · AntiGravity · Windsurf

---

## Claude Code — MCP Plugin (recommended)

```bash
# Step 1 — Install Raven framework (once, ever)
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash

# Step 2 — Register as MCP plugin
claude mcp add raven -- python3 ~/.raven/mcp/server.py

# Step 3 — Verify
claude mcp list
# Should show: raven (stdio)
```

**Tools available in every Claude Code session:**
```
/mcp__raven__raven_status       — check manifest, version, mode
/mcp__raven__raven_cve_check    — CVE scan any library
/mcp__raven__raven_sync_libs    — sync requirements → manifest
/mcp__raven__raven_debug        — full health check
/mcp__raven__raven_violation    — emit violation to audit log
```

**Per project — init once:**
```bash
cd YourProject
raven-setup
```

---

## VS Code — MCP Extension

VS Code supports MCP servers via `settings.json`:

```json
// .vscode/settings.json
{
  "mcp": {
    "servers": {
      "raven": {
        "type": "stdio",
        "command": "python3",
        "args": ["${env:HOME}/.raven/mcp/server.py"]
      }
    }
  }
}
```

Or globally in VS Code user settings (`Cmd+Shift+P` → Open User Settings JSON):
```json
{
  "mcp.servers": {
    "raven": {
      "type": "stdio",
      "command": "python3",
      "args": ["/Users/YOUR_NAME/.raven/mcp/server.py"]
    }
  }
}
```

Raven tools then appear in GitHub Copilot Chat inside VS Code.

---

## Cursor

Cursor supports MCP servers via `.cursor/mcp.json`:

```json
// .cursor/mcp.json (project level)
// or ~/.cursor/mcp.json (global)
{
  "mcpServers": {
    "raven": {
      "command": "python3",
      "args": ["/Users/YOUR_NAME/.raven/mcp/server.py"]
    }
  }
}
```

Raven tools appear in Cursor's AI panel automatically.

---

## Windsurf (Codeium)

Windsurf supports MCP via `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "raven": {
      "command": "python3",
      "args": ["/Users/YOUR_NAME/.raven/mcp/server.py"]
    }
  }
}
```

---

## AntiGravity (Cowork)

For internal Cowork deployment — enterprise zero-click:

```bash
# Admin deploys to system-wide location
sudo mkdir -p /usr/local/raven
sudo cp -r ~/.raven/* /usr/local/raven/

# Deploy managed MCP config
sudo cp managed-mcp.json \
  "/Library/Application Support/ClaudeCode/managed-mcp.json"
```

All developers get Raven automatically on next Claude Code launch.
No install. No setup. Just works.

---

## All IDEs — One-line path reference

Replace `/Users/YOUR_NAME/` with your actual home path.
Or use `${env:HOME}` where the IDE supports env var expansion.

```
Raven MCP server path:
  ~/.raven/mcp/server.py

Command to run:
  python3 ~/.raven/mcp/server.py
```

---

## Enterprise — managed-mcp.json

For MDM/Jamf/Intune deployment — push to all machines:

```json
{
  "mcpServers": {
    "raven": {
      "type": "stdio",
      "command": "python3",
      "args": ["/usr/local/raven/mcp/server.py"]
    }
  }
}
```

macOS path: `/Library/Application Support/ClaudeCode/managed-mcp.json`
Windows path: `C:\ProgramData\ClaudeCode\managed-mcp.json`

---

## Verify installation (any IDE)

After adding the MCP config, ask your AI assistant:
```
Check Raven status
```

Should respond with:
```
✅ Raven v2.8
Project: [name] | Mode: [solo/team/enterprise]
Stack: [languages] | Cloud: [provider]
```

---

Built by [Giggso](https://giggso.com) · [github.com/giggsoinc/raven](https://github.com/giggsoinc/raven) · MIT
