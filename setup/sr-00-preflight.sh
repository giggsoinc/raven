#!/bin/bash
# Raven Setup — Step 0: Pre-flight + Work Mode Discovery
# Sourced by raven-setup.sh — do not run directly
#
# WHAT IT DOES:
#   1. Checks python3 + git are available
#   2. Silently scans the project directory
#   3. Shows "Here's what I see" discovery screen
#   4. Asks ONE intent question
#   5. Exports WORK_MODE and RAVEN_DETECTED for downstream steps

G='\033[0;32m' B='\033[0;34m' Y='\033[1;33m' R='\033[0;31m' W='\033[1m' N='\033[0m'

# ─── REQUIREMENTS CHECK ──────────────────────────────────────────────────────
command -v python3 &>/dev/null || { echo -e "${R}❌ python3 required. Install from python.org${N}"; exit 1; }
command -v git     &>/dev/null || { echo -e "${R}❌ git required. Install from git-scm.com${N}"; exit 1; }

# ─── SILENT SCAN ─────────────────────────────────────────────────────────────
# Run detection script against current directory
DETECT_SCRIPT="$SR_REPO_DIR/setup/sr-detect-workmode.py"
if [[ ! -f "$DETECT_SCRIPT" ]]; then
    echo -e "${R}❌ sr-detect-workmode.py missing from setup/ directory${N}"
    exit 1
fi

DETECTED=$(python3 "$DETECT_SCRIPT" "$(pwd)" 2>/dev/null)
if [[ -z "$DETECTED" ]]; then
    # Detection failed — fall back to unknown mode
    DETECTED='{"platform":"Unknown","has_git":false,"manifest_exists":false,"mode":"unknown","primary":"unknown","secondary":null,"signals":{},"confidence":"none","mode_description":"","mode_rules":[]}'
fi

# Parse JSON fields
_jq() { echo "$DETECTED" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$1','') or '')" 2>/dev/null; }
_jq_bool() { echo "$DETECTED" | python3 -c "import sys,json; d=json.load(sys.stdin); print('true' if d.get('$1') else 'false')" 2>/dev/null; }

DETECTED_PLATFORM=$(_jq "platform")
DETECTED_MODE=$(_jq "mode")
DETECTED_PRIMARY=$(_jq "primary")
DETECTED_SECONDARY=$(_jq "secondary")
DETECTED_CONFIDENCE=$(_jq "confidence")
DETECTED_DESCRIPTION=$(_jq "mode_description")
MANIFEST_EXISTS=$(_jq_bool "manifest_exists")
HAS_GIT=$(_jq_bool "has_git")
HAS_SOURCE_CODE=$(_jq_bool "has_source_code")

# ─── MANIFEST ALREADY EXISTS — EXIT EARLY ────────────────────────────────────
if [[ "$MANIFEST_EXISTS" == "true" ]]; then
    echo ""
    echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo -e "${G}  Raven is already configured for this project.${N}"
    echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
    echo ""
    echo -e "  Manifest found at: ${W}.raven/manifest.json${N}"
    echo -e "  Loading existing configuration — nothing to set up."
    echo ""
    echo -e "  Run ${W}claude .${N} to open Claude Code."
    echo -e "  Run ${W}/raven-debug${N} inside Claude Code to verify everything is loaded."
    echo ""
    exit 0
fi

# ─── DISCOVERY SCREEN ────────────────────────────────────────────────────────
echo ""
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo -e "${W}  RAVEN — first run${N}"
echo -e "${W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${N}"
echo ""
echo -e "  Scanned this directory. Here's what I see:"
echo ""

# Print signals
echo "$DETECTED" | python3 - << 'PYEOF'
import sys, json
d = json.load(sys.stdin)
signals = d.get("signals", {})
if signals:
    for label, val in signals.items():
        print(f"    {label:<26} {val}")
else:
    print("    (no recognisable project files found)")
PYEOF

echo ""
echo -e "    Platform                   ${W}${DETECTED_PLATFORM}${N} (auto-detected)"

if [[ "$HAS_GIT" == "false" ]]; then
    echo -e "    Git repo                   ${Y}not found — run git init first${N}"
fi
if [[ "$HAS_SOURCE_CODE" == "false" && "$DETECTED_MODE" != "code" ]]; then
    echo -e "    No source code             ${W}—${N} (code linting rules won't apply)"
fi

echo ""

# ─── MODE ANNOUNCEMENT ───────────────────────────────────────────────────────
case "$DETECTED_MODE" in
    "salesforce")
        echo -e "  ${G}Detected: Salesforce project.${N}"
        echo -e "  Raven will operate in ${W}Salesforce mode${N}."
        ;;
    "odoo")
        echo -e "  ${G}Detected: Odoo ERP project.${N}"
        echo -e "  Raven will operate in ${W}Odoo mode${N}."
        ;;
    "data")
        echo -e "  ${G}Detected: Data engineering workspace.${N}"
        echo -e "  Raven will operate in ${W}data mode${N}."
        ;;
    "docs")
        echo -e "  ${G}Detected: Documentation workspace.${N}"
        echo -e "  Raven will operate in ${W}docs mode${N}."
        ;;
    "infra")
        echo -e "  ${G}Detected: Pure infrastructure workspace.${N}"
        echo -e "  Raven will operate in ${W}infrastructure mode${N}."
        echo -e "  ${W}Code linting rules will not apply.${N}"
        ;;
    "code")
        echo -e "  ${G}Detected: Software development project.${N}"
        echo -e "  Raven will operate in ${W}software engineering mode${N}."
        ;;
    "ambiguous")
        echo -e "  ${Y}Detected mixed workspace: ${W}${DETECTED_PRIMARY}${N}${Y} + ${W}${DETECTED_SECONDARY}${N}"
        echo ""
        echo -e "  Which is the primary work here?"
        echo ""
        echo -e "    1) ${W}${DETECTED_PRIMARY}${N}  — the other is just a helper"
        echo -e "    2) Both equally — enforce rules for each"
        echo -e "    3) ${W}${DETECTED_SECONDARY}${N}  — the other is legacy/being phased out"
        echo ""
        read -p "  → " AMBIG_CHOICE </dev/tty
        case "$AMBIG_CHOICE" in
            1) DETECTED_MODE="$DETECTED_PRIMARY" ;;
            2) DETECTED_MODE="mixed" ;;
            3) DETECTED_MODE="$DETECTED_SECONDARY" ;;
            *) DETECTED_MODE="$DETECTED_PRIMARY" ;;
        esac
        echo ""
        ;;
    "unknown")
        echo -e "  ${Y}Could not automatically classify this workspace.${N}"
        echo ""
        echo -e "  What kind of work is this project?"
        echo ""
        echo -e "    1) ${W}code${N}    — writing application code (Python, TypeScript, Go…)"
        echo -e "    2) ${W}infra${N}   — infrastructure only (Terraform, K8s, CloudFormation)"
        echo -e "    3) ${W}data${N}    — data engineering / analytics / SQL / notebooks"
        echo -e "    4) ${W}docs${N}    — documentation / architecture review"
        echo -e "    5) ${W}review${N}  — reviewing code or diagrams (no new files)"
        echo -e "    6) ${W}mixed${N}   — combination of the above"
        echo ""
        read -p "  → " UNKNOWN_CHOICE </dev/tty
        case "$UNKNOWN_CHOICE" in
            1) DETECTED_MODE="code" ;;
            2) DETECTED_MODE="infra" ;;
            3) DETECTED_MODE="data" ;;
            4) DETECTED_MODE="docs" ;;
            5) DETECTED_MODE="review" ;;
            6) DETECTED_MODE="mixed" ;;
            *) DETECTED_MODE="code" ;;
        esac
        echo ""
        ;;
