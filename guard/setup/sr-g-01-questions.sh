#!/bin/bash
# Guard Setup — Step 1: Questions
B='\033[0;34m' G='\033[0;32m' N='\033[0m'

echo -e "${B}Where is your project? (Enter = current dir: $(pwd))${N}"
read -p "  → " P </dev/tty
export PROJECT_DIR="${P:-$(pwd)}"
export PROJECT_DIR="${PROJECT_DIR/#\~/$HOME}"
[ ! -d "$PROJECT_DIR" ] && echo "❌ Not found: $PROJECT_DIR" && exit 1
echo -e "  ${G}✅ $PROJECT_DIR${N}\n"

_ask() { echo -e "  ${B}$1${N}" >/dev/tty; read -p "  → " V </dev/tty; echo -e "  ${G}✅ ${V:-skipped}${N}\n" >/dev/tty; echo "$V"; }
export G_ESCALATION=$(_ask "Escalation email for P1 incidents (Enter to skip):")
export G_PAGERDUTY=$(_ask "PagerDuty routing key (Enter to skip):")
export G_THRESHOLD=$(_ask "Mass DB deletion threshold in rows (Enter = 100):")
export G_THRESHOLD="${G_THRESHOLD:-100}"
