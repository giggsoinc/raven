#!/bin/bash
# Raven — Setup
# Usage: bash /path/to/raven/raven-setup.sh
# Runs 7 steps. Each step is a separate script in setup/

set -e
export SR_REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
W='\033[1m' N='\033[0m'

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  Raven — Setup v2.8${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}\n"

source "$SR_REPO_DIR/setup/sr-00-preflight.sh"  || exit 1

# Backup existing secrets before questions wipe state
export SR_SECRETS_BAK=""
[ -f ".shay-rolls/manifest.secrets.json" ] && \
    export SR_SECRETS_BAK=$(cat ".shay-rolls/manifest.secrets.json")

source "$SR_REPO_DIR/setup/sr-01-questions.sh"  || exit 1

echo -e "${W}Installing...${N}"
source "$SR_REPO_DIR/setup/sr-02-install-files.sh" || exit 1
source "$SR_REPO_DIR/setup/sr-03-gitignore.sh"     || exit 1
source "$SR_REPO_DIR/setup/sr-04-manifest.sh"      || exit 1
source "$SR_REPO_DIR/setup/sr-05-secrets.sh"       || exit 1

echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
source "$SR_REPO_DIR/setup/sr-06-verify.sh"        || exit 1
