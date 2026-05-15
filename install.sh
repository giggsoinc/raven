#!/bin/bash
# Raven — Global Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash
#
# What this does (one command, done forever):
#   1. Downloads Raven to ~/.raven/
#   2. Wires ALL 35 skills + 10 agents into Claude Code globally (~/.claude/)
#   3. Registers the MCP server globally
#   4. Makes raven-setup available as a command
#
# After this: open Claude Code in ANY project and Raven is already there.
# Per-project: run raven-setup once to create the manifest.
#
# Requires: git, bash, python3
# Claude Code recommended: anthropic.com/claude-code

set -e

G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[0;34m' W='\033[1m' N='\033[0m'

REPO="https://github.com/giggsoinc/raven.git"
RAVEN_DIR="$HOME/.raven"
CLAUDE_DIR="$HOME/.claude"
BIN_DIR="$HOME/.local/bin"

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  Raven — Global Install v2.9${N}"
echo -e "${W}  Guardrails before you ship.${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""

# ─── REQUIREMENTS ────────────────────────────────────────────────────────────
command -v git     &>/dev/null || { echo -e "${R}❌ git required — brew install git / apt install git${N}"; exit 1; }
command -v python3 &>/dev/null || { echo -e "${R}❌ python3 required — python.org${N}"; exit 1; }

CLAUDE_FOUND=true
command -v claude  &>/dev/null || {
    echo -e "${Y}⚠️  Claude Code not in PATH${N}"
    echo -e "   Install: ${B}https://claude.ai/download${N}"
    echo -e "   Raven will still install — run this again after Claude Code is set up."
    CLAUDE_FOUND=false
}

# ─── DOWNLOAD / UPDATE ───────────────────────────────────────────────────────
if [ -d "$RAVEN_DIR/.git" ]; then
    echo -e "${B}Updating existing Raven install...${N}"
    cd "$RAVEN_DIR" && git pull --quiet
    echo -e "${G}✅ Updated to latest${N}"
else
    echo -e "${B}Downloading Raven...${N}"
    git clone --quiet --depth=1 "$REPO" "$RAVEN_DIR"
    echo -e "${G}✅ Downloaded to $RAVEN_DIR${N}"
fi

# ─── WIRE INTO CLAUDE CODE GLOBALLY ─────────────────────────────────────────
echo ""
echo -e "${B}Installing into Claude Code (~/.claude/)...${N}"

mkdir -p "$CLAUDE_DIR"/{skills,agents,commands,scripts}

# ── All 35 skills ──
SKILLS_INSTALLED=0
for skill_dir in "$RAVEN_DIR/core/skills"/*/; do
    skill_name=$(basename "$skill_dir")
    skill_md="$skill_dir/SKILL.md"
    if [ -f "$skill_md" ]; then
        mkdir -p "$CLAUDE_DIR/skills/$skill_name"
        cp "$skill_md" "$CLAUDE_DIR/skills/$skill_name/SKILL.md"
        # Copy rules/ subdirectory if it exists
        if [ -d "$skill_dir/rules" ]; then
            mkdir -p "$CLAUDE_DIR/skills/$skill_name/rules"
            cp "$skill_dir/rules/"*.md "$CLAUDE_DIR/skills/$skill_name/rules/" 2>/dev/null || true
        fi
        ((SKILLS_INSTALLED++)) || true
    fi
done
echo -e "${G}✅ $SKILLS_INSTALLED skills installed${N}"

# ── All 10 agents ──
AGENTS_INSTALLED=0
for agent_md in "$RAVEN_DIR/core/agents/"*.md; do
    [ -f "$agent_md" ] || continue
    cp "$agent_md" "$CLAUDE_DIR/agents/"
    ((AGENTS_INSTALLED++)) || true
done
echo -e "${G}✅ $AGENTS_INSTALLED agents installed${N}"

# ── Commands ──
CMDS_INSTALLED=0
for cmd_md in "$RAVEN_DIR/core/commands/"*.md; do
    [ -f "$cmd_md" ] || continue
    cp "$cmd_md" "$CLAUDE_DIR/commands/"
    ((CMDS_INSTALLED++)) || true
done
echo -e "${G}✅ $CMDS_INSTALLED commands installed${N}"

# ── Scripts (Python tools) ──
for py in "$RAVEN_DIR/raven-core/"*.py; do
    [ -f "$py" ] || continue
    cp "$py" "$CLAUDE_DIR/scripts/"
    chmod +x "$CLAUDE_DIR/scripts/$(basename $py)"
done
for py in "$RAVEN_DIR/core/scripts/"*.py; do
    [ -f "$py" ] || continue
    cp "$py" "$CLAUDE_DIR/scripts/"
    chmod +x "$CLAUDE_DIR/scripts/$(basename $py)"
done
# Also copy detection script — used by raven-debug
cp "$RAVEN_DIR/setup/sr-detect-workmode.py" "$CLAUDE_DIR/scripts/" 2>/dev/null || true
echo -e "${G}✅ Scripts installed${N}"

# ── CLAUDE.md — global Raven instructions ──
GLOBAL_CLAUDE="$CLAUDE_DIR/CLAUDE.md"
RAVEN_MARKER="# RAVEN GLOBAL CONFIG"

if [ -f "$GLOBAL_CLAUDE" ] && grep -q "$RAVEN_MARKER" "$GLOBAL_CLAUDE" 2>/dev/null; then
    # Already there — update in place
    python3 - "$GLOBAL_CLAUDE" "$RAVEN_DIR/CLAUDE.md" << 'PYEOF'
import sys
target, source = sys.argv[1], sys.argv[2]
marker = "# RAVEN GLOBAL CONFIG"
raven_content = open(source).read()
existing = open(target).read()
# Replace everything from marker to end
if marker in existing:
    pre = existing[:existing.index(marker)]
    open(target,"w").write(pre + marker + "\n\n" + raven_content)
PYEOF
    echo -e "${G}✅ ~/.claude/CLAUDE.md updated${N}"
else
    # Append to existing or create
    {
        [ -f "$GLOBAL_CLAUDE" ] && echo "" && echo "" || true
        echo "$RAVEN_MARKER"
        echo ""
        cat "$RAVEN_DIR/CLAUDE.md"
    } >> "$GLOBAL_CLAUDE"
    echo -e "${G}✅ ~/.claude/CLAUDE.md configured${N}"
fi

# ── MCP server — register globally ──
MCP_JSON="$CLAUDE_DIR/mcp.json"
MCP_SERVER_PY="$RAVEN_DIR/mcp/server.py"

if [ ! -f "$MCP_SERVER_PY" ]; then
    # Try alternate paths
    MCP_SERVER_PY="$RAVEN_DIR/raven-core/server.py"
fi

if [ -f "$MCP_SERVER_PY" ] && command -v claude &>/dev/null; then
    # Register via claude CLI if available
    claude mcp add raven -- python3 "$MCP_SERVER_PY" 2>/dev/null && \
        echo -e "${G}✅ MCP server registered (raven_status, raven_cve_check, raven_debug...)${N}" || \
        echo -e "${Y}⚠️  MCP auto-register skipped — run manually: claude mcp add raven -- python3 $MCP_SERVER_PY${N}"
elif [ -f "$MCP_SERVER_PY" ]; then
    echo -e "${Y}⚠️  MCP server found but Claude Code not in PATH — register manually after Claude Code install:${N}"
    echo -e "     claude mcp add raven -- python3 $MCP_SERVER_PY"
fi

# ─── MAKE raven-setup GLOBALLY AVAILABLE ─────────────────────────────────────
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/raven-setup" << CMDEOF
#!/bin/bash
# Raven per-project setup — creates manifest + pre-commit hook
bash "$RAVEN_DIR/raven-setup.sh" "\$@"
CMDEOF
chmod +x "$BIN_DIR/raven-setup"

# Add BIN_DIR to PATH in shell rc
for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile"; do
    if [ -f "$rc" ] && ! grep -q "$BIN_DIR" "$rc" 2>/dev/null; then
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$rc"
        echo -e "${G}✅ Added $BIN_DIR to PATH in $(basename $rc)${N}"
        break
    fi
done
export PATH="$PATH:$BIN_DIR"

# ─── DONE ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${G}  ✅ Raven installed globally${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""
echo -e "  ${W}What's now available in every Claude Code session:${N}"
echo -e "  • 35 skills (Andie, all 23 specialists, raven-core…)"
echo -e "  • 10 guard agents (always on)"
echo -e "  • All commands (/raven-debug, /raven-review…)"
echo -e "  • MCP tools (raven_status, raven_cve_check…)"
echo ""
echo -e "  ${W}Per-project setup (run once per project):${N}"
echo -e "  ${B}cd YourProject && raven-setup${N}"
echo ""
echo -e "  ${W}Then open Claude Code:${N}"
echo -e "  ${B}claude .${N}"
echo ""
echo -e "  ${W}To update Raven later:${N}"
echo -e "  ${B}curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash${N}"
echo -e "  (re-running install.sh updates and re-wires everything)"
echo ""

if [ "$CLAUDE_FOUND" = false ]; then
    echo -e "${Y}  ⚠️  Install Claude Code then re-run this script to register the MCP server.${N}"
    echo -e "     Download: ${B}https://claude.ai/download${N}"
    echo ""
fi
