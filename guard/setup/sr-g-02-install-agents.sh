#!/bin/bash
# Guard Setup — Step 2: Install agents + scripts
G='\033[0;32m' N='\033[0m'

mkdir -p "$PROJECT_DIR/.claude/agents"
mkdir -p "$PROJECT_DIR/.claude/scripts"
mkdir -p "$PROJECT_DIR/.claude/skills/andie"
mkdir -p "$PROJECT_DIR/.raven/guard"

for A in guard-git-watch guard-db-watch guard-infra-watch \
          guard-observability-watch guard-firewall-watch guard-incident-manager; do
    cp "$SR_GUARD_DIR/guard/agents/$A.md" "$PROJECT_DIR/.claude/agents/"
    echo -e "  ${G}✅ $A${N}"
done

for S in guard-notify.py guard-weekly-digest.py emit-violation.py audit-log.py; do
    [ -f "$SR_GUARD_DIR/guard/scripts/$S" ] && \
        cp "$SR_GUARD_DIR/guard/scripts/$S" "$PROJECT_DIR/.claude/scripts/" && \
        chmod +x "$PROJECT_DIR/.claude/scripts/$S" && \
        echo -e "  ${G}✅ $S${N}"
done

[ -f "$SR_GUARD_DIR/guard/skills/andie/SKILL.md" ] && \
    cp "$SR_GUARD_DIR/guard/skills/andie/SKILL.md" "$PROJECT_DIR/.claude/skills/andie/" && \
    echo -e "  ${G}✅ andie skill${N}"
