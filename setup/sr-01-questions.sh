#!/bin/bash
# Raven Setup — Step 1: Adaptive Questions
# Reads WORK_MODE from sr-00-preflight.sh
# Asks only what sr-00 could NOT detect automatically
# Maximum 3 questions total (usually 1-2)

B='\033[0;34m' G='\033[0;32m' Y='\033[1;33m' N='\033[0m' W='\033[1m'

# ─── WORK MODE should be set by sr-00 ────────────────────────────────────────
WORK_MODE="${WORK_MODE:-code}"
WORK_TYPE="$WORK_MODE"

# ─── HELPERS ─────────────────────────────────────────────────────────────────
_ask() {
    echo -e "  ${B}$1${N}" >/dev/tty
    [ -n "$2" ] && echo -e "  ${Y}$2${N}" >/dev/tty
    read -p "  → " V </dev/tty
    echo -e "  ${G}✅ ${V:-skipped}${N}\n" >/dev/tty
    echo "$V"
}

_pick() {
    local LABEL="$1"; shift; local OPTS=("$@")
    echo -e "  ${B}$LABEL${N}" >/dev/tty
    for i in "${!OPTS[@]}"; do
        echo -e "  $((i+1))) ${OPTS[$i]}" >/dev/tty
    done
    echo -e "  ${Y}Numbers (comma-sep), free text, or both. Enter to skip.${N}" >/dev/tty
    read -p "  → " RAW </dev/tty
    python3 - "$RAW" "${OPTS[@]}" << 'PYEOF'
import sys, json
raw  = sys.argv[1].strip()
opts = sys.argv[2:]
if not raw:
    print("[]"); sys.exit(0)
result = []
for tok in raw.split(","):
    tok = tok.strip()
    if not tok:
        continue
    if tok.isdigit() and 1 <= int(tok) <= len(opts):
        result.append(opts[int(tok)-1])
    else:
        result.append(tok.lower().strip())
seen = set(); out = []
for r in result:
    if r not in seen and r not in ("none",""):
        seen.add(r); out.append(r)
print(json.dumps(out))
PYEOF
}

# ─── PROJECT DIRECTORY ───────────────────────────────────────────────────────
echo -e "  ${B}Where is your project? (Enter = current dir: $(pwd))${N}" >/dev/tty
read -p "  → " P </dev/tty
export PROJECT_DIR="${P:-$(pwd)}"
export PROJECT_DIR="${PROJECT_DIR/#\~/$HOME}"
[ ! -d "$PROJECT_DIR" ] && mkdir -p "$PROJECT_DIR"
[ "$PROJECT_DIR" = "$SR_REPO_DIR" ] && echo "❌ Cannot init inside Raven repo" && exit 1
echo -e "  ${G}✅ $PROJECT_DIR${N}\n" >/dev/tty

# ─── MODE ────────────────────────────────────────────────────────────────────
echo -e "  ${B}Mode:${N}" >/dev/tty
echo -e "  1) solo       — lone developer, no approvals" >/dev/tty
echo -e "  2) team       — small team, email approvals" >/dev/tty
echo -e "  3) enterprise — full governance, org manifest" >/dev/tty
read -p "  → " M </dev/tty
case "$M" in 1) export MODE="solo" ;; 2) export MODE="team" ;; *) export MODE="enterprise" ;; esac
echo -e "  ${G}✅ $MODE${N}\n" >/dev/tty

# ─── BASIC INFO ──────────────────────────────────────────────────────────────
export PROJECT=$(_ask "Project name (Enter = $(basename $PROJECT_DIR)):")
export PROJECT="${PROJECT:-$(basename $PROJECT_DIR)}"
export EMAIL=$(_ask "Your email:")

# ─── GITHUB ID OR TAG ────────────────────────────────────────────────────────
echo -e "  ${B}GitHub username (Enter to use a project tag instead):${N}" >/dev/tty
read -p "  → " GITHUB_ID </dev/tty
export GITHUB_ID
export PROJECT_TAG=""
if [ -z "$GITHUB_ID" ]; then
    echo -e "  ${B}Project tag for audit trail (e.g. internal, client-abc):${N}" >/dev/tty
    read -p "  → " PROJECT_TAG </dev/tty
    export PROJECT_TAG="${PROJECT_TAG// /-}"
    export PROJECT_TAG="${PROJECT_TAG:-$PROJECT}"
    echo -e "  ${G}✅ Tag: $PROJECT_TAG${N}\n" >/dev/tty
else
    echo -e "  ${G}✅ GitHub: $GITHUB_ID${N}\n" >/dev/tty
fi

# ─── CLOUD (always ask — needed for secrets config and audit log) ─────────────
export CLOUD=$(_pick "Cloud provider(s):" \
    "aws" "gcp" "azure" "oci" \
    "on-prem" "multi" \
    "cloudflare" "vercel" "railway" "hetzner" "none")
