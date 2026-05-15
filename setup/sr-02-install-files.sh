#!/bin/bash
# Raven Setup — Step 2: Install files into project
# Requires: SR_REPO_DIR PROJECT_DIR WORK_MODE (from sr-00/sr-01)
#
# NOTE: If the global install (install.sh) was run, skills/agents are already
# in ~/.claude/ and available everywhere. This step installs project-local copies
# for teams that prefer explicit per-repo skill versioning.

G='\033[0;32m' N='\033[0m'

# ─── DIRECTORIES ─────────────────────────────────────────────────────────────
mkdir -p "$PROJECT_DIR"/{.claude/{agents,commands,scripts},.raven/{.cache,audit,guard}}
mkdir -p "$PROJECT_DIR"/{docs/{observations,knowledge},.raven/.cache/dynamic-skills}
mkdir -p "$PROJECT_DIR/.claude/skills/raven-core/rules"
mkdir -p "$PROJECT_DIR/.raven/ci"

# ─── CORE FILES ──────────────────────────────────────────────────────────────
cp "$SR_REPO_DIR/CLAUDE.md"                   "$PROJECT_DIR/CLAUDE.md"
cp "$SR_REPO_DIR/core/hooks/settings.json"    "$PROJECT_DIR/.claude/settings.json"

# Agents — all 10
cp "$SR_REPO_DIR/core/agents/"*.md            "$PROJECT_DIR/.claude/agents/"

# Commands
cp "$SR_REPO_DIR/core/commands/"*.md          "$PROJECT_DIR/.claude/commands/"

# Scripts
cp "$SR_REPO_DIR/raven-core/"*.py             "$PROJECT_DIR/.claude/scripts/" 2>/dev/null || true
cp "$SR_REPO_DIR/core/scripts/"*.py           "$PROJECT_DIR/.claude/scripts/" 2>/dev/null || true
cp "$SR_REPO_DIR/core/scripts/"*.sh           "$PROJECT_DIR/.claude/scripts/" 2>/dev/null || true
cp "$SR_REPO_DIR/setup/sr-detect-workmode.py" "$PROJECT_DIR/.claude/scripts/" 2>/dev/null || true
chmod +x "$PROJECT_DIR/.claude/scripts/"*.py 2>/dev/null || true
chmod +x "$PROJECT_DIR/.claude/scripts/"*.sh 2>/dev/null || true

# raven-core skill (always — it's the entry router)
cp "$SR_REPO_DIR/core/skills/raven-core/SKILL.md"       "$PROJECT_DIR/.claude/skills/raven-core/"
cp "$SR_REPO_DIR/core/skills/raven-core/rules/"*.md     "$PROJECT_DIR/.claude/skills/raven-core/rules/" 2>/dev/null || true

# ─── ALL 35 SKILLS ───────────────────────────────────────────────────────────
# Install every skill from core/skills/ — not just the original 8
SKILLS_INSTALLED=0
for skill_dir in "$SR_REPO_DIR/core/skills"/*/; do
    skill_name=$(basename "$skill_dir")
    skill_md="$skill_dir/SKILL.md"
    if [ -f "$skill_md" ]; then
        mkdir -p "$PROJECT_DIR/.claude/skills/$skill_name"
        cp "$skill_md" "$PROJECT_DIR/.claude/skills/$skill_name/"
        # rules/ subdirectory if present
        if [ -d "$skill_dir/rules" ]; then
            mkdir -p "$PROJECT_DIR/.claude/skills/$skill_name/rules"
            cp "$skill_dir/rules/"*.md "$PROJECT_DIR/.claude/skills/$skill_name/rules/" 2>/dev/null || true
        fi
        ((SKILLS_INSTALLED++)) || true
    fi
done

# ─── DOCS + TEMPLATES ────────────────────────────────────────────────────────
cp "$SR_REPO_DIR/templates/architecture.md"    "$PROJECT_DIR/.raven/architecture.md" 2>/dev/null || true
cp "$SR_REPO_DIR/templates/erd-template.md"    "$PROJECT_DIR/docs/erd-template.md"   2>/dev/null || true
cp "$SR_REPO_DIR/docs/observations/security_log.md" \
   "$PROJECT_DIR/docs/observations/security_log.md"  2>/dev/null || true
cp "$SR_REPO_DIR/docs/knowledge/"*.md \
   "$PROJECT_DIR/docs/knowledge/"                    2>/dev/null || true
cp "$SR_REPO_DIR/core/ci/"*  "$PROJECT_DIR/.raven/ci/" 2>/dev/null || true

# ─── GIT INIT + PRE-COMMIT HOOK ──────────────────────────────────────────────
[ ! -d "$PROJECT_DIR/.git" ] && git -C "$PROJECT_DIR" init --quiet && \
    git -C "$PROJECT_DIR" checkout -b main 2>/dev/null || true

cp "$SR_REPO_DIR/core/hooks/pre-commit" "$PROJECT_DIR/.git/hooks/pre-commit"
chmod +x "$PROJECT_DIR/.git/hooks/pre-commit"

echo -e "  ${G}✅ All files installed ($SKILLS_INSTALLED skills)${N}"
