#!/bin/bash
# Raven — Enterprise Installer
# Run as root/sudo on the machine IT manages.
#
# What this does:
#   1. Installs Raven to /usr/local/raven/ (system-wide, all users)
#   2. Creates managed-mcp.json at the Claude Code system path
#      → every developer on this machine gets Raven MCP auto-loaded
#   3. Creates managed-settings.json (hooks, permissions)
#   4. Interactively creates manifest.org.json (org-level locked rules)
#   5. Optionally provisions ~/.claude/ for all existing users
#
# Usage:
#   sudo bash install-enterprise.sh
#
# Requirements: git, python3

set -e

G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[0;34m' W='\033[1m' N='\033[0m'

# ─── PATHS ───────────────────────────────────────────────────────────────────
RAVEN_SYSTEM="/usr/local/raven"
RAVEN_MCP="$RAVEN_SYSTEM/mcp/server.py"

# Claude Code managed paths — drop files here, every user picks them up
if [[ "$OSTYPE" == "darwin"* ]]; then
    MANAGED_DIR="/Library/Application Support/ClaudeCode"
else
    MANAGED_DIR="/etc/claude-code"
fi

REPO="https://github.com/giggsoinc/raven.git"

# ─── ROOT CHECK ──────────────────────────────────────────────────────────────
if [[ "$EUID" -ne 0 ]]; then
    echo -e "${R}❌ Run as root: sudo bash install-enterprise.sh${N}"
    exit 1
fi

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  Raven — Enterprise Install v2.9${N}"
echo -e "${W}  IT / Admin deployment${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""

# ─── REQUIREMENTS ────────────────────────────────────────────────────────────
command -v git     &>/dev/null || { echo -e "${R}❌ git required${N}"; exit 1; }
command -v python3 &>/dev/null || { echo -e "${R}❌ python3 required${N}"; exit 1; }

# ─── DOWNLOAD / UPDATE ───────────────────────────────────────────────────────
if [ -d "$RAVEN_SYSTEM/.git" ]; then
    echo -e "${B}Updating Raven at $RAVEN_SYSTEM ...${N}"
    git -C "$RAVEN_SYSTEM" pull --quiet
    echo -e "${G}✅ Updated${N}"
else
    echo -e "${B}Installing Raven to $RAVEN_SYSTEM ...${N}"
    git clone --quiet --depth=1 "$REPO" "$RAVEN_SYSTEM"
    echo -e "${G}✅ Installed to $RAVEN_SYSTEM${N}"
fi

# Make scripts executable
chmod +x "$RAVEN_SYSTEM/raven-setup.sh" 2>/dev/null || true
find "$RAVEN_SYSTEM" -name "*.py" -exec chmod +x {} \; 2>/dev/null || true

# ─── MANAGED-MCP.JSON ────────────────────────────────────────────────────────
echo ""
echo -e "${B}Creating managed-mcp.json → $MANAGED_DIR${N}"
mkdir -p "$MANAGED_DIR"

cat > "$MANAGED_DIR/managed-mcp.json" << MCPEOF
{
  "_comment": "Raven Enterprise MCP — auto-loaded for all Claude Code users on this machine. Do not edit manually. Re-run install-enterprise.sh to update.",
  "mcpServers": {
    "raven": {
      "type":    "stdio",
      "command": "python3",
      "args":    ["$RAVEN_MCP"],
      "env":     {}
    }
  }
}
MCPEOF

echo -e "${G}✅ managed-mcp.json → $MANAGED_DIR/managed-mcp.json${N}"
echo -e "   MCP server path: ${W}$RAVEN_MCP${N}"

# ─── MANAGED-SETTINGS.JSON ───────────────────────────────────────────────────
echo ""
echo -e "${B}Creating managed-settings.json (hooks + permissions)...${N}"

cat > "$MANAGED_DIR/managed-settings.json" << SETTINGSEOF
{
  "_comment": "Raven Enterprise — managed settings. Controls hooks and permissions for all users.",
  "permissions": {
    "deny": [
      "Bash(curl * | bash)",
      "Bash(curl * | sh)",
      "Bash(wget * | bash)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $RAVEN_SYSTEM/raven-core/tool-guard.py"
          }
        ]
      }
    ]
  }
}
SETTINGSEOF

echo -e "${G}✅ managed-settings.json → $MANAGED_DIR/managed-settings.json${N}"

