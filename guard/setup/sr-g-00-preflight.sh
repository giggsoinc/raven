#!/bin/bash
# Guard Setup — Step 0: Pre-flight
G='\033[0;32m' R='\033[0;31m' N='\033[0m'
command -v python3 &>/dev/null || { echo -e "${R}❌ python3 required${N}"; exit 1; }
[ ! -f "$PROJECT_DIR/.raven/manifest.json" ] && \
    echo -e "${R}❌ Raven Core not found in $PROJECT_DIR\n   Run raven-setup.sh first${N}" && exit 1
echo -e "${G}✅ Core detected${N}"
