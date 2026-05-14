#!/usr/bin/env bash
# bundle.sh — sync engine scripts and plugin content across all platform repos
# Lives at raven-core/bundle.sh inside the main giggsoinc/raven repo
#
# Usage: bash raven-core/bundle.sh [--dry-run]

set -e

DRY_RUN=false
[[ "$1" == "--dry-run" ]] && DRY_RUN=true

# Resolve paths relative to this script's location
CORE_DIR="$(cd "$(dirname "$0")" && pwd)"       # .../RAVEN/raven-core/
RAVEN_DIR="$(dirname "$CORE_DIR")"              # .../RAVEN/
ANTIGRAVITY_DIR="$(cd "$CORE_DIR/../../../.." && pwd)"  # .../AntiGravity_Projects/
CURRENT_VERSION="$(cat "$CORE_DIR/VERSION" 2>/dev/null || echo "unknown")"

ENGINE_SCRIPTS=("cve-check.py" "secret-scan.py" "audit-log.py" "emit-violation.py" "db-guard.py")
MCP_SCRIPT="server.py"
ANDIE_SRC="${HOME}/.claude/skills/andie/SKILL.md"
TOOLS_SRC="${HOME}/.claude/skills/tools-landscape"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Raven — Bundle"
echo "  Version: $CURRENT_VERSION"
[[ "$DRY_RUN" == "true" ]] && echo "  DRY RUN — no files written"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

bundle_scripts() {
  local LABEL="$1"
  local DEST="$2"
  echo "▶ $LABEL → $DEST"
  [[ "$DRY_RUN" == "false" ]] && mkdir -p "$DEST"
  for SCRIPT in "${ENGINE_SCRIPTS[@]}"; do
    SRC="$CORE_DIR/$SCRIPT"
    if [[ -f "$SRC" ]]; then
      [[ "$DRY_RUN" == "false" ]] && cp "$SRC" "$DEST/$SCRIPT" && chmod +x "$DEST/$SCRIPT"
      echo "  ✅ $SCRIPT"
    else
      echo "  ❌ $SCRIPT — not found in raven-core/"
    fi
  done
  if [[ "$DRY_RUN" == "false" ]]; then
    RAVEN_META_DIR="$(dirname "$DEST")/.raven"
    mkdir -p "$RAVEN_META_DIR"
    echo "$CURRENT_VERSION" > "$RAVEN_META_DIR/raven_version"
    echo "  ✅ .raven/raven_version → $CURRENT_VERSION"
  fi
}

bundle_mcp() {
  local LABEL="$1"
  local DEST="$2"
  echo "▶ $LABEL (MCP) → $DEST"
  if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$DEST"
    cp "$CORE_DIR/$MCP_SCRIPT" "$DEST/$MCP_SCRIPT"
    chmod +x "$DEST/$MCP_SCRIPT"
  fi
  echo "  ✅ $MCP_SCRIPT"
}

# ── Engine scripts → platform repos ─────────────────────────────────────────
bundle_scripts "raven (codex)"  "$RAVEN_DIR/codex/scripts"
bundle_scripts "raven-action"   "$ANTIGRAVITY_DIR/raven-action/scripts"

echo ""

# ── MCP server ───────────────────────────────────────────────────────────────
bundle_mcp "raven (codex)"   "$RAVEN_DIR/codex/mcp"
bundle_mcp "raven (.claude)" "$RAVEN_DIR/.claude/scripts"

