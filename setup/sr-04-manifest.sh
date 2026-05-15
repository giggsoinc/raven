#!/bin/bash
# Raven Setup — Step 4: Generate manifest.json
# Requires all exported vars from sr-01-questions.sh

G='\033[0;32m' N='\033[0m'
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

PROJECT_VAL="$PROJECT" MODE_VAL="$MODE" EMAIL_VAL="$EMAIL" TS_VAL="$TS" \
GITHUB_VAL="$GITHUB_ID" TAG_VAL="$PROJECT_TAG" \
WORK_TYPE_VAL="${WORK_TYPE:-code}" \
LANGUAGES_VAL="$LANGUAGES" CLOUD_VAL="$CLOUD" APPS_VAL="$APPS" \
DB_PRIMARY_VAL="$DB_PRIMARY" DB_NOSQL_VAL="$DB_NOSQL" DB_STREAM_VAL="$DB_STREAM" \
DB_WAREHOUSE_VAL="$DB_WAREHOUSE" DB_CACHE_VAL="$DB_CACHE" DB_VECTOR_VAL="$DB_VECTOR" \
DB_GRAPH_VAL="$DB_GRAPH" DB_BLOB_VAL="$DB_BLOB" OUT_VAL="$PROJECT_DIR" \
python3 - << 'PYEOF'
import json, os

def jl(val):
    try:
        v = json.loads(val)
        return v if isinstance(v, list) else [val]
    except:
        return [val] if val and val not in ("[]","none","None") else []

proj      = os.environ["PROJECT_VAL"]
mode      = os.environ["MODE_VAL"]
email     = os.environ["EMAIL_VAL"]
ts        = os.environ["TS_VAL"]
github    = os.environ.get("GITHUB_VAL","")
tag       = os.environ.get("TAG_VAL","")
outdir    = os.environ["OUT_VAL"]
work_type = os.environ.get("WORK_TYPE_VAL","code")
audit_id  = github or tag or proj

manifest = {
  "project":   proj,
  "version":   "1.0",
  "mode":      mode,
  "github_id": github,
  "audit_tag": audit_id,
  "stack": {
    "work_type": work_type,
    "language":  jl(os.environ["LANGUAGES_VAL"]),
    "db": {
      "primary":   jl(os.environ["DB_PRIMARY_VAL"]),
      "nosql":     jl(os.environ["DB_NOSQL_VAL"]),
      "streaming": jl(os.environ["DB_STREAM_VAL"]),
      "warehouse": jl(os.environ["DB_WAREHOUSE_VAL"]),
      "cache":     jl(os.environ["DB_CACHE_VAL"]),
      "vector":    jl(os.environ["DB_VECTOR_VAL"]),
      "graph":     jl(os.environ["DB_GRAPH_VAL"]),
      "blob":      jl(os.environ["DB_BLOB_VAL"])
    },
    "cloud":     jl(os.environ["CLOUD_VAL"]),
    "apps":      jl(os.environ["APPS_VAL"]),
    "libraries": []
  },
  "standards":     "raven-v2.8",
  "approval_mode": "auto" if mode == "solo" else "first_responder",
  "guard": {
    "enabled":  True,
    "db":       {"mass_deletion_threshold": 100},
    "git":      {"force_push": "hard_block"},
    "infra":    {"terraform_state": "hard_block"},
    "firewall": {"open_world": "hard_block"}
  },
  "style": {
    "max_lines_per_file":      150,
    "require_type_hints":      True,
    "require_docstrings":      True,
    "forbid_print_statements": True
  },
  "allowed_tools": {
    "default_policy": "warn",
    "mcps": [], "apis": [],
    "web": {"blocked_url_patterns": ["api.openai.com","platform.openai.com"]}
  },
  "approved_skills": {
    "giggso":    ["raven-core","raven-expert","raven-plan","raven-review",
                  "raven-security","raven-refactor","raven-test","raven-document","andie"],
    "anthropic": ["debug","batch","review","security-review","init"],
    "community": []
  },
  "project_rules": {
    "forbidden_frameworks":      [],
    "forbidden_file_extensions": [],
    "license":                   "",
    "commit_convention":         "conventional",
    "require_approval_gates":    False,
    "ui_framework":              "",
    "phase_gated":               False
  },
  "changelog": [{
    "version":    "1.0",
    "changed_by": email,
    "github_id":  github,
    "audit_tag":  audit_id,
    "changed_at": ts,
    "changes":    f"Init: mode={mode}",
    "pr":         "pending"
  }]
}

with open(f"{outdir}/.raven/manifest.json","w") as f:
    json.dump(manifest, f, indent=2)
print("written")
PYEOF
echo -e "  ${G}✅ manifest.json created${N}"
