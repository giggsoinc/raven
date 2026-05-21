#!/usr/bin/env bash
# raven-core/symlink-init.sh
# Wires engine scripts as symlinks on first install.
# Run once after cloning. Never copies files — always references raven-core/.
#
# Usage: bash raven-core/symlink-init.sh [--dry-run]

set -e
DRY_RUN=false
[[ "$1" == "--dry-run" ]] && DRY_RUN=true

CORE_DIR="$(cd "$(dirname "$0")" && pwd)"
RAVEN_DIR="$(dirname "$CORE_DIR")"

ENGINE_SCRIPTS=(cve-check.py secret-scan.py audit-log.py emit-violation.py db-guard.py)

TARGETS=(
  "$RAVEN_DIR/core/scripts"
  "$RAVEN_DIR/plugin/scripts"
  "$RAVEN_DIR/codex/scripts"
  "$RAVEN_DIR/.claude/scripts"
)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Raven — Symlink Init"
echo "  Source of truth: raven-core/"
[[ "$DRY_RUN" == "true" ]] && echo "  DRY RUN — no files written"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

for TARGET in "${TARGETS[@]}"; do
  echo "▶ $(realpath --relative-to="$RAVEN_DIR" "$TARGET" 2>/dev/null || echo "$TARGET")"
  [[ "$DRY_RUN" == "false" ]] && mkdir -p "$TARGET"
  for SCRIPT in "${ENGINE_SCRIPTS[@]}"; do
    SRC="$CORE_DIR/$SCRIPT"
    DEST="$TARGET/$SCRIPT"
    if [[ ! -f "$SRC" ]]; then
      echo "  ❌ $SCRIPT — not found in raven-core/, skipping"
      continue
    fi
    if [[ "$DRY_RUN" == "false" ]]; then
      rm -f "$DEST"
      ln -sf "$SRC" "$DEST"
    fi
    echo "  ✅ $SCRIPT → raven-core/$SCRIPT"
  done
done

echo ""
echo "  Done. Edit scripts only in raven-core/ — all locations update automatically."
echo ""
