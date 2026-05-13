#!/bin/bash
# Raven Guard — One-Line Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-guard/main/install.sh | bash
# Requires: Raven Core installed first

set -e
G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' B='\033[0;34m' W='\033[1m' N='\033[0m'

REPO="https://github.com/giggsoinc/raven-guard.git"
INSTALL_DIR="$HOME/.raven-guard"
BIN_DIR="$HOME/.local/bin"

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  Raven Guard — Installer${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""

# Check Core is installed
command -v raven-setup &>/dev/null || [ -f "$HOME/.raven/raven-setup.sh" ] || {
    echo -e "${R}❌ Raven Core not installed.${N}"
    echo -e "   Run first: ${B}curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash${N}"
    exit 1
}

# Download or update
if [ -d "$INSTALL_DIR/.git" ]; then
    echo -e "${B}Updating Guard...${N}"
    cd "$INSTALL_DIR" && git pull --quiet
    echo -e "${G}✅ Updated${N}"
else
    echo -e "${B}Downloading Raven Guard...${N}"
    git clone --quiet --depth=1 "$REPO" "$INSTALL_DIR"
    echo -e "${G}✅ Downloaded to $INSTALL_DIR${N}"
fi

mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/raven-guard-setup" << CMDEOF
#!/bin/bash
bash "$INSTALL_DIR/raven-guard-setup.sh" "\$@"
CMDEOF
chmod +x "$BIN_DIR/raven-guard-setup"

SHELL_RC=""
[ -f "$HOME/.zshrc"  ] && SHELL_RC="$HOME/.zshrc"
[ -f "$HOME/.bashrc" ] && SHELL_RC="$HOME/.bashrc"
if [ -n "$SHELL_RC" ] && ! grep -q "$BIN_DIR" "$SHELL_RC" 2>/dev/null; then
    echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$SHELL_RC"
fi
export PATH="$PATH:$BIN_DIR"

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${G}  ✅ Raven Guard installed${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""
echo -e "  To add Guard to any project (after Core init):"
echo -e "  ${B}cd YourProject && raven-guard-setup${N}"
echo ""
echo -e "  To update Guard later:"
echo -e "  ${B}cd ~/.raven-guard && git pull${N}"
echo ""
