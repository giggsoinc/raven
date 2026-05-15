#!/bin/bash
# Raven Setup — Step 1: User questions
# Sets all exported vars consumed by steps 2-6

B='\033[0;34m' G='\033[0;32m' Y='\033[1;33m' N='\033[0m'

# -- Project directory --
echo -e "${B}Where is your project? (Enter = current dir: $(pwd))${N}"
read -p "  → " P </dev/tty
export PROJECT_DIR="${P:-$(pwd)}"
export PROJECT_DIR="${PROJECT_DIR/#\~/$HOME}"
[ ! -d "$PROJECT_DIR" ] && mkdir -p "$PROJECT_DIR"
[ "$PROJECT_DIR" = "$SR_REPO_DIR" ] && echo "❌ Cannot init inside Raven repo" && exit 1
echo -e "  ${G}✅ $PROJECT_DIR${N}\n"

# -- Mode --
echo -e "  ${B}Mode:${N}" >/dev/tty
echo -e "  1) solo       — lone developer, no approvals" >/dev/tty
echo -e "  2) team       — small team, email approvals" >/dev/tty
echo -e "  3) enterprise — full governance, org manifest" >/dev/tty
read -p "  → " M </dev/tty
case "$M" in 1) export MODE="solo" ;; 2) export MODE="team" ;; *) export MODE="enterprise" ;; esac
echo -e "  ${G}✅ $MODE${N}\n" >/dev/tty

# -- Work type --
echo -e "  ${B}What kind of work is this project?${N}" >/dev/tty
echo -e "  1) code    — writing application code (Python, TypeScript, Go, etc.)" >/dev/tty
echo -e "  2) infra   — infrastructure only (Terraform, K8s YAML, CloudFormation)" >/dev/tty
echo -e "  3) review  — reviewing code, docs, or architecture (no new files)" >/dev/tty
echo -e "  4) mixed   — both code and infra in same project" >/dev/tty
read -p "  → " WT </dev/tty
case "$WT" in
  1) export WORK_TYPE="code" ;;
  2) export WORK_TYPE="infra" ;;
  3) export WORK_TYPE="review" ;;
  4) export WORK_TYPE="mixed" ;;
  *) export WORK_TYPE="code" ;;
esac
echo -e "  ${G}✅ $WORK_TYPE${N}\n" >/dev/tty

# -- Helper: ask single value --
_ask() {
    echo -e "  ${B}$1${N}" >/dev/tty
    read -p "  → " V </dev/tty
    echo -e "  ${G}✅ ${V:-skipped}${N}\n" >/dev/tty
    echo "$V"
}

# -- Helper: multi-select with freeform --
# Usage: _pick "Label" opt1 opt2 opt3 ...
# User can type numbers (comma-sep), type freely, or combine both
_pick() {
    local LABEL="$1"; shift; local OPTS=("$@")
    echo -e "  ${B}$LABEL${N}" >/dev/tty
    for i in "${!OPTS[@]}"; do
        echo -e "  $((i+1))) ${OPTS[$i]}" >/dev/tty
    done
    echo -e "  ${Y}Numbers (comma-sep), free text, or both. Enter to skip.${N}" >/dev/tty
    read -p "  → " RAW </dev/tty
    # Python parses: numbers → lookup opts, plain text → keep as-is, mixed → both
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
        # Freeform — clean and add as-is
        result.append(tok.lower().strip())
# Deduplicate, preserve order
seen = set()
out = []
for r in result:
    if r not in seen and r not in ("none",""):
        seen.add(r); out.append(r)
print(json.dumps(out))
PYEOF
}

# -- Basic info --
export PROJECT=$(_ask "Project name (Enter = $(basename $PROJECT_DIR)):")
export PROJECT="${PROJECT:-$(basename $PROJECT_DIR)}"
export EMAIL=$(_ask "Your email:")

# -- GitHub ID or tag --
echo -e "  ${B}GitHub username (Enter to use a project tag instead):${N}" >/dev/tty
read -p "  → " GITHUB_ID </dev/tty
export GITHUB_ID
export PROJECT_TAG=""
if [ -z "$GITHUB_ID" ]; then
    echo -e "  ${B}Project tag for audit trail (e.g. internal, client-abc, skunkworks):${N}" >/dev/tty
    echo -e "  ${Y}No spaces — used in S3 path${N}" >/dev/tty
    read -p "  → " PROJECT_TAG </dev/tty
    export PROJECT_TAG="${PROJECT_TAG// /-}"
    export PROJECT_TAG="${PROJECT_TAG:-$PROJECT}"
    echo -e "  ${G}✅ Tag: $PROJECT_TAG${N}\n" >/dev/tty
else
    echo -e "  ${G}✅ GitHub: $GITHUB_ID${N}\n" >/dev/tty
fi

# -- Languages --
# Adjust prompt and options based on work_type
if [ "$WORK_TYPE" = "review" ]; then
    export LANGUAGES='["review-only"]'
    echo -e "  ${G}✅ review-only (skipping language selection for review work)${N}\n" >/dev/tty
elif [ "$WORK_TYPE" = "infra" ]; then
    export LANGUAGES=$(_pick "Infra file types used:" \
        "yaml" "hcl" "json" "dockerfile" "bicep" "shell" "other")
    echo -e "  ${G}✅ $LANGUAGES${N}\n" >/dev/tty
