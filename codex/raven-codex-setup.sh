#!/bin/bash
set -e

RAVEN_DIR="$HOME/.raven-codex"
PROJECT_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Raven-Codex Setup v2.8        ║"
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
read -p "OpenAI API key (for CVE deep scan): " OPENAI_KEY

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
  "raven_version": "2.8.0",
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

# Write .env template
cat > "$PROJECT_DIR/.raven/.env.template" <<EOF
RAVEN_CVE_MODEL=gpt-4o
RAVEN_AUDIT_KEY=
OPENAI_API_KEY=$OPENAI_KEY
EOF

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
else
  echo "✅ Raven MCP already registered in ~/.codex/config.toml"
fi

echo ""
echo "✅ manifest.json written to .raven/"
echo "✅ AGENTS.md written to project root"
echo "✅ Audit log directory created"
echo "✅ MCP server registered"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Verify Raven is active:"
echo ""
echo "  In Codex: ask 'Run raven_status'"
echo "  Expected: ✅ manifest loaded, version, mode"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
