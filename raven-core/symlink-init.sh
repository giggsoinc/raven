#!/usr/bin/env bash
# raven-core/symlink-init.sh
# Wires engine scripts as symlinks on first install.
# Run once after cloning. Never copies files — always references raven-core/.
#
# Usage: bash raven-core/symlink-init.sh [--dry-run]
#
# ⚠️  DO NOT DELETE FILES FROM raven-core/
# All other script locations are symlinks pointing here.
# Deleting a file here breaks all of them silently.

set -e
DRY_RUN=false
[[ "$1" == "--dry-run" ]] && DRY_RUN=true

CORE_DIR="$(cd "$(dirname "$0")" && pwd)"
RAVEN_DIR="$(dirname "$CORE_DIR")"

ENGINE_SCRIPTS=(
  cve-check.py
  secret-scan.py
  audit-log.py
  emit-violation.py
  db-guard.py
  schema-guard.py
  cve-prompt-guard.py
)

TARGETS=(
  "$RAVEN_DIR/core/scripts"
  "$RAVEN_DIR/plugin/scripts"
  "$RAVEN_DIR/.claude/scripts"
)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Raven — Symlink Init"
echo "  Source of truth: raven-core/"
[[ "$DRY_RUN" == "true" ]] && echo "  DRY RUN — no files written"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Pre-flight: verify ALL source files exist before touching anything ─────────
echo "  🔍 Verifying raven-core/ source files..."
MISSING=0
for SCRIPT in "${ENGINE_SCRIPTS[@]}"; do
  if [[ ! -f "$CORE_DIR/$SCRIPT" ]]; then
    echo "  ❌ MISSING: raven-core/$SCRIPT"
    MISSING=$((MISSING + 1))
  fi
done

if [[ $MISSING -gt 0 ]]; then
  echo ""
  echo "  ⛔ HARD STOP: $MISSING source file(s) missing from raven-core/"
  echo "     raven-core/ is the only real copy of these scripts."
  echo "     Do NOT recreate them outside raven-core/."
  echo "     Restore the missing files to raven-core/ first, then re-run this script."
  echo ""
  exit 1
fi
echo "  ✅ All source files present"
echo ""

# ── Create symlinks ────────────────────────────────────────────────────────────
for TARGET in "${TARGETS[@]}"; do
  echo "▶ $(realpath --relative-to="$RAVEN_DIR" "$TARGET" 2>/dev/null || echo "$TARGET")"
  [[ "$DRY_RUN" == "false" ]] && mkdir -p "$TARGET"
  for SCRIPT in "${ENGINE_SCRIPTS[@]}"; do
    SRC="$CORE_DIR/$SCRIPT"
    DEST="$TARGET/$SCRIPT"
    if [[ "$DRY_RUN" == "false" ]]; then
      rm -f "$DEST"
      ln -sf "$SRC" "$DEST"
    fi
    echo "  ✅ $SCRIPT → raven-core/$SCRIPT"
  done
done

echo ""
echo "  ⚠️  Remember: edit scripts ONLY in raven-core/"
echo "  Done. All locations update automatically via symlinks."
echo ""
