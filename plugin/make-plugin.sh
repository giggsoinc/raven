#!/usr/bin/env bash
# Raven OSS — one plugin zip. Version from raven-core/VERSION.
# Usage: bash plugin/make-plugin.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="5.5.6"
VERSION="$(tr -d '[:space:]' < "$REPO_DIR/raven-core/VERSION")"
ZIP_NAME="raven-plugin-v${VERSION}.zip"
ZIP_PATH="$SCRIPT_DIR/$ZIP_NAME"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Raven plugin  v${VERSION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p "$TMP_DIR/.claude-plugin"
cp "$REPO_DIR/.claude-plugin/plugin.json" "$TMP_DIR/.claude-plugin/plugin.json"
cp "$REPO_DIR/plugin/plugin.json" "$TMP_DIR/plugin.json"

mkdir -p "$TMP_DIR/skills"
cp -R "$REPO_DIR/skills/." "$TMP_DIR/skills/"
SKILL_COUNT="$(find "$TMP_DIR/skills" -name SKILL.md | wc -l | tr -d ' ')"

mkdir -p "$TMP_DIR/agents"
cp "$REPO_DIR/agents/"*.md "$TMP_DIR/agents/" 2>/dev/null || true
AGENT_COUNT="$(find "$TMP_DIR/agents" -name '*.md' | wc -l | tr -d ' ')"

mkdir -p "$TMP_DIR/commands"
cp "$REPO_DIR/core/commands/"*.md "$TMP_DIR/commands/" 2>/dev/null || true
COMMAND_COUNT="$(find "$TMP_DIR/commands" -name '*.md' | wc -l | tr -d ' ')"

mkdir -p "$TMP_DIR/scripts"
for sub in session routing memory guards ops dashboard; do
  if [[ -d "$REPO_DIR/scripts/$sub" ]]; then
    cp -R "$REPO_DIR/scripts/$sub" "$TMP_DIR/scripts/$sub"
  fi
done
for f in "$REPO_DIR/scripts/"*.py "$REPO_DIR/scripts/"*.json; do
  [[ -f "$f" ]] || continue
  cp "$f" "$TMP_DIR/scripts/"
done
cp "$SCRIPT_DIR/settings.json" "$TMP_DIR/settings.json"
cp "$REPO_DIR/.model.env.template" "$TMP_DIR/.model.env.template" 2>/dev/null || true
cp "$REPO_DIR/templates/routing-policy.example.json" "$TMP_DIR/routing-policy.example.json" 2>/dev/null || true

if [[ -d "$REPO_DIR/assets/kg-icons" ]]; then
  mkdir -p "$TMP_DIR/assets/kg-icons"
  cp "$REPO_DIR/assets/kg-icons/"*.svg "$TMP_DIR/assets/kg-icons/" 2>/dev/null || true
fi

# Host glue — same zip, not Claude-only
mkdir -p "$TMP_DIR/hosts/cursor" "$TMP_DIR/hosts/windsurf" "$TMP_DIR/hosts/antigravity" "$TMP_DIR/hosts/claude" "$TMP_DIR/hosts/vscode" "$TMP_DIR/hosts/github"
cp "$REPO_DIR/AGENTS.md" "$TMP_DIR/hosts/AGENTS.md"
cp "$REPO_DIR/AGENTS.override.md" "$TMP_DIR/hosts/AGENTS.override.md" 2>/dev/null || true
cp "$REPO_DIR/CLAUDE.md" "$TMP_DIR/hosts/CLAUDE.md"
cp "$REPO_DIR/GEMINI.md" "$TMP_DIR/hosts/GEMINI.md" 2>/dev/null || true
cp "$REPO_DIR/replit.md" "$TMP_DIR/hosts/replit.md" 2>/dev/null || true
cp "$REPO_DIR/.agents/agents.md" "$TMP_DIR/hosts/antigravity/agents.md" 2>/dev/null || true
cp "$REPO_DIR/scripts/raven-python.sh" "$TMP_DIR/scripts/raven-python.sh"
chmod +x "$TMP_DIR/scripts/raven-python.sh"
cp "$REPO_DIR/.cursor/rules/raven-router.mdc" "$TMP_DIR/hosts/cursor/raven-router.mdc" 2>/dev/null || true
cp "$REPO_DIR/.windsurf/rules/ide-boot.md" "$TMP_DIR/hosts/windsurf/ide-boot.md" 2>/dev/null || true
cp "$REPO_DIR/.vscode/raven-router.md" "$TMP_DIR/hosts/vscode/raven-router.md" 2>/dev/null || true
cp "$REPO_DIR/.github/copilot-instructions.md" "$TMP_DIR/hosts/github/copilot-instructions.md" 2>/dev/null || true
cp "$REPO_DIR/.claude/settings.json" "$TMP_DIR/hosts/claude/settings.json"
cp "$SCRIPT_DIR/install-host.sh" "$TMP_DIR/install-host.sh"
chmod +x "$TMP_DIR/install-host.sh"
cp "$SCRIPT_DIR/HOSTS.md" "$TMP_DIR/HOSTS.md"
cp "$SCRIPT_DIR/README.md" "$TMP_DIR/README.md"
echo "$VERSION" > "$TMP_DIR/VERSION"

echo "  skills=$SKILL_COUNT agents=$AGENT_COUNT commands=$COMMAND_COUNT"

PREFLIGHT_FAIL=0
for skill_md in "$TMP_DIR/skills/"*/SKILL.md; do
  [[ -f "$skill_md" ]] || continue
  first="$(head -1 "$skill_md")"
  if [[ "$first" != "---" ]]; then
    echo "  ❌ MISSING FRONTMATTER: $skill_md"
    PREFLIGHT_FAIL=1
  fi
done
if [[ "$PREFLIGHT_FAIL" -eq 1 ]]; then
  exit 1
fi
for marker in mcp-guard.py model-discover.py raven_agent.py stream-signal.py; do
  if [[ -f "$TMP_DIR/scripts/$marker" ]]; then
    echo "  ❌ ENTERPRISE LEAK: $marker" >&2
    exit 1
  fi
done

cd "$TMP_DIR"
rm -f "$ZIP_PATH"
zip -rq "$ZIP_PATH" . -x "*.DS_Store" -x "*/__pycache__/*" -x "*.pyc"
SIZE="$(du -h "$ZIP_PATH" | cut -f1)"
echo "  📦 $ZIP_PATH ($SIZE)"
python3 -c "import json; json.load(open('$TMP_DIR/.claude-plugin/plugin.json'))"
python3 -c "import json; json.load(open('$TMP_DIR/settings.json'))"
echo "  install: unzip then  claude plugin install <dir>  OR  bash install-host.sh <project>"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
