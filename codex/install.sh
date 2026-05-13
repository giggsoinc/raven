#!/bin/bash
set -e

RAVEN_DIR="$HOME/.raven-codex"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║     Raven for Codex — Installing     ║"
echo "║        Guardrails before you ship.   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Clone monorepo to temp, copy codex/ to install location
TEMP_DIR="$(mktemp -d)"
echo "Fetching Raven..."
git clone --depth 1 https://github.com/giggsoinc/raven.git "$TEMP_DIR/raven" --quiet

# Install from codex/ subfolder
rm -rf "$RAVEN_DIR"
cp -r "$TEMP_DIR/raven/codex" "$RAVEN_DIR"
rm -rf "$TEMP_DIR"

chmod +x "$RAVEN_DIR/raven-codex-setup.sh"
chmod +x "$RAVEN_DIR/scripts/"*.py 2>/dev/null || true
chmod +x "$RAVEN_DIR/mcp/server.py" 2>/dev/null || true

echo "Installing Python dependencies..."
pip3 install -q openai requests packaging 2>/dev/null || true

# Add raven-codex-setup alias to shell profile
SHELL_PROFILE="$HOME/.zshrc"
[ -f "$HOME/.bashrc" ] && SHELL_PROFILE="$HOME/.bashrc"

if ! grep -q "raven-codex-setup" "$SHELL_PROFILE" 2>/dev/null; then
  echo "" >> "$SHELL_PROFILE"
  echo "# Raven for Codex" >> "$SHELL_PROFILE"
  echo "alias raven-codex-setup='bash $RAVEN_DIR/raven-codex-setup.sh'" >> "$SHELL_PROFILE"
fi

echo ""
echo "✅ Raven installed at $RAVEN_DIR"
echo ""
echo "Run in your project:"
echo "  source ~/.zshrc && cd YourProject && raven-codex-setup"
echo ""
