#!/bin/bash
# Raven Guard — Setup
# Usage: bash /path/to/raven-claude-guard/raven-guard-setup.sh
# Requires: Core already installed in target project

set -e
export SR_GUARD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W='\033[1m' N='\033[0m'

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  Raven Guard — Setup v1.3${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"

source "$SR_GUARD_DIR/setup/sr-g-01-questions.sh"      || exit 1
source "$SR_GUARD_DIR/setup/sr-g-00-preflight.sh"      || exit 1

echo -e "${W}Installing Guard...${N}"
source "$SR_GUARD_DIR/setup/sr-g-02-install-agents.sh" || exit 1
source "$SR_GUARD_DIR/setup/sr-g-03-manifest-update.sh"|| exit 1

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
source "$SR_GUARD_DIR/setup/sr-g-04-verify.sh"         || exit 1
