#!/bin/bash
set -e

PROJECT_DIR="$(pwd)"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Raven-Guard-Codex Setup v1.3     ║"
echo "║     Enterprise Production Guard      ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Check raven manifest exists
if [ ! -f "$PROJECT_DIR/.raven/manifest.json" ]; then
  echo "❌ .raven/manifest.json not found."
  echo "   Run raven-codex-setup first."
  exit 1
fi

read -p "Escalation email for P1 incidents: " ESCALATION_EMAIL
read -p "Slack webhook URL (optional, press enter to skip): " SLACK_WEBHOOK

# Write guard config
mkdir -p "$PROJECT_DIR/.raven"
cat > "$PROJECT_DIR/.raven/guard.json" <<EOF
{
  "version": "1.3.0",
  "platform": "codex",
  "escalation_email": "$ESCALATION_EMAIL",
  "slack_webhook": "$SLACK_WEBHOOK",
  "hard_blocks": [
    "force_push",
    "truncate_table",
    "drop_table",
    "drop_schema",
    "terraform_state_edit",
    "firewall_open_all",
    "rdp_public",
    "ssh_public",
    "k8s_namespace_delete",
    "secrets_committed",
    "repo_config_wipe"
  ],
  "approval_required": [
    "mass_delete_rows",
    "s3_bucket_delete",
    "vm_termination",
    "network_rule_change",
    "index_delete"
  ],
  "sla": {
    "p1_critical_minutes": 15,
    "p2_high_minutes": 60,
    "p3_medium_hours": 24
  }
}
EOF

echo ""
echo "✅ guard.json written to .raven/"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Hard blocks active (no exceptions):"
echo "  force push · TRUNCATE · DROP TABLE"
echo "  Terraform state · open firewall rules"
echo "  public RDP/SSH · K8s namespace delete"
echo "  secrets committed · repo config wipe"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
