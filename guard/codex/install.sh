#!/bin/bash
set -e

GUARD_DIR="$HOME/.raven-guard-codex"

echo "Installing Raven-Guard-Codex..."

# Requires raven-codex
if [ ! -d "$HOME/.raven-codex" ]; then
  echo "❌ raven-codex not found. Install it first:"
  echo "   curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-codex/main/install.sh | bash"
  exit 1
fi

git clone https://github.com/giggsoinc/raven-guard-codex.git "$GUARD_DIR"

chmod +x "$GUARD_DIR/raven-guard-codex-setup.sh"

SHELL_PROFILE="$HOME/.zshrc"
[ -f "$HOME/.bashrc" ] && SHELL_PROFILE="$HOME/.bashrc"

if ! grep -q "raven-guard-codex-setup" "$SHELL_PROFILE" 2>/dev/null; then
  echo "" >> "$SHELL_PROFILE"
  echo "# Raven-Guard-Codex" >> "$SHELL_PROFILE"
  echo "alias raven-guard-codex-setup='bash $GUARD_DIR/raven-guard-codex-setup.sh'" >> "$SHELL_PROFILE"
fi

echo ""
echo "✅ Raven-Guard-Codex installed at $GUARD_DIR"
echo ""
echo "Run in your project:"
echo "  source ~/.zshrc && cd YourProject && raven-guard-codex-setup"
echo ""