# ── Hook scripts: core/scripts/ → .claude/scripts/ ───────────────────────────
echo "▶ Hook scripts sync (core/scripts/ → .claude/scripts/)"
HOOK_SCRIPTS_SRC="$RAVEN_DIR/core/scripts"
HOOK_SCRIPTS_DST="$RAVEN_DIR/.claude/scripts"
if [[ -d "$HOOK_SCRIPTS_SRC" ]]; then
  [[ "$DRY_RUN" == "false" ]] && mkdir -p "$HOOK_SCRIPTS_DST"
  for f in "$HOOK_SCRIPTS_SRC"/*.py "$HOOK_SCRIPTS_SRC"/*.sh; do
    [[ -f "$f" ]] || continue
    [[ "$DRY_RUN" == "false" ]] && cp "$f" "$HOOK_SCRIPTS_DST/" && chmod +x "$HOOK_SCRIPTS_DST/$(basename "$f")"
    echo "  ✅ $(basename "$f")"
  done
else
  echo "  ⚠️  core/scripts/ not found — skipping"
fi

echo ""

# ── Andie skill sync ─────────────────────────────────────────────────────────
echo "▶ Andie skill sync"
ANDIE_TARGETS=(
  "$RAVEN_DIR/core/skills/andie/SKILL.md"
  "$RAVEN_DIR/skills/andie/SKILL.md"
)
if [[ ! -f "$ANDIE_SRC" ]]; then
  echo "  ⚠️  Andie SKILL.md not found at $ANDIE_SRC — skipping"
else
  for DEST in "${ANDIE_TARGETS[@]}"; do
    if [[ "$DRY_RUN" == "false" ]]; then
      mkdir -p "$(dirname "$DEST")"
      cp "$ANDIE_SRC" "$DEST"
    fi
    echo "  ✅ $(echo "$DEST" | sed "s|$RAVEN_DIR/||")"
  done
fi

# ── Tools landscape skill sync ───────────────────────────────────────────────
echo "▶ Tools landscape skill sync"
TOOLS_TARGETS=(
  "$RAVEN_DIR/core/skills/tools-landscape"
  "$RAVEN_DIR/skills/tools-landscape"
)
if [[ ! -d "$TOOLS_SRC" ]]; then
  echo "  ⚠️  tools-landscape not found at $TOOLS_SRC — skipping"
else
  for DEST in "${TOOLS_TARGETS[@]}"; do
    if [[ "$DRY_RUN" == "false" ]]; then
      mkdir -p "$DEST"
      cp "$TOOLS_SRC/SKILL.md" "$DEST/SKILL.md"
      [[ -f "$TOOLS_SRC/registry.json" ]] && cp "$TOOLS_SRC/registry.json" "$DEST/registry.json"
    fi
    echo "  ✅ $(echo "$DEST" | sed "s|$RAVEN_DIR/||") (SKILL.md + registry.json)"
  done
fi

echo ""

# ── Plugin content sync: core/ → root skills/agents/commands/ ────────────────
echo "▶ Plugin content sync (core/ → root)"
PLUGIN_SRC="$RAVEN_DIR/core"

if [[ -d "$PLUGIN_SRC/skills" ]]; then
  for skill_dir in "$PLUGIN_SRC/skills"/*/; do
    skill_name="$(basename "$skill_dir")"
    if [[ "$DRY_RUN" == "false" ]]; then
      mkdir -p "$RAVEN_DIR/skills/$skill_name"
      [[ -f "$skill_dir/SKILL.md" ]] && cp "$skill_dir/SKILL.md" "$RAVEN_DIR/skills/$skill_name/SKILL.md"
      if [[ -d "$skill_dir/rules" ]]; then
        mkdir -p "$RAVEN_DIR/skills/$skill_name/rules"
        cp "$skill_dir/rules/"*.md "$RAVEN_DIR/skills/$skill_name/rules/" 2>/dev/null || true
      fi
    fi
    echo "  ✅ skills/$skill_name"
  done
fi

if [[ "$DRY_RUN" == "false" ]]; then
  mkdir -p "$RAVEN_DIR/agents"
  cp "$PLUGIN_SRC/agents/"*.md "$RAVEN_DIR/agents/" 2>/dev/null || true
  mkdir -p "$RAVEN_DIR/commands"
  cp "$PLUGIN_SRC/commands/"*.md "$RAVEN_DIR/commands/" 2>/dev/null || true
fi
echo "  ✅ agents/   ($(ls "$RAVEN_DIR/agents/" 2>/dev/null | wc -l | tr -d ' ') files)"
echo "  ✅ commands/ ($(ls "$RAVEN_DIR/commands/" 2>/dev/null | wc -l | tr -d ' ') files)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done."
echo "  Install: claude plugin install giggsoinc/raven"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
