#!/bin/bash
# Raven Setup — Step 5: Generate manifest.secrets.json + set permissions
# Requires: PROJECT_DIR EMAIL INBOX OPENAI_KEY SR_SECRETS_BAK

G='\033[0;32m' N='\033[0m'

if [ -n "$SR_SECRETS_BAK" ]; then
    echo "$SR_SECRETS_BAK" > "$PROJECT_DIR/.raven/manifest.secrets.json"
    echo -e "  ${G}✅ Existing secrets restored${N}"
else
    EMAIL_VAL="$EMAIL" INBOX_VAL="$INBOX" KEY_VAL="$OPENAI_KEY" OUT_VAL="$PROJECT_DIR" \
    python3 - << 'PYEOF'
import json, os
s = {
  "_warning": "NEVER commit this file.",
  "approvals": {
    "shared_inbox": os.environ.get("INBOX_VAL",""),
    "approvers":    [os.environ.get("EMAIL_VAL","")],
    "escalation":   os.environ.get("EMAIL_VAL","")
  },
  "cve_check": {
    "openai_api_key": os.environ.get("KEY_VAL",""),
    "model": "gpt-5.5"
  },
  "audit": {
    "provider":       "",
    "s3_bucket":      "",
    "s3_region":      "us-east-1",
    "kms_key_id":     "",
    "gcs_bucket":     "",
    "azure_connection_string": "",
    "azure_container": "",
    "oci_namespace":  "",
    "oci_bucket":     "",
    "encryption_key": "",
    "local_fallback": False
  },
  "guard": {
    "pagerduty_key":  "",
    "webhook_url":    "",
    "weekly_digest":  False
  }
}
with open(f"{os.environ['OUT_VAL']}/.raven/manifest.secrets.json","w") as f:
    json.dump(s, f, indent=2)
PYEOF
    echo -e "  ${G}✅ manifest.secrets.json created${N}"
fi

chmod 600 "$PROJECT_DIR/.raven/manifest.secrets.json"
chmod 444 "$PROJECT_DIR/.claude/settings.json" 2>/dev/null || true
echo -e "  ${G}✅ Permissions set (secrets 600, settings 444)${N}"
