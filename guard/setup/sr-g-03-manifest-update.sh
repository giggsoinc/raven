#!/bin/bash
# Guard Setup — Step 3: Update manifest + secrets + permissions
G='\033[0;32m' Y='\033[1;33m' N='\033[0m'

# .gitignore
if [ -f "$PROJECT_DIR/.gitignore" ]; then
    MISSING=""
    for E in ".env" "raven-claude/" "manifest.secrets.json"; do
        grep -q "$E" "$PROJECT_DIR/.gitignore" 2>/dev/null || MISSING="$MISSING $E"
    done
    [ -n "$MISSING" ] && \
        printf '\n# Raven Guard\n.env\n.env.*\n*.pem\nmanifest.secrets.json\nraven-claude/\nraven-claude-guard/\n.raven/guard/digest.log\n' \
            >> "$PROJECT_DIR/.gitignore" && \
        echo -e "  ${Y}⚠️  .gitignore updated${N}" || echo -e "  ${G}✅ .gitignore OK${N}"
fi

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
G_ESCALATION_VAL="$G_ESCALATION" G_PAGERDUTY_VAL="$G_PAGERDUTY" \
G_THRESHOLD_VAL="$G_THRESHOLD" OUT_VAL="$PROJECT_DIR" TS_VAL="$TS" \
python3 - << 'PYEOF'
import json, os

out = os.environ["OUT_VAL"]

with open(f"{out}/.raven/manifest.json") as f:
    m = json.load(f)
m.setdefault("guard",{})
m["guard"].update({
    "enabled":   True,
    "version":   "1.2",
    "db":        {"mass_deletion_threshold": int(os.environ.get("G_THRESHOLD_VAL","100")),
                  "truncation": "hard_block", "schema_drop": "hard_block"},
    "git":       {"force_push": "hard_block"},
    "infra":     {"terraform_state": "hard_block", "s3_delete": "approval_flow"},
    "firewall":  {"open_world": "hard_block"},
    "incidents": {"p1_sla_minutes":15,"p2_sla_minutes":60,"p3_sla_hours":24}
})
with open(f"{out}/.raven/manifest.json","w") as f:
    json.dump(m, f, indent=2)

try:
    with open(f"{out}/.raven/manifest.secrets.json") as f:
        s = json.load(f)
except:
    s = {"_warning":"NEVER commit this file."}
s["guard"] = {
    "escalation":    os.environ.get("G_ESCALATION_VAL",""),
    "pagerduty_key": os.environ.get("G_PAGERDUTY_VAL",""),
    "webhook_url":   "",
    "weekly_digest": True,
    "p1_sla_minutes":15,"p2_sla_minutes":60,"p3_sla_hours":24
}
with open(f"{out}/.raven/manifest.secrets.json","w") as f:
    json.dump(s, f, indent=2)
PYEOF

chmod 600 "$PROJECT_DIR/.raven/manifest.secrets.json"
chmod 444 "$PROJECT_DIR/.claude/settings.json" 2>/dev/null || true
echo -e "  ${G}✅ Manifest + secrets updated, permissions set${N}"
