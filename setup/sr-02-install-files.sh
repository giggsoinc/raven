#!/bin/bash
# Raven Setup — Step 2: Install files into project
# Requires: SR_REPO_DIR PROJECT_DIR (from sr-01)

G='\033[0;32m' N='\033[0m'

mkdir -p "$PROJECT_DIR"/{.claude/{agents,commands,scripts},.raven/{.cache,audit,guard}}
mkdir -p "$PROJECT_DIR"/{docs/{observations,knowledge},.raven/.cache/dynamic-skills}
mkdir -p "$PROJECT_DIR/.claude/skills/"{raven-core/rules,raven-expert,raven-plan,\
raven-review,raven-security,raven-refactor,raven-test,raven-document,andie}

cp "$SR_REPO_DIR/CLAUDE.md"                                       "$PROJECT_DIR/CLAUDE.md"
cp "$SR_REPO_DIR/core/hooks/settings.json"                        "$PROJECT_DIR/.claude/settings.json"
cp "$SR_REPO_DIR/core/agents/"*.md                                "$PROJECT_DIR/.claude/agents/"
cp "$SR_REPO_DIR/core/commands/"*.md                              "$PROJECT_DIR/.claude/commands/"
cp "$SR_REPO_DIR/raven-core/"*.py                                  "$PROJECT_DIR/.claude/scripts/"
cp "$SR_REPO_DIR/raven-core/server.py"                            "$PROJECT_DIR/.claude/scripts/"
chmod +x "$PROJECT_DIR/.claude/scripts/"*.py 2>/dev/null || true
chmod +x "$PROJECT_DIR/.claude/scripts/"*.sh 2>/dev/null || true
cp "$SR_REPO_DIR/core/skills/raven-core/SKILL.md"            "$PROJECT_DIR/.claude/skills/raven-core/"
cp "$SR_REPO_DIR/core/skills/raven-core/rules/"*.md          "$PROJECT_DIR/.claude/skills/raven-core/rules/"
for SK in raven-expert raven-plan raven-review raven-security raven-refactor raven-test raven-document andie; do
    cp "$SR_REPO_DIR/core/skills/$SK/SKILL.md" "$PROJECT_DIR/.claude/skills/$SK/"
done
cp "$SR_REPO_DIR/templates/architecture.md"       "$PROJECT_DIR/.raven/architecture.md"
cp "$SR_REPO_DIR/templates/erd-template.md"       "$PROJECT_DIR/docs/erd-template.md" 2>/dev/null || true
cp "$SR_REPO_DIR/docs/observations/security_log.md" "$PROJECT_DIR/docs/observations/security_log.md"
cp "$SR_REPO_DIR/docs/knowledge/internal_raven_ops.md" "$PROJECT_DIR/docs/knowledge/internal_raven_ops.md"
cp "$SR_REPO_DIR/docs/knowledge/general_security_patterns.md" "$PROJECT_DIR/docs/knowledge/general_security_patterns.md"
mkdir -p "$PROJECT_DIR/.raven/ci"
cp "$SR_REPO_DIR/core/ci/"*                   "$PROJECT_DIR/.raven/ci/"

[ ! -d "$PROJECT_DIR/.git" ] && git -C "$PROJECT_DIR" init --quiet && \
    git -C "$PROJECT_DIR" checkout -b main 2>/dev/null || true

cp "$SR_REPO_DIR/core/hooks/pre-commit"  "$PROJECT_DIR/.git/hooks/pre-commit"
chmod +x "$PROJECT_DIR/.git/hooks/pre-commit"

echo -e "  ${G}✅ All files installed${N}"
