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

echo ""
echo "✅ manifest.json written to .raven/"
echo "✅ Audit log directory created"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next: Connect Raven MCP server to Codex"
echo ""
echo "  1. Go to https://chatgpt.com/codex"
echo "  2. Settings → MCP Servers → Add MCP Server"
echo "  3. Name: raven"
echo "     Command: python3"
echo "     Args: $RAVEN_DIR/mcp/server.py"
echo "  4. Test: ask Codex to run raven_status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