# ─── ORG MANIFEST ────────────────────────────────────────────────────────────
echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  Org Manifest — locked rules for all projects${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""
echo -e "  These fields will be locked in every developer's project manifest."
echo -e "  Developers cannot override them."
echo ""

_ask() {
    echo -e "  ${B}$1${N}" >/dev/tty
    [ -n "$2" ] && echo -e "  ${Y}Default: $2${N}" >/dev/tty
    read -p "  → " V </dev/tty
    echo "${V:-$2}"
}

ORG_NAME=$(_ask "Organisation name:" "MyOrg")
ORG_EMAIL=$(_ask "IT / architect email (audit trail author):" "it@example.com")

echo ""
echo -e "  ${B}Approval mode:${N}" >/dev/tty
echo -e "  1) first_responder  — first to approve wins (default)" >/dev/tty
echo -e "  2) majority_vote    — majority of architects must agree" >/dev/tty
echo -e "  3) owner_only       — only the project owner can approve" >/dev/tty
read -p "  → " AM </dev/tty
case "$AM" in
    2) APPROVAL_MODE="majority_vote" ;;
    3) APPROVAL_MODE="owner_only" ;;
    *) APPROVAL_MODE="first_responder" ;;
esac

echo ""
echo -e "  ${B}Token control:${N}" >/dev/tty
echo -e "  1) per_developer  — each dev has their own quota (default)" >/dev/tty
echo -e "  2) per_project    — project pool shared by all devs" >/dev/tty
echo -e "  3) per_team       — team pool" >/dev/tty
read -p "  → " TC </dev/tty
case "$TC" in
    2) TOKEN_CONTROL="per_project" ;;
    3) TOKEN_CONTROL="per_team" ;;
    *) TOKEN_CONTROL="per_developer" ;;
esac

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

ORG_NAME_VAL="$ORG_NAME" ORG_EMAIL_VAL="$ORG_EMAIL" \
APPROVAL_MODE_VAL="$APPROVAL_MODE" TOKEN_CONTROL_VAL="$TOKEN_CONTROL" \
TS_VAL="$TS" RAVEN_SYSTEM_VAL="$RAVEN_SYSTEM" \
python3 - << 'PYEOF'
import json, os

org_name      = os.environ["ORG_NAME_VAL"]
org_email     = os.environ["ORG_EMAIL_VAL"]
approval_mode = os.environ["APPROVAL_MODE_VAL"]
token_control = os.environ["TOKEN_CONTROL_VAL"]
ts            = os.environ["TS_VAL"]
raven_system  = os.environ["RAVEN_SYSTEM_VAL"]

org_manifest = {
  "_layer":  "org",
  "_locked": [
    "standards",
    "approval_mode",
    "guard.enabled",
    "tokens.control"
  ],
  "project":       org_name,
  "version":       "1.0",
  "standards":     "raven-v2.9",
  "approval_mode": approval_mode,
  "guard": {
    "enabled": True,
    "git":      {"force_push": "hard_block"},
    "infra":    {"terraform_state": "hard_block"},
    "firewall": {"open_world": "hard_block"},
    "db":       {"mass_deletion_threshold": 100, "truncation": "hard_block"}
  },
  "tokens": {
    "control":   token_control,
    "warnings":  [25, 50, 75, 80, 90, 95]
  },
  "style": {
    "max_lines_per_file":      150,
    "require_type_hints":      True,
    "require_docstrings":      True,
    "forbid_print_statements": True
  },
  "changelog": [{
    "version":    "1.0",
    "changed_by": org_email,
    "changed_at": ts,
    "changes":    f"Enterprise org manifest init — {org_name}",
    "pr":         "pending"
  }]
}

org_manifest_path = f"{raven_system}/manifest.org.json"
with open(org_manifest_path, "w") as f:
    json.dump(org_manifest, f, indent=2)

print(f"written to {org_manifest_path}")
PYEOF

echo -e "${G}✅ manifest.org.json → $RAVEN_SYSTEM/manifest.org.json${N}"

# ─── PROVISION EXISTING USERS ────────────────────────────────────────────────
echo ""
echo -e "  ${B}Provision skills/agents to existing users' ~/.claude/ directories?${N}" >/dev/tty
echo -e "  ${Y}This wires all 35 skills for every existing developer on this machine.${N}" >/dev/tty
echo -e "  1) Yes — provision all users now" >/dev/tty
echo -e "  2) No  — developers run install.sh themselves on first login" >/dev/tty
read -p "  → " PROVISION </dev/tty

