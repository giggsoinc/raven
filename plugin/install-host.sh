#!/usr/bin/env bash
# Copy Raven 5.5 host glue into a target project. One plugin, per-host files.
# Usage: bash install-host.sh [TARGET_DIR]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"
HOSTS="$ROOT/hosts"
if [[ ! -d "$HOSTS" ]]; then
  echo "install-host.sh: missing $HOSTS (unzip raven-plugin-v5.5.5.zip first)" >&2
  exit 1
fi

copy() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  cp "$src" "$dest"
  echo "  $dest"
}

echo "Raven host glue → $TARGET"
[[ -f "$HOSTS/AGENTS.md" ]] && copy "$HOSTS/AGENTS.md" "$TARGET/AGENTS.md"
[[ -f "$HOSTS/AGENTS.override.md" ]] && copy "$HOSTS/AGENTS.override.md" "$TARGET/AGENTS.override.md"
[[ -f "$HOSTS/CLAUDE.md" ]] && copy "$HOSTS/CLAUDE.md" "$TARGET/CLAUDE.md"
[[ -f "$HOSTS/GEMINI.md" ]] && copy "$HOSTS/GEMINI.md" "$TARGET/GEMINI.md"
[[ -f "$HOSTS/replit.md" ]] && copy "$HOSTS/replit.md" "$TARGET/replit.md"
[[ -f "$HOSTS/antigravity/agents.md" ]] && copy "$HOSTS/antigravity/agents.md" "$TARGET/.agents/agents.md"
[[ -f "$HOSTS/antigravity/agents.md" ]] && copy "$HOSTS/antigravity/agents.md" "$TARGET/.agents/AGENTS.md"
[[ -f "$HOSTS/cursor/raven-router.mdc" ]] && copy "$HOSTS/cursor/raven-router.mdc" "$TARGET/.cursor/rules/raven-router.mdc"
[[ -f "$HOSTS/windsurf/ide-boot.md" ]] && copy "$HOSTS/windsurf/ide-boot.md" "$TARGET/.windsurf/rules/ide-boot.md"
[[ -f "$HOSTS/vscode/raven-router.md" ]] && copy "$HOSTS/vscode/raven-router.md" "$TARGET/.vscode/raven-router.md"
[[ -f "$HOSTS/github/copilot-instructions.md" ]] && copy "$HOSTS/github/copilot-instructions.md" "$TARGET/.github/copilot-instructions.md"
if [[ -f "$HOSTS/claude/settings.json" ]]; then
  mkdir -p "$TARGET/.claude"
  if [[ ! -f "$TARGET/.claude/settings.json" ]]; then
    copy "$HOSTS/claude/settings.json" "$TARGET/.claude/settings.json"
  else
    echo "  keep $TARGET/.claude/settings.json — must include model-router.py --hook (stdin), not --prompt \$PROMPT"
  fi
fi
if [[ -d "$ROOT/scripts" ]]; then
  mkdir -p "$TARGET/scripts"
  cp -R "$ROOT/scripts/." "$TARGET/scripts/"
  echo "  $TARGET/scripts/ (engine)"
fi
echo "Done. Open the project in your IDE. Router: python3 scripts/ops/raven-first.py --prompt \"...\""