esac

echo ""

# ─── INTENT QUESTION ─────────────────────────────────────────────────────────
echo -e "  What's the main thing you want Raven to enforce?"
echo ""

case "$DETECTED_MODE" in
    "salesforce")
        echo -e "    1) No hardcoded IDs or unreviewed SOQL"
        echo -e "    2) Block secrets and credentials in metadata"
        echo -e "    3) Enforce test coverage and bulk patterns"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
    "odoo")
        echo -e "    1) Module structure and naming discipline"
        echo -e "    2) No raw SQL or hardcoded DB IDs"
        echo -e "    3) Security and access control checks"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
    "data")
        echo -e "    1) SQL quality and schema documentation"
        echo -e "    2) No PII in pipeline configs or logs"
        echo -e "    3) Pipeline naming and dependency tracking"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
    "docs")
        echo -e "    1) No broken links or orphaned pages"
        echo -e "    2) Consistent structure and headings"
        echo -e "    3) Diagrams stay in sync with code"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
    "infra")
        echo -e "    1) No undocumented infrastructure changes"
        echo -e "    2) Secrets never in config files"
        echo -e "    3) Consistent naming conventions"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
    "review")
        echo -e "    1) Flag security issues in reviewed code"
        echo -e "    2) Check for outdated patterns and anti-patterns"
        echo -e "    3) Ensure architecture diagrams exist and are current"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
    *)  # code, mixed, unknown
        echo -e "    1) Code quality, style, and type safety"
        echo -e "    2) Secrets never in source files"
        echo -e "    3) CVE scan every new dependency"
        echo -e "    4) All of the above ${W}(recommended)${N}"
        ;;
esac

echo ""
echo -e "    ${Y}Or describe what you want enforced (free text):${N}"
echo ""
read -p "  → " INTENT_CHOICE </dev/tty
echo ""

# Record intent
if [[ "$INTENT_CHOICE" =~ ^[1-4]$ ]]; then
    case "$INTENT_CHOICE" in
        1|2|3) export RAVEN_INTENT="custom-${INTENT_CHOICE}" ;;
        4)     export RAVEN_INTENT="all" ;;
    esac
else
    export RAVEN_INTENT="$INTENT_CHOICE"
fi

# ─── EXPORT FOR DOWNSTREAM STEPS ─────────────────────────────────────────────
export WORK_MODE="$DETECTED_MODE"
export RAVEN_DETECTED="$DETECTED"
export RAVEN_PLATFORM="$DETECTED_PLATFORM"

echo -e "  ${G}✅ python3 + git found${N}"
echo -e "  ${G}✅ Platform: ${DETECTED_PLATFORM}${N}"
echo -e "  ${G}✅ Work mode: ${WORK_MODE}${N}"
echo ""