else
    export LANGUAGES=$(_pick "Languages:" \
        "python3.13" "python3.12" "python3.11" \
        "typescript" "javascript" \
        "swift" "kotlin" "go" "rust" "java" "csharp" \
        "yaml" "hcl" "shell" "sql" "other")
    echo -e "  ${G}✅ $LANGUAGES${N}\n" >/dev/tty
fi

# ── CLOUD FIRST ──────────────────────────────────────────────────────────────
export CLOUD=$(_pick "Cloud provider(s):" \
    "aws" "gcp" "azure" "oci" \
    "on-prem" "multi" \
    "cloudflare" "vercel" "railway" "fly.io" "hetzner")
echo -e "  ${G}✅ $CLOUD${N}\n" >/dev/tty

# Detect primary cloud for smart defaults
_primary_cloud() {
    python3 - "$CLOUD" << 'PYEOF'
import sys, json
try:
    clouds = json.loads(sys.argv[1])
    if not clouds: print(""); sys.exit(0)
    # Priority: aws > gcp > azure > oci > others
    for c in ["aws","gcp","azure","oci"]:
        if c in clouds: print(c); sys.exit(0)
    print(clouds[0])
except:
    print("")
PYEOF
}
PRIMARY_CLOUD=$(_primary_cloud)

# ── BLOB DEFAULT FROM CLOUD ──────────────────────────────────────────────────
_blob_default() {
    case "$1" in
        aws)   echo "s3" ;;
        gcp)   echo "gcs" ;;
        azure) echo "azure-blob" ;;
        oci)   echo "oci-object-storage" ;;
        *)     echo "" ;;
    esac
}
BLOB_DEFAULT=$(_blob_default "$PRIMARY_CLOUD")

if [ -n "$BLOB_DEFAULT" ]; then
    echo -e "  ${B}Object/Blob store:${N}" >/dev/tty
    echo -e "  ${Y}Detected cloud: $PRIMARY_CLOUD → default: $BLOB_DEFAULT${N}" >/dev/tty
    echo -e "  Enter to accept, or: 1) s3  2) gcs  3) azure-blob  4) r2  5) minio  6) oci-object-storage  7) none" >/dev/tty
    read -p "  → " BLOB_RAW </dev/tty
    if [ -z "$BLOB_RAW" ]; then
        export DB_BLOB="[\"$BLOB_DEFAULT\"]"
        echo -e "  ${G}✅ $BLOB_DEFAULT (default)${N}
" >/dev/tty
    else
        export DB_BLOB=$(_pick "Object/Blob store:" \
            "s3" "gcs" "azure-blob" "r2" "minio" "oci-object-storage" "none")
    fi
else
    export DB_BLOB=$(_pick "Object/Blob store:" \
        "s3" "gcs" "azure-blob" "r2" "minio" "oci-object-storage" "none")
    echo -e "  ${G}✅ $DB_BLOB${N}
" >/dev/tty
fi

# -- Apps --
export APPS=$(_pick "App types:" \
    "api" "mcp" "web" "mobile-ios" "mobile-android" "cli" "worker" "none")
echo -e "  ${G}✅ $APPS${N}\n" >/dev/tty

# ── DATABASES ────────────────────────────────────────────────────────────────
echo -e "  ${Y}Databases — type numbers, free text, or both. Enter to skip any.${N}\n" >/dev/tty

export DB_PRIMARY=$(_pick "Primary/Relational DB:" \
    "postgresql" "mysql" "mariadb" "sqlite" "oracle" "sqlserver" "cockroachdb")
echo -e "  ${G}✅ $DB_PRIMARY${N}\n" >/dev/tty

export DB_NOSQL=$(_pick "NoSQL / Document:" \
    "mongodb" "dynamodb" "firestore" "cosmosdb" "couchdb" "cassandra")
echo -e "  ${G}✅ $DB_NOSQL${N}\n" >/dev/tty

export DB_STREAM=$(_pick "Streaming / Queue:" \
    "kafka" "pubsub" "kinesis" "rabbitmq" "sqs" "nats" "pulsar")
echo -e "  ${G}✅ $DB_STREAM${N}\n" >/dev/tty

export DB_WAREHOUSE=$(_pick "Analytics / Warehouse:" \
    "bigquery" "snowflake" "redshift" "databricks" "clickhouse" "duckdb")
echo -e "  ${G}✅ $DB_WAREHOUSE${N}\n" >/dev/tty

export DB_CACHE=$(_pick "Cache / In-memory:" \
    "redis" "memcached" "valkey" "dragonfly" "elasticache" "upstash")
echo -e "  ${G}✅ $DB_CACHE${N}\n" >/dev/tty

export DB_VECTOR=$(_pick "Vector / Search:" \
    "pinecone" "weaviate" "qdrant" "milvus" "opensearch" "pgvector" "chromadb" "faiss")
echo -e "  ${G}✅ $DB_VECTOR${N}\n" >/dev/tty

export DB_GRAPH=$(_pick "Graph DB:" \
    "neo4j" "falkordb" "neptune" "arangodb" "tigergraph" "memgraph")
echo -e "  ${G}✅ $DB_GRAPH${N}\n" >/dev/tty

# -- Notifications --
export INBOX=""
[ "$MODE" != "solo" ] && INBOX=$(_ask "Notification email (Enter to skip):")
export INBOX
export OPENAI_KEY=$(_ask "OpenAI key for CVE check (Enter to skip):")
