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
ORACLE_SKILLS_REPO="https://github.com/giggsoinc/skills"  # source of oracle-* skills

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
  # Commands migrate to skills/<name>/SKILL.md (preferred format)
  for cmd in "$PLUGIN_SRC/commands/"*.md; do
    [[ -f "$cmd" ]] || continue
    cmd_name="$(basename "$cmd" .md)"
    mkdir -p "$RAVEN_DIR/skills/$cmd_name"
    cp "$cmd" "$RAVEN_DIR/skills/$cmd_name/SKILL.md"
  done
fi
echo "  ✅ agents/   ($(ls "$RAVEN_DIR/agents/" 2>/dev/null | wc -l | tr -d ' ') files)"
echo "  ✅ commands → skills/ ($(ls "$RAVEN_DIR/commands/" 2>/dev/null | wc -l | tr -d ' ') migrated)"

# ── Oracle skills sync (giggsoinc/skills → skills/oracle-*-specialist) ───────
echo "▶ Oracle skills sync (giggsoinc/skills)"
ORACLE_SKILL_MAP=(
  "apex:oracle-apex-specialist"
  "db:oracle-db-specialist"
  "graal:oracle-graal-specialist"
  "fusion:oracle-fusion-specialist"
  "oci:oracle-oci-specialist"
  "apex/apexlang:oracle-apexlang-specialist"
)
ORACLE_TMP="$(mktemp -d)"
if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  gh repo clone giggsoinc/skills "$ORACLE_TMP/skills" -- --depth=1 -q 2>/dev/null && ORACLE_CLONED=true || ORACLE_CLONED=false
else
  ORACLE_CLONED=false
fi

if [[ "$ORACLE_CLONED" == "true" ]]; then
  for entry in "${ORACLE_SKILL_MAP[@]}"; do
    src_path="${entry%%:*}"
    skill_name="${entry##*:}"
    SRC="$ORACLE_TMP/skills/$src_path"
    if [[ -d "$SRC" ]]; then
      if [[ "$DRY_RUN" == "false" ]]; then
        mkdir -p "$RAVEN_DIR/skills/$skill_name"
        mkdir -p "$RAVEN_DIR/plugin/skills/$skill_name"
        # Copy all .md files, preserving subdirectory structure
        find "$SRC" -name "*.md" | while read f; do
          rel="${f#$SRC/}"
          dest_dir="$RAVEN_DIR/skills/$skill_name/$(dirname "$rel")"
          mkdir -p "$dest_dir"
          cp "$f" "$dest_dir/"
          dest_dir2="$RAVEN_DIR/plugin/skills/$skill_name/$(dirname "$rel")"
          mkdir -p "$dest_dir2"
          cp "$f" "$dest_dir2/"
        done
      fi
      count=$(find "$RAVEN_DIR/skills/$skill_name" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
      echo "  ✅ $skill_name ($count .md files)"
    else
      echo "  ⚠️  $src_path not found in giggsoinc/skills — skipping"
    fi
  done
else
  echo "  ⚠️  giggsoinc/skills clone failed — Oracle skills not synced (run manually)"
  echo "     Manual sync: cd /tmp && gh repo clone giggsoinc/skills && bash raven-core/bundle.sh"
fi
rm -rf "$ORACLE_TMP"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done."
echo "  Install: claude plugin install giggsoinc/raven"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
