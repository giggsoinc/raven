#!/usr/bin/env bash
# Raven (OSS) — Plugin Builder
# Builds raven-plugin-v{VERSION}.zip with OSS-safe scripts only.
# Excludes enterprise-only scripts (Hub agent, MCP guard, model discovery, policy sync, etc.)
#
# ZIP structure:
#   .claude-plugin/plugin.json
#   skills/{name}/SKILL.md
#   agents/{name}.md
#   scripts/{name}.py
#   settings.json
#   .model.env.template
#
# Usage: bash plugin/make-plugin.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="4.1.0"
ZIP_NAME="raven-plugin-v${VERSION}.zip"
ZIP_PATH="$SCRIPT_DIR/$ZIP_NAME"
TMP_DIR="$(mktemp -d)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Raven (OSS) — Plugin Builder"
echo "  Version: $VERSION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── plugin.json ──
mkdir -p "$TMP_DIR/.claude-plugin"
cp "$REPO_DIR/.claude-plugin/plugin.json" "$TMP_DIR/.claude-plugin/plugin.json"
echo "  ✅ .claude-plugin/plugin.json"

# ── Skills (at ZIP root) ──
mkdir -p "$TMP_DIR/skills"
cp -r "$REPO_DIR/skills/." "$TMP_DIR/skills/"
SKILL_COUNT=$(find "$TMP_DIR/skills" -name "SKILL.md" | wc -l | tr -d ' ')
echo "  ✅ $SKILL_COUNT skills"

# ── Agents (at ZIP root) ──
mkdir -p "$TMP_DIR/agents"
cp "$REPO_DIR/agents/"*.md "$TMP_DIR/agents/" 2>/dev/null || true
AGENT_COUNT=$(find "$TMP_DIR/agents" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "  ✅ $AGENT_COUNT agents"

# ── Slash commands (at ZIP root) ──
# Source of truth is core/commands/. Includes /andie + /andie-jr force-paths.
mkdir -p "$TMP_DIR/commands"
cp "$REPO_DIR/core/commands/"*.md "$TMP_DIR/commands/" 2>/dev/null || true
COMMAND_COUNT=$(find "$TMP_DIR/commands" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
echo "  ✅ $COMMAND_COUNT slash commands"

# ── OSS Hook scripts (at ZIP root) ──
# Cost-aware routing + guards. NO Hub. NO MCP governance. NO telemetry.
mkdir -p "$TMP_DIR/scripts"
for script in \
    session-start.py \
    triage-router.py \
    architect-router.py \
    log-overhead.py \
    model-router.py \
    token-guard.py \
    obsidian-log.py \
    cve-prompt-guard.py \
    cve-check.py \
    secret-scan.py \
    audit-log.py \
    emit-violation.py \
    notify.py \
    install-claudemd.py \
    db-guard.py; do
    src="$REPO_DIR/scripts/$script"
    if [[ -f "$src" ]]; then
        cp "$src" "$TMP_DIR/scripts/$script"
        chmod +x "$TMP_DIR/scripts/$script"
        echo "  ✅ scripts/$script"
    else
        echo "  ⚠️  scripts/$script — not found, skipping"
    fi
done

# ── settings.json (hook wiring) ──
cp "$SCRIPT_DIR/settings.json" "$TMP_DIR/settings.json"
echo "  ✅ settings.json (hook wiring)"

# ── .model.env.template (cost routing config) ──
cp "$REPO_DIR/.model.env.template" "$TMP_DIR/.model.env.template" 2>/dev/null && echo "  ✅ .model.env.template"

# ── Pre-flight validation ──
echo ""
echo "  🔍 Pre-flight validation..."
PREFLIGHT_FAIL=0
for skill_md in "$TMP_DIR/skills/"*/SKILL.md; do
    [[ -f "$skill_md" ]] || continue
    first=$(head -1 "$skill_md")
    if [[ "$first" != "---" ]]; then
        echo "  ❌ MISSING FRONTMATTER: skills/$(basename $(dirname $skill_md))/SKILL.md"
        PREFLIGHT_FAIL=1
    fi
done

if [[ $PREFLIGHT_FAIL -eq 1 ]]; then
    echo ""
    echo "  ❌ Pre-flight failed. Fix issues above before building."
    exit 1
fi

# ── Check for accidentally-included enterprise scripts ──
for marker in mcp-guard.py model-discover.py model-router-hook.py raven_agent.py \
              stream-signal.py policy-sync.py approval-request.py session-gate.py \
              tool-guard.py raven-skill-reminder.py; do
    if [[ -f "$TMP_DIR/scripts/$marker" ]]; then
        echo "  ❌ ENTERPRISE LEAK: scripts/$marker is in the OSS zip — abort"
        exit 1
    fi
done
echo "  ✅ Air-gap check: no enterprise infrastructure in zip"

# ── Build ──
cd "$TMP_DIR"
rm -f "$ZIP_PATH"
zip -rq "$ZIP_PATH" . -x "*.DS_Store" -x "*/__pycache__/*"

# ── Report ──
SIZE=$(du -h "$ZIP_PATH" | cut -f1)
echo ""
echo "  📦 Built: $ZIP_NAME"
echo "  📏 Size:  $SIZE"
echo ""
echo "  🔍 Validating..."
python3 -c "import json; json.load(open('$TMP_DIR/.claude-plugin/plugin.json'))" && echo "  ✅ plugin.json valid JSON"
python3 -c "import json; json.load(open('$TMP_DIR/settings.json'))" && echo "  ✅ settings.json valid JSON"
echo "  ✅ $SKILL_COUNT skills at ZIP root"
echo "  ✅ $AGENT_COUNT agents at ZIP root"
echo "  ✅ $COMMAND_COUNT commands at ZIP root"
SCRIPT_COUNT=$(find "$TMP_DIR/scripts" -name "*.py" | wc -l | tr -d ' ')
echo "  ✅ $SCRIPT_COUNT OSS scripts bundled"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done. Install:"
echo "  claude plugin install $ZIP_PATH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

rm -rf "$TMP_DIR"