echo -e "  ${G}✅ $CLOUD${N}\n" >/dev/tty

# ─── ADAPTIVE: LANGUAGE — only if work mode needs it ─────────────────────────
case "$WORK_MODE" in

    "review")
        # No language selection — review work doesn't need a stack
        export LANGUAGES='["review-only"]'
        echo -e "  ${G}✅ Language: review-only (skipped for review work)${N}\n" >/dev/tty
        ;;

    "infra")
        # Ask about infra file types, not programming languages
        export LANGUAGES=$(_pick "Infra file types (what's in this repo):" \
            "yaml" "hcl" "json" "dockerfile" "bicep" "shell")
        echo -e "  ${G}✅ $LANGUAGES${N}\n" >/dev/tty
        ;;

    "data")
        # Data work — SQL + notebooks, maybe Python
        export LANGUAGES=$(_pick "Primary languages / formats:" \
            "sql" "python3.12" "python3.11" "yaml" "r" "scala" "other")
        echo -e "  ${G}✅ $LANGUAGES${N}\n" >/dev/tty
        ;;

    "docs")
        # Docs work — markdown, rst, maybe code examples
        export LANGUAGES='["markdown"]'
        echo -e "  ${G}✅ Language: markdown (skipped for docs work)${N}\n" >/dev/tty
        ;;

    "salesforce")
        # Salesforce — Apex + metadata
        export LANGUAGES='["apex","xml","yaml"]'
        echo -e "  ${G}✅ Language: apex + xml (Salesforce project)${N}\n" >/dev/tty
        ;;

    "odoo")
        # Odoo — Python + XML
        export LANGUAGES='["python3.12","xml"]'
        echo -e "  ${G}✅ Language: python + xml (Odoo project)${N}\n" >/dev/tty
        ;;

    "mixed")
        # Mixed: ask for both code languages AND confirm infra types
        export LANGUAGES=$(_pick "Languages (code + infra — pick all that apply):" \
            "python3.13" "python3.12" "python3.11" \
            "typescript" "javascript" "go" "rust" "java" "csharp" \
            "yaml" "hcl" "shell" "sql" "other")
        echo -e "  ${G}✅ $LANGUAGES${N}\n" >/dev/tty
        ;;

    *)  # "code" and anything unrecognised
        export LANGUAGES=$(_pick "Primary language(s):" \
            "python3.13" "python3.12" "python3.11" \
            "typescript" "javascript" \
            "go" "rust" "java" "kotlin" "swift" "csharp" \
            "sql" "shell" "other")
        echo -e "  ${G}✅ $LANGUAGES${N}\n" >/dev/tty
        ;;
esac

# ─── DATABASES — simplified, only if relevant ────────────────────────────────
if [[ "$WORK_MODE" != "docs" && "$WORK_MODE" != "review" ]]; then
    echo -e "  ${Y}Databases (Enter to skip any category):${N}\n" >/dev/tty

    export DB_PRIMARY=$(_pick "Primary DB (if any):" \
        "postgresql" "mysql" "sqlite" "oracle" "sqlserver" "cockroachdb" "none")
    echo -e "  ${G}✅ $DB_PRIMARY${N}\n" >/dev/tty

    export DB_NOSQL=$(_pick "NoSQL / Document (if any):" \
        "mongodb" "dynamodb" "firestore" "cosmosdb" "none")
    echo -e "  ${G}✅ $DB_NOSQL${N}\n" >/dev/tty

    export DB_STREAM=$(_pick "Streaming / Queue (if any):" \
        "kafka" "pubsub" "kinesis" "rabbitmq" "sqs" "nats" "none")
    echo -e "  ${G}✅ $DB_STREAM${N}\n" >/dev/tty

    export DB_CACHE=$(_pick "Cache (if any):" \
        "redis" "memcached" "valkey" "none")
    echo -e "  ${G}✅ $DB_CACHE${N}\n" >/dev/tty
else
    export DB_PRIMARY="[]" DB_NOSQL="[]" DB_STREAM="[]" DB_CACHE="[]"
fi

# ─── REMAINING (all modes) ────────────────────────────────────────────────────
export DB_WAREHOUSE="[]" DB_VECTOR="[]" DB_GRAPH="[]" DB_BLOB="[]" APPS="[]"

# ─── NOTIFICATION EMAIL (team/enterprise only) ────────────────────────────────
export INBOX=""
[ "$MODE" != "solo" ] && INBOX=$(_ask "Notification email (Enter to skip):")
export INBOX

# ─── OPENAI KEY ───────────────────────────────────────────────────────────────
export OPENAI_KEY=$(_ask "OpenAI key for CVE check (Enter to skip):")
