#!/bin/bash
# Raven Setup — Step 3: .gitignore
# Requires: PROJECT_DIR

G='\033[0;32m' Y='\033[1;33m' N='\033[0m'

if [ ! -f "$PROJECT_DIR/.gitignore" ]; then
    cat > "$PROJECT_DIR/.gitignore" << 'GIEOF'
# Secrets — NEVER commit
.env
.env.*
*.pem
*.key
*.p12
*.pfx
manifest.secrets.json
.raven/manifest.secrets.json
.raven/.cache/
.raven/audit/
.raven/guard/digest.log

# Raven framework — never commit (lives outside project)
raven-claude/
raven-claude-guard/
.raven-claude/
.raven-claude-guard/

# Python
__pycache__/
*.py[cod]
.venv/
venv/

# Node
node_modules/

# OS
.DS_Store
Thumbs.db
GIEOF
    echo -e "  ${G}✅ .gitignore created${N}"
else
    MISSING=""
    for E in ".env" "*.pem" "manifest.secrets.json" "raven-claude/"; do
        grep -q "$E" "$PROJECT_DIR/.gitignore" 2>/dev/null || MISSING="$MISSING $E"
    done
    if [ -n "$MISSING" ]; then
        printf '\n# Raven\n.env\n.env.*\n*.pem\n*.key\nmanifest.secrets.json\n.raven/manifest.secrets.json\nraven-claude/\nraven-claude-guard/\n' \
            >> "$PROJECT_DIR/.gitignore"
        echo -e "  ${Y}⚠️  .gitignore updated — added:$MISSING${N}"
    else
        echo -e "  ${G}✅ .gitignore OK${N}"
    fi
fi
printf 'manifest.secrets.json\n.cache/\naudit/\n' > "$PROJECT_DIR/.raven/.gitignore"