if [[ "$PROVISION" == "1" ]]; then
    echo ""
    echo -e "${B}Provisioning all users...${N}"
    PROVISIONED=0

    for user_home in /home/* /Users/*; do
        [ -d "$user_home" ] || continue
        username=$(basename "$user_home")
        [ "$username" = "root" ] && continue
        [ "$username" = "lost+found" ] && continue

        user_claude="$user_home/.claude"
        mkdir -p "$user_claude"/{skills,agents,commands,scripts}

        # Copy all 35 skills
        for skill_dir in "$RAVEN_SYSTEM/core/skills"/*/; do
            skill_name=$(basename "$skill_dir")
            skill_md="$skill_dir/SKILL.md"
            [ -f "$skill_md" ] || continue
            mkdir -p "$user_claude/skills/$skill_name"
            cp "$skill_md" "$user_claude/skills/$skill_name/"
            [ -d "$skill_dir/rules" ] && {
                mkdir -p "$user_claude/skills/$skill_name/rules"
                cp "$skill_dir/rules/"*.md "$user_claude/skills/$skill_name/rules/" 2>/dev/null || true
            }
        done

        # Agents
        cp "$RAVEN_SYSTEM/core/agents/"*.md "$user_claude/agents/" 2>/dev/null || true
        # Commands
        cp "$RAVEN_SYSTEM/core/commands/"*.md "$user_claude/commands/" 2>/dev/null || true
        # Scripts
        cp "$RAVEN_SYSTEM/raven-core/"*.py "$user_claude/scripts/" 2>/dev/null || true
        cp "$RAVEN_SYSTEM/core/scripts/"*.py "$user_claude/scripts/" 2>/dev/null || true
        cp "$RAVEN_SYSTEM/setup/sr-detect-workmode.py" "$user_claude/scripts/" 2>/dev/null || true

        # CLAUDE.md
        RAVEN_MARKER="# RAVEN GLOBAL CONFIG"
        GLOBAL_CLAUDE="$user_claude/CLAUDE.md"
        if [ -f "$GLOBAL_CLAUDE" ] && grep -q "$RAVEN_MARKER" "$GLOBAL_CLAUDE" 2>/dev/null; then
            python3 -c "
import sys
target, source = '$GLOBAL_CLAUDE', '$RAVEN_SYSTEM/CLAUDE.md'
marker = '# RAVEN GLOBAL CONFIG'
raven_content = open(source).read()
existing = open(target).read()
if marker in existing:
    pre = existing[:existing.index(marker)]
    open(target,'w').write(pre + marker + '\n\n' + raven_content)
" 2>/dev/null || true
        else
            {
                [ -f "$GLOBAL_CLAUDE" ] && echo "" && echo "" || true
                echo "$RAVEN_MARKER"
                echo ""
                cat "$RAVEN_SYSTEM/CLAUDE.md"
            } >> "$GLOBAL_CLAUDE"
        fi

        # Fix ownership
        chown -R "$username" "$user_claude" 2>/dev/null || true

        echo -e "  ${G}✅ $username${N}"
        ((PROVISIONED++)) || true
    done

    echo ""
    echo -e "${G}✅ Provisioned $PROVISIONED users${N}"
    echo -e "   New users: add 'bash $RAVEN_SYSTEM/install.sh' to login provisioning${N}"
fi

# ─── raven-setup global command ──────────────────────────────────────────────
ln -sf "$RAVEN_SYSTEM/raven-setup.sh" /usr/local/bin/raven-setup 2>/dev/null || \
    cp "$RAVEN_SYSTEM/raven-setup.sh" /usr/local/bin/raven-setup
chmod +x /usr/local/bin/raven-setup
echo -e "${G}✅ raven-setup available system-wide${N}"

# ─── DONE ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${G}  ✅ Raven Enterprise deployed${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""
echo -e "  ${W}What's deployed:${N}"
echo -e "  • Raven installed at:    ${B}$RAVEN_SYSTEM${N}"
echo -e "  • MCP auto-loads from:   ${B}$MANAGED_DIR/managed-mcp.json${N}"
echo -e "  • Org manifest at:       ${B}$RAVEN_SYSTEM/manifest.org.json${N}"
echo -e "  • raven-setup command:   ${B}/usr/local/bin/raven-setup${N}"
echo ""
echo -e "  ${W}Developer day 1 — nothing to install:${N}"
echo -e "  ${B}cd MyProject && raven-setup${N}"
echo -e "  ${B}claude .${N}"
echo ""
echo -e "  ${W}Update Raven for all users:${N}"
echo -e "  ${B}sudo bash $RAVEN_SYSTEM/install-enterprise.sh${N}"
echo ""
echo -e "  ${W}For new users joining the org:${N}"
echo -e "  Add to your onboarding script:"
echo -e "  ${B}sudo bash $RAVEN_SYSTEM/install.sh${N}"
echo ""
