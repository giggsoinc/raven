#!/bin/bash
# Raven Setup — Step 6: Verify installation
# Requires: PROJECT_DIR PROJECT MODE

G='\033[0;32m' R='\033[0;31m' W='\033[1m' N='\033[0m'

ERR=0
chk() { [ -e "$1" ] && echo -e "  ${G}✅ $2${N}" || { echo -e "  ${R}❌ $2${N}"; ((ERR++)); }; }

echo -e "${W}  Verification${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"

chk "$PROJECT_DIR/CLAUDE.md"                                "CLAUDE.md"
chk "$PROJECT_DIR/.gitignore"                               ".gitignore"
chk "$PROJECT_DIR/.claude/agents/manifest-checker.md"      "manifest-checker"
chk "$PROJECT_DIR/.claude/agents/style-enforcer.md"        "style-enforcer"
chk "$PROJECT_DIR/.claude/agents/claude-mem.md"            "claude-mem"
chk "$PROJECT_DIR/.claude/skills/raven-core/SKILL.md" "raven-core skill"
chk "$PROJECT_DIR/.claude/skills/andie/SKILL.md"           "andie skill"
chk "$PROJECT_DIR/.claude/scripts/cve-check.py"            "cve-check.py"
chk "$PROJECT_DIR/.claude/scripts/secret-scan.py"          "secret-scan.py"
chk "$PROJECT_DIR/.claude/scripts/audit-log.py"            "audit-log.py"
chk "$PROJECT_DIR/.git/hooks/pre-commit"                   "pre-commit hook"
chk "$PROJECT_DIR/.raven/manifest.json"               "manifest.json"
chk "$PROJECT_DIR/.raven/manifest.secrets.json"       "manifest.secrets.json"

python3 -c "
import json, sys
try:
    json.load(open('$PROJECT_DIR/.raven/manifest.json'))
    print('  \033[0;32m✅ manifest.json valid JSON\033[0m')
except Exception as e:
    print(f'  \033[0;31m❌ manifest.json invalid: {e}\033[0m')
    sys.exit(1)
"

SPERM=$(stat -f "%Mp%Lp" "$PROJECT_DIR/.raven/manifest.secrets.json" 2>/dev/null || \
        stat -c "%a"     "$PROJECT_DIR/.raven/manifest.secrets.json" 2>/dev/null)
# Normalize — macOS returns 0600, Linux returns 600
SPERM="${SPERM#0}"
if [ "$SPERM" = "600" ]; then
    echo -e "  ${G}✅ secrets chmod 600${N}"
else
    echo -e "  ${R}❌ secrets chmod $SPERM (expected 600) — run: chmod 600 .raven/manifest.secrets.json${N}"
    ((ERR++))
fi

echo ""
[ "$ERR" -eq 0 ] && \
    echo -e "${W}  ✅ CLEARED — $PROJECT ($MODE mode)${N}" || \
    echo -e "${W}  ❌ $ERR error(s) — fix above and re-run${N}"

echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"
echo -e "  Next: cd $PROJECT_DIR && claude ."
echo -e "  Then: /raven-debug\n"

echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  💡 Recommended alongside Raven${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"
echo -e "  ${B}Superpowers${N} — dev methodology: brainstorm → plan → TDD → ship"
echo -e "  ${G}  claude skill install superpowers --global${N}\n"
echo -e "  ${B}GSD${N} — context management: keeps quality high in long sessions"
echo -e "  ${G}  claude skill install gsd --global${N}\n"
echo -e "  Raven: governance + security"
echo -e "  Superpowers + GSD: workflow + execution"
echo -e "  They stack. No conflicts.\n"
