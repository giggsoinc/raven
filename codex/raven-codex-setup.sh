#!/bin/bash
set -e

RAVEN_DIR="$HOME/.raven-codex"
PROJECT_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Raven-Codex Setup v3.0        ║"
echo "║   Enterprise AI Coding Discipline    ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Collect project info
read -p "Project name: " PROJECT_NAME
read -p "Your email (audit trail): " USER_EMAIL
echo "Stack options: python / node / go / java / ruby / other"
read -p "Stack: " STACK
echo "Cloud options: aws / gcp / azure / oci / none"
read -p "Cloud provider: " CLOUD
echo ""
echo "ℹ️  OpenAI API key is used for CVE deep scan (gpt-based analysis)."
echo "   Raven will NEVER store it in .env or commit it to git."
echo "   Add it to your shell environment instead:"
echo "     export OPENAI_API_KEY=sk-...   ← add to ~/.zshrc or ~/.bashrc"
echo "   Press Enter to skip (PyPI basic scan will run instead)."
read -p "OpenAI API key (optional — for CVE deep scan): " OPENAI_KEY

# Create .raven directory in project
mkdir -p "$PROJECT_DIR/.raven/audit"
mkdir -p "$PROJECT_DIR/.raven/logs"

# Write manifest
cat > "$PROJECT_DIR/.raven/manifest.json" <<EOF
{
  "project": "$PROJECT_NAME",
  "version": "1.0",
  "platform": "codex",
  "owner": "$USER_EMAIL",
  "stack": "$STACK",
  "cloud": "$CLOUD",
  "mode": "active",
  "created": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "raven_version": "3.0.0",
  "approved_libraries": [],
  "blocked_patterns": [
    "TRUNCATE TABLE",
    "DROP TABLE",
    "DROP SCHEMA",
    "0.0.0.0/0",
    "force-push",
    "terraform.tfstate"
  ]
}
EOF

# Write .env template (template only — Raven never reads this; key must be in shell env)
cat > "$PROJECT_DIR/.raven/.env.template" <<EOF
# Raven environment template — DO NOT add real secrets here.
# Export these in your shell (~/.zshrc or ~/.bashrc) instead.
# Raven will NEVER read this file for credentials.
RAVEN_CVE_MODEL=gpt-5.5
# OPENAI_API_KEY=sk-...   ← export in shell, not here
EOF

# Issue 4 fix: Create .claude/scripts/ and deploy Raven scripts into project
# AGENTS.md references python3 .claude/scripts/version-check.py — this makes it real.
mkdir -p "$PROJECT_DIR/.claude/scripts"
echo "  Deploying Raven scripts to .claude/scripts/ ..."
for script in version-check.py cve-check.py audit-log.py secret-scan.py; do
  if [ -f "$RAVEN_DIR/scripts/$script" ]; then
    cp "$RAVEN_DIR/scripts/$script" "$PROJECT_DIR/.claude/scripts/$script"
    echo "  ✅ .claude/scripts/$script"
  else
    echo "  ⚠️  $script not found in $RAVEN_DIR/scripts/ — skipping"
  fi
done

# Copy AGENTS.md to project root — Codex reads this before every task
cp "$RAVEN_DIR/AGENTS.md" "$PROJECT_DIR/AGENTS.md" 2>/dev/null || true

# Write Codex MCP config (config.toml format)
mkdir -p "$HOME/.codex"
CODEX_CONFIG="$HOME/.codex/config.toml"

if ! grep -q "\[mcp_servers.raven\]" "$CODEX_CONFIG" 2>/dev/null; then
  cat >> "$CODEX_CONFIG" <<EOF

[mcp_servers.raven]
command = "python3"
args    = ["$RAVEN_DIR/mcp/server.py"]
EOF
  echo "✅ Raven MCP server registered in ~/.codex/config.toml"
  MCP_NEWLY_REGISTERED=true
else
  echo "✅ Raven MCP already registered in ~/.codex/config.toml"
  MCP_NEWLY_REGISTERED=false
fi

echo ""
echo "✅ manifest.json written to .raven/"
echo "✅ AGENTS.md written to project root"
echo "✅ Audit log directory created"
echo "✅ MCP server registered"
echo "✅ Raven scripts deployed to .claude/scripts/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Raven v3.0 is ready."
echo ""
echo "Verify Raven is active:"
echo "  In Codex: ask 'Run raven_status'"
echo "  Expected: ✅ manifest loaded, version, mode"
echo ""
if [ "$MCP_NEWLY_REGISTERED" = "true" ]; then
  echo "⚠️  IMPORTANT — MCP tools require a session restart to load."
  echo "   Close and reopen your Codex session now."
  echo "   Then ask: 'Run raven_status' — you should see ✅ on all checks."
  echo ""
fi
echo "CVE deep scan (recommended):"
echo "  export OPENAI_API_KEY=sk-...   ← add to ~/.zshrc and source it"
echo "  Without this, Raven runs PyPI basic scan only."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
