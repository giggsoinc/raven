#!/bin/bash
set -e

RAVEN_DIR="$HOME/.raven-codex"

echo "Installing Raven-Codex..."

git clone https://github.com/giggsoinc/raven-codex.git "$RAVEN_DIR"

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
  echo "# Raven-Codex" >> "$SHELL_PROFILE"
  echo "alias raven-codex-setup='bash $RAVEN_DIR/raven-codex-setup.sh'" >> "$SHELL_PROFILE"
fi

echo ""
echo "✅ Raven-Codex installed at $RAVEN_DIR"
echo ""
echo "Run in your project:"
echo "  source ~/.zshrc && cd YourProject && raven-codex-setup"
echo ""
