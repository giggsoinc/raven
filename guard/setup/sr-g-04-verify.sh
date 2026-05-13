#!/bin/bash
# Guard Setup — Step 4: Verify
G='\033[0;32m' R='\033[0;31m' W='\033[1m' N='\033[0m'
ERR=0
chk() { [ -e "$1" ] && echo -e "  ${G}✅ $2${N}" || { echo -e "  ${R}❌ $2${N}"; ((ERR++)); }; }

echo -e "\n${W}  Verification${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"
chk "$PROJECT_DIR/.claude/agents/guard-git-watch.md"           "guard-git-watch"
chk "$PROJECT_DIR/.claude/agents/guard-db-watch.md"            "guard-db-watch"
chk "$PROJECT_DIR/.claude/agents/guard-infra-watch.md"         "guard-infra-watch"
chk "$PROJECT_DIR/.claude/agents/guard-observability-watch.md" "guard-observability-watch"
chk "$PROJECT_DIR/.claude/agents/guard-firewall-watch.md"      "guard-firewall-watch"
chk "$PROJECT_DIR/.claude/agents/guard-incident-manager.md"    "guard-incident-manager"
chk "$PROJECT_DIR/.claude/scripts/guard-notify.py"             "guard-notify.py"
chk "$PROJECT_DIR/.claude/scripts/guard-weekly-digest.py"      "guard-weekly-digest.py"
chk "$PROJECT_DIR/.claude/scripts/audit-log.py"                "audit-log.py"
chk "$PROJECT_DIR/.raven/manifest.secrets.json"           "manifest.secrets.json"

SPERM=$(stat -f "%Mp%Lp" "$PROJECT_DIR/.raven/manifest.secrets.json" 2>/dev/null || \
        stat -c "%a"     "$PROJECT_DIR/.raven/manifest.secrets.json" 2>/dev/null)
[ "$SPERM" = "600" ] && echo -e "  ${G}✅ secrets chmod 600${N}" || \
    echo -e "  ${R}❌ secrets chmod wrong${N}" && ((ERR++))

echo ""
[ "$ERR" -eq 0 ] && echo -e "${W}  ✅ GUARD ACTIVE${N}" || echo -e "${W}  ❌ $ERR error(s)${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"
