# Raven — Setup for Windows (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File raven-setup.ps1
# Requires: Python 3.10+, Git, Claude Code
# Run from: any project directory (NOT inside the Raven repo)

$ErrorActionPreference = "Stop"

$RAVEN_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

# Colours
function Write-Bold   { param($msg) Write-Host $msg -ForegroundColor White }
function Write-OK     { param($msg) Write-Host "  ✅ $msg" -ForegroundColor Green }
function Write-Prompt { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Warn   { param($msg) Write-Host "  ⚠️  $msg" -ForegroundColor Yellow }
function Write-Err    { param($msg) Write-Host "  ❌ $msg" -ForegroundColor Red }

Write-Host ""
Write-Bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Bold "  Raven — Setup v2.9 (Windows)"
Write-Bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# ─── PRE-FLIGHT ──────────────────────────────────────────────────────────────
Write-Host "Checking requirements..."

try { $null = python --version 2>&1 } catch { Write-Err "python not found. Install from python.org"; exit 1 }
try { $null = git --version 2>&1 } catch { Write-Err "git not found. Install from git-scm.com"; exit 1 }

Write-OK "python + git found"

# ─── PROJECT DIR ─────────────────────────────────────────────────────────────
Write-Prompt "Where is your project? (Enter = current dir: $(Get-Location))"
$P = Read-Host "  →"
if ([string]::IsNullOrWhiteSpace($P)) { $P = (Get-Location).Path }
$P = $P -replace "^~", $env:USERPROFILE
$PROJECT_DIR = $P

if (-not (Test-Path $PROJECT_DIR)) { New-Item -ItemType Directory -Path $PROJECT_DIR | Out-Null }
if ((Resolve-Path $PROJECT_DIR).Path -eq (Resolve-Path $RAVEN_DIR).Path) {
    Write-Err "Cannot init inside the Raven repo itself"
    exit 1
}
Write-OK $PROJECT_DIR

# Check if manifest already exists — if so, load and trust it
$manifestPath = Join-Path $PROJECT_DIR ".raven\manifest.json"
if (Test-Path $manifestPath) {
    Write-Host ""
    Write-Warn "Manifest already exists at $manifestPath"
    Write-Host "  Loading existing manifest. Raven is already initialized for this project."
    Write-Host "  Run /raven-init inside Claude Code if you need to modify the manifest."
    Write-Host ""
    exit 0
}

# ─── MODE ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Prompt "Mode:"
Write-Host "  1) solo       — lone developer, no approvals"
Write-Host "  2) team       — small team, email approvals"
Write-Host "  3) enterprise — full governance, org manifest"
$M = Read-Host "  →"
switch ($M) {
    "1" { $MODE = "solo" }
    "2" { $MODE = "team" }
    default { $MODE = "enterprise" }
}
Write-OK $MODE

# ─── WORK TYPE ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Prompt "What kind of work is this project?"
Write-Host "  1) code    — writing application code (Python, TypeScript, Go, etc.)"
Write-Host "  2) infra   — infrastructure only (Terraform, K8s YAML, CloudFormation)"
Write-Host "  3) review  — reviewing code, docs, or architecture"
Write-Host "  4) mixed   — both code and infrastructure"
$WT = Read-Host "  →"
switch ($WT) {
    "1" { $WORK_TYPE = "code" }
    "2" { $WORK_TYPE = "infra" }
    "3" { $WORK_TYPE = "review" }
    "4" { $WORK_TYPE = "mixed" }
    default { $WORK_TYPE = "code" }
}
Write-OK $WORK_TYPE

# ─── PROJECT NAME ────────────────────────────────────────────────────────────
$defaultName = Split-Path -Leaf $PROJECT_DIR
Write-Host ""
Write-Prompt "Project name (Enter = $defaultName):"
$PROJECT = Read-Host "  →"
if ([string]::IsNullOrWhiteSpace($PROJECT)) { $PROJECT = $defaultName }
Write-OK $PROJECT

# ─── EMAIL ───────────────────────────────────────────────────────────────────
Write-Prompt "Your email:"
$EMAIL = Read-Host "  →"
Write-OK $EMAIL

# ─── GITHUB / TAG ────────────────────────────────────────────────────────────
Write-Prompt "GitHub username (Enter to use a project tag instead):"
$GITHUB_ID = Read-Host "  →"
$PROJECT_TAG = ""
if ([string]::IsNullOrWhiteSpace($GITHUB_ID)) {
    Write-Prompt "Project tag for audit trail (e.g. internal, client-abc):"
    $PROJECT_TAG = Read-Host "  →"
    if ([string]::IsNullOrWhiteSpace($PROJECT_TAG)) { $PROJECT_TAG = $PROJECT }
    $PROJECT_TAG = $PROJECT_TAG -replace "\s+", "-"
    Write-OK "Tag: $PROJECT_TAG"
} else {
    Write-OK "GitHub: $GITHUB_ID"
}
$AUDIT_ID = if ($GITHUB_ID) { $GITHUB_ID } elseif ($PROJECT_TAG) { $PROJECT_TAG } else { $PROJECT }

# ─── LANGUAGES ───────────────────────────────────────────────────────────────
Write-Host ""
if ($WORK_TYPE -eq "review") {
    $LANGUAGES = '["review-only"]'
    Write-OK "review-only (skipping language selection)"
} elseif ($WORK_TYPE -eq "infra") {
    Write-Prompt "Infra file types used (numbers, comma-sep, or type freely):"
    Write-Host "  1) yaml  2) hcl  3) json  4) dockerfile  5) bicep  6) shell"
    $rawLang = Read-Host "  →"
    $LANGUAGES = python -c "
import sys, json
opts=['yaml','hcl','json','dockerfile','bicep','shell']
raw='$rawLang'
if not raw.strip(): print('[]'); exit()
result=[]
for tok in raw.split(','):
    tok=tok.strip()
    if tok.isdigit() and 1<=int(tok)<=len(opts): result.append(opts[int(tok)-1])
    elif tok: result.append(tok.lower())
print(json.dumps(list(dict.fromkeys(result))))
"
    Write-OK "$LANGUAGES"
} else {
    Write-Prompt "Languages (numbers, comma-sep, or type freely):"
    Write-Host "  1) python3.13  2) python3.12  3) python3.11"
    Write-Host "  4) typescript  5) javascript  6) go  7) rust  8) java"
    Write-Host "  9) kotlin  10) swift  11) csharp  12) yaml  13) hcl  14) shell  15) sql"
    $rawLang = Read-Host "  →"
    $LANGUAGES = python -c "
import sys, json
opts=['python3.13','python3.12','python3.11','typescript','javascript','go','rust','java','kotlin','swift','csharp','yaml','hcl','shell','sql']
raw='$rawLang'
if not raw.strip(): print('[]'); exit()
result=[]
for tok in raw.split(','):
    tok=tok.strip()
    if tok.isdigit() and 1<=int(tok)<=len(opts): result.append(opts[int(tok)-1])
    elif tok: result.append(tok.lower())
print(json.dumps(list(dict.fromkeys(result))))
"
    Write-OK "$LANGUAGES"
}

# ─── CLOUD ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Prompt "Cloud provider (numbers, comma-sep, or type freely):"
Write-Host "  1) aws  2) gcp  3) azure  4) oci  5) on-prem  6) multi"
$rawCloud = Read-Host "  →"
$CLOUD = python -c "
import sys, json
opts=['aws','gcp','azure','oci','on-prem','multi']
raw='$rawCloud'
if not raw.strip(): print('[]'); exit()
result=[]
for tok in raw.split(','):
    tok=tok.strip()
    if tok.isdigit() and 1<=int(tok)<=len(opts): result.append(opts[int(tok)-1])
    elif tok: result.append(tok.lower())
print(json.dumps(list(dict.fromkeys(result))))
"
Write-OK $CLOUD

# ─── NOTIFICATION EMAIL ──────────────────────────────────────────────────────
$INBOX = ""
if ($MODE -ne "solo") {
    Write-Prompt "Notification email (Enter to skip):"
    $INBOX = Read-Host "  →"
}

# ─── GENERATE MANIFEST ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "Installing..."

$ravenDir = Join-Path $PROJECT_DIR ".raven"
if (-not (Test-Path $ravenDir)) { New-Item -ItemType Directory -Path $ravenDir | Out-Null }

$TS = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")

$env:PROJECT_VAL   = $PROJECT
$env:MODE_VAL      = $MODE
$env:EMAIL_VAL     = $EMAIL
$env:TS_VAL        = $TS
$env:GITHUB_VAL    = $GITHUB_ID
$env:TAG_VAL       = $PROJECT_TAG
$env:AUDIT_ID_VAL  = $AUDIT_ID
$env:WORK_TYPE_VAL = $WORK_TYPE
$env:LANGUAGES_VAL = $LANGUAGES
$env:CLOUD_VAL     = $CLOUD
$env:INBOX_VAL     = $INBOX
$env:OUT_VAL       = $PROJECT_DIR

python -c @"
import json, os

def jl(val):
    try:
        v = json.loads(val)
        return v if isinstance(v, list) else [val]
    except:
        return [val] if val and val not in ('[]','none','None') else []

proj      = os.environ['PROJECT_VAL']
mode      = os.environ['MODE_VAL']
email     = os.environ['EMAIL_VAL']
ts        = os.environ['TS_VAL']
github    = os.environ.get('GITHUB_VAL','')
tag       = os.environ.get('TAG_VAL','')
audit_id  = os.environ.get('AUDIT_ID_VAL', proj)
work_type = os.environ.get('WORK_TYPE_VAL','code')
outdir    = os.environ['OUT_VAL']

manifest = {
  'project':   proj,
  'version':   '1.0',
  'mode':      mode,
  'github_id': github,
  'audit_tag': audit_id,
  'stack': {
    'work_type': work_type,
    'language':  jl(os.environ['LANGUAGES_VAL']),
    'cloud':     jl(os.environ['CLOUD_VAL']),
    'apps':      [],
    'libraries': []
  },
  'standards':     'raven-v2.9',
  'approval_mode': 'auto' if mode == 'solo' else 'first_responder',
  'guard': {
    'enabled':  True,
    'db':       {'mass_deletion_threshold': 100},
    'git':      {'force_push': 'hard_block'},
    'infra':    {'terraform_state': 'hard_block'},
    'firewall': {'open_world': 'hard_block'}
  },
  'style': {
    'max_lines_per_file':      150,
    'require_type_hints':      True,
    'require_docstrings':      True,
    'forbid_print_statements': True
  },
  'changelog': [{
    'version':    '1.0',
    'changed_by': email,
    'github_id':  github,
    'audit_tag':  audit_id,
    'changed_at': ts,
    'changes':    f'Init: mode={mode} work_type={work_type}',
    'pr':         'pending'
  }]
}

with open(f'{outdir}/.raven/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
print('written')
"@

Write-OK "manifest.json created"

# ─── GITIGNORE ───────────────────────────────────────────────────────────────
$gitignorePath = Join-Path $ravenDir ".gitignore"
Set-Content -Path $gitignorePath -Value "manifest.secrets.json`n.cache/"
Write-OK ".gitignore created"

# ─── CLAUDE.md ───────────────────────────────────────────────────────────────
$ravenRepoClaudeMd = Join-Path $RAVEN_DIR "CLAUDE.md"
$projectClaudeMd   = Join-Path $PROJECT_DIR "CLAUDE.md"
if (Test-Path $ravenRepoClaudeMd) {
    Copy-Item -Path $ravenRepoClaudeMd -Destination $projectClaudeMd -Force
    Write-OK "CLAUDE.md installed"
}

# ─── CLAUDE SETTINGS ─────────────────────────────────────────────────────────
$claudeDir      = Join-Path $PROJECT_DIR ".claude"
$claudeSettings = Join-Path $claudeDir "settings.json"
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir | Out-Null }
$settingsContent = Join-Path $RAVEN_DIR ".claude\settings.json"
if (Test-Path $settingsContent) {
    Copy-Item -Path $settingsContent -Destination $claudeSettings -Force
    Write-OK ".claude/settings.json installed"
}

# ─── VERIFY ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Bold "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

if (Test-Path $manifestPath) { Write-OK "manifest.json valid" } else { Write-Err "manifest.json missing — something went wrong"; exit 1 }
if (Test-Path $gitignorePath) { Write-OK ".gitignore present" } else { Write-Warn ".gitignore missing" }
if (Test-Path $projectClaudeMd) { Write-OK "CLAUDE.md present" } else { Write-Warn "CLAUDE.md missing" }

Write-Host ""
Write-Bold "Raven initialized for $PROJECT ($WORK_TYPE)"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Get manifest.secrets.json from your architect via secure channel"
Write-Host "  2. Place it at: $ravenDir\manifest.secrets.json"
Write-Host "  3. Open Claude Code in: $PROJECT_DIR"
Write-Host "  4. Commit the manifest:"
Write-Host ""
Write-Host "     git add .raven/manifest.json .raven/.gitignore CLAUDE.md"
Write-Host "     git commit -m `"chore: init raven manifest v1.0 [RAVEN:INIT]`""
Write-Host ""
Write-Warn "NEVER commit manifest.secrets.json"
Write-Warn "NEVER commit .raven/.cache/"
Write-Host ""
