#!/bin/bash
# Raven — Claude Mem Setup
# Installs Claude Mem for session memory + 95% token reduction
set -e
G='\033[0;32m' Y='\033[1;33m' R='\033[0;31m' N='\033[0m'

command -v node &>/dev/null || { echo -e "${R}❌ Node.js required${N}"; exit 1; }

echo "Installing Claude Mem..."
npm install -g claude-mem 2>/dev/null || pip install claude-mem --break-system-packages 2>/dev/null || \
  { echo -e "${Y}⚠️  Install manually: npm install -g claude-mem${N}"; exit 0; }

# Add to project CLAUDE.md if not already there
CLAUDE_MD="${1:-CLAUDE.md}"
grep -q "claude-mem" "$CLAUDE_MD" 2>/dev/null || cat >> "$CLAUDE_MD" << 'MD'

## Memory (Claude Mem)
Session decisions, architectural choices, and bug fixes are indexed locally.
On session start: load relevant context from Claude Mem index.
On session end: save key decisions to Claude Mem index.
MD

echo -e "${G}✅ Claude Mem installed + CLAUDE.md updated${N}"
echo "Start with: claude-mem start"
