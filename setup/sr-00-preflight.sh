#!/bin/bash
# Raven Setup — Step 0: Pre-flight checks
# Sourced by raven-setup.sh — do not run directly

G='\033[0;32m' R='\033[0;31m' N='\033[0m'

command -v python3 &>/dev/null || { echo -e "${R}❌ python3 required${N}"; exit 1; }
command -v git     &>/dev/null || { echo -e "${R}❌ git required${N}"; exit 1; }

echo -e "${G}✅ python3 + git found${N}"
