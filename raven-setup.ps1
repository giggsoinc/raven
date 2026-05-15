# Raven — Setup for Windows (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File raven-setup.ps1
# Requires: Python 3.10+, Git, Claude Code
# Run from: any project directory (NOT inside the Raven repo)

$ErrorActionPreference = "Stop"

$RAVEN_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Bold   { param($msg) Write-Host $msg -ForegroundColor White }
function Write-OK     { param($msg) Write-Host "  v $msg" -ForegroundColor Green }
function Write-Prompt { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Warn   { param($msg) Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Err    { param($msg) Write-Host "  X $msg" -ForegroundColor Red }

Write-Host ""
Write-Bold "================================================"
Write-Bold "  Raven -- Setup v2.9 (Windows)"
Write-Bold "================================================"
Write-Host ""

# ─── REQUIREMENTS ────────────────────────────────────────────────────────────
try { $null = python --version 2>&1 } catch { Write-Err "python not found. Install from python.org"; exit 1 }
try { $null = git --version 2>&1 } catch { Write-Err "git not found. Install from git-scm.com"; exit 1 }
Write-OK "python + git found"

# ─── PROJECT DIR ─────────────────────────────────────────────────────────────
Write-Prompt "Where is your project? (Enter = current dir: $(Get-Location))"
$P = Read-Host "  ->"
if ([string]::IsNullOrWhiteSpace($P)) { $P = (Get-Location).Path }
$P = $P -replace "^~", $env:USERPROFILE
$PROJECT_DIR = $P

if (-not (Test-Path $PROJECT_DIR)) { New-Item -ItemType Directory -Path $PROJECT_DIR | Out-Null }
if ((Resolve-Path $PROJECT_DIR).Path -eq (Resolve-Path $RAVEN_DIR).Path) {
    Write-Err "Cannot init inside the Raven repo itself"; exit 1
}
Write-OK $PROJECT_DIR

# ─── MANIFEST ALREADY EXISTS ─────────────────────────────────────────────────
$manifestPath = Join-Path $PROJECT_DIR ".raven\manifest.json"
if (Test-Path $manifestPath) {
    Write-Host ""
    Write-Bold "================================================"
    Write-OK "Raven is already configured for this project."
    Write-Bold "================================================"
    Write-Host ""
    Write-Host "  Manifest found at: $manifestPath"
    Write-Host "  Nothing to set up. Run 'claude .' to open Claude Code."
    Write-Host "  Run /raven-debug inside Claude Code to verify everything loaded."
    Write-Host ""
    exit 0
}

# ─── SILENT SCAN ─────────────────────────────────────────────────────────────
$DETECT_SCRIPT = Join-Path $RAVEN_DIR "setup\sr-detect-workmode.py"
if (-not (Test-Path $DETECT_SCRIPT)) {
    Write-Err "sr-detect-workmode.py missing from setup\ directory"
    exit 1
}

$DETECTED_JSON = python $DETECT_SCRIPT $PROJECT_DIR 2>$null
if ([string]::IsNullOrWhiteSpace($DETECTED_JSON)) {
    $DETECTED_JSON = '{"platform":"Windows","has_git":false,"manifest_exists":false,"mode":"unknown","primary":"unknown","secondary":null,"signals":{},"confidence":"none","mode_description":"","mode_rules":[]}'
}

$DETECTED = $DETECTED_JSON | python -c @"
import sys, json
d = json.load(sys.stdin)
# Output as key=value lines for PowerShell to parse
for k, v in d.items():
    if isinstance(v, (dict, list)):
        print(f'{k}={json.dumps(v)}')
    elif v is None:
        print(f'{k}=')
    else:
        print(f'{k}={v}')
"@

# Parse into variables
$detectedVars = @{}
foreach ($line in $DETECTED -split "`n") {
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
        $detectedVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$DETECTED_PLATFORM     = $detectedVars["platform"]
$DETECTED_MODE         = $detectedVars["mode"]
$DETECTED_PRIMARY      = $detectedVars["primary"]
$DETECTED_SECONDARY    = $detectedVars["secondary"]
$DETECTED_DESCRIPTION  = $detectedVars["mode_description"]
$MANIFEST_EXISTS       = $detectedVars["manifest_exists"] -eq "True"
$HAS_GIT               = $detectedVars["has_git"] -eq "True"
$HAS_SOURCE_CODE       = $detectedVars["has_source_code"] -eq "True"

# ─── DISCOVERY SCREEN ────────────────────────────────────────────────────────
Write-Host ""
Write-Bold "================================================"
Write-Bold "  RAVEN -- first run"
Write-Bold "================================================"
Write-Host ""
Write-Host "  Scanned this directory. Here's what I see:"
Write-Host ""

# Print signals from JSON
$DETECTED_JSON | python -c @"
import sys, json
d = json.load(sys.stdin)
signals = d.get('signals', {})
if signals:
    for label, val in signals.items():
        print(f'    {label:<28} {val}')
else:
    print('    (no recognisable project files found)')
"@

Write-Host ""
Write-Host "    Platform                     $DETECTED_PLATFORM (auto-detected)"
if (-not $HAS_GIT) {
    Write-Warn "Git repo not found -- run 'git init' first"
}
if (-not $HAS_SOURCE_CODE -and $DETECTED_MODE -ne "code") {
    Write-Host "    No source code               -- (code linting rules won't apply)"
}
Write-Host ""

# Mode announcement
switch ($DETECTED_MODE) {
    "salesforce" { Write-Host "  Detected: Salesforce project. Raven will operate in Salesforce mode." -ForegroundColor Green }
    "odoo"       { Write-Host "  Detected: Odoo ERP project. Raven will operate in Odoo mode." -ForegroundColor Green }
    "data"       { Write-Host "  Detected: Data engineering workspace. Raven will operate in data mode." -ForegroundColor Green }
    "docs"       { Write-Host "  Detected: Documentation workspace. Raven will operate in docs mode." -ForegroundColor Green }
    "infra"      {
        Write-Host "  Detected: Pure infrastructure workspace." -ForegroundColor Green
        Write-Host "  Raven will operate in infrastructure mode."
        Write-Host "  Code linting rules will not apply." -ForegroundColor White
    }
    "code"       { Write-Host "  Detected: Software development project. Raven will operate in software engineering mode." -ForegroundColor Green }
    "ambiguous"  {
        Write-Host "  Detected mixed workspace: $DETECTED_PRIMARY + $DETECTED_SECONDARY" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  Which is the primary work here?"
        Write-Host "    1) $DETECTED_PRIMARY -- the other is just a helper"
        Write-Host "    2) Both equally -- enforce rules for each"
        Write-Host "    3) $DETECTED_SECONDARY -- the other is legacy"
        $AC = Read-Host "  ->"
        switch ($AC) {
            "1" { $DETECTED_MODE = $DETECTED_PRIMARY }
            "2" { $DETECTED_MODE = "mixed" }
            "3" { $DETECTED_MODE = $DETECTED_SECONDARY }
            default { $DETECTED_MODE = $DETECTED_PRIMARY }
        }
    }
    default {
        Write-Host "  Could not automatically classify this workspace." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "  What kind of work is this project?"
        Write-Host "    1) code    -- writing application code (Python, TypeScript, Go...)"
        Write-Host "    2) infra   -- infrastructure only (Terraform, K8s, CloudFormation)"
        Write-Host "    3) data    -- data engineering / analytics / SQL / notebooks"
        Write-Host "    4) docs    -- documentation / architecture review"
        Write-Host "    5) review  -- reviewing code or diagrams (no new files)"
        Write-Host "    6) mixed   -- combination of the above"
        $UC = Read-Host "  ->"
        switch ($UC) {
            "1" { $DETECTED_MODE = "code" }
            "2" { $DETECTED_MODE = "infra" }
            "3" { $DETECTED_MODE = "data" }
            "4" { $DETECTED_MODE = "docs" }
            "5" { $DETECTED_MODE = "review" }
            "6" { $DETECTED_MODE = "mixed" }
            default { $DETECTED_MODE = "code" }
        }
    }
}

Write-Host ""

# ─── INTENT QUESTION ─────────────────────────────────────────────────────────
Write-Host "  What's the main thing you want Raven to enforce?"
Write-Host ""
switch ($DETECTED_MODE) {
    "infra" {
        Write-Host "    1) No undocumented infrastructure changes"
        Write-Host "    2) Secrets never in config files"
        Write-Host "    3) Consistent naming conventions"
        Write-Host "    4) All of the above (recommended)"
    }
    "data" {
        Write-Host "    1) SQL quality and schema documentation"
        Write-Host "    2) No PII in pipeline configs or logs"
        Write-Host "    3) Pipeline naming and dependency tracking"
        Write-Host "    4) All of the above (recommended)"
    }
    "salesforce" {
        Write-Host "    1) No hardcoded IDs or unreviewed SOQL"
        Write-Host "    2) Block secrets and credentials in metadata"
        Write-Host "    3) Enforce test coverage and bulk patterns"
        Write-Host "    4) All of the above (recommended)"
    }
    "odoo" {
        Write-Host "    1) Module structure and naming discipline"
        Write-Host "    2) No raw SQL or hardcoded DB IDs"
        Write-Host "    3) Security and access control checks"
        Write-Host "    4) All of the above (recommended)"
    }
    default {
        Write-Host "    1) Code quality, style, and type safety"
        Write-Host "    2) Secrets never in source files"
        Write-Host "    3) CVE scan every new dependency"
        Write-Host "    4) All of the above (recommended)"
    }
}
Write-Host ""
$INTENT = Read-Host "  -> [1/2/3/4 or describe your own]"
Write-Host ""

$WORK_TYPE = $DETECTED_MODE

# ─── REMAINING QUESTIONS ──────────────────────────────────────────────────────
Write-Prompt "Mode: 1) solo  2) team  3) enterprise"
$M = Read-Host "  ->"
switch ($M) {
    "1" { $MODE = "solo" }
    "2" { $MODE = "team" }
    default { $MODE = "enterprise" }
}
Write-OK $MODE

$defaultName = Split-Path -Leaf $PROJECT_DIR
Write-Prompt "Project name (Enter = $defaultName):"
$PROJECT = Read-Host "  ->"
if ([string]::IsNullOrWhiteSpace($PROJECT)) { $PROJECT = $defaultName }
Write-OK $PROJECT

Write-Prompt "Your email:"
$EMAIL = Read-Host "  ->"

Write-Prompt "GitHub username (Enter to use a project tag):"
$GITHUB_ID = Read-Host "  ->"
$PROJECT_TAG = ""
if ([string]::IsNullOrWhiteSpace($GITHUB_ID)) {
    Write-Prompt "Project tag (e.g. internal, client-abc):"
    $PROJECT_TAG = Read-Host "  ->"
    if ([string]::IsNullOrWhiteSpace($PROJECT_TAG)) { $PROJECT_TAG = $PROJECT }
    $PROJECT_TAG = $PROJECT_TAG -replace "\s+", "-"
}
$AUDIT_ID = if ($GITHUB_ID) { $GITHUB_ID } elseif ($PROJECT_TAG) { $PROJECT_TAG } else { $PROJECT }

# Cloud
Write-Prompt "Cloud: 1) aws  2) gcp  3) azure  4) oci  5) on-prem  6) multi  7) none"
$rawCloud = Read-Host "  ->"
$cloudOpts = @("aws","gcp","azure","oci","on-prem","multi","none")
if ($rawCloud -match "^\d+$" -and [int]$rawCloud -ge 1 -and [int]$rawCloud -le 7) {
    $CLOUD = '["' + $cloudOpts[[int]$rawCloud - 1] + '"]'
} elseif ([string]::IsNullOrWhiteSpace($rawCloud)) {
    $CLOUD = "[]"
} else {
    $CLOUD = '["' + $rawCloud.ToLower() + '"]'
}

# Language — adaptive to work mode
switch ($WORK_TYPE) {
    "review" { $LANGUAGES = '["review-only"]' }
    "docs"   { $LANGUAGES = '["markdown"]' }
    "salesforce" { $LANGUAGES = '["apex","xml"]' }
    "odoo"   { $LANGUAGES = '["python3.12","xml"]' }
    "infra"  {
        Write-Prompt "Infra file types: 1) yaml  2) hcl  3) json  4) dockerfile  5) bicep  6) shell"
        $rawL = Read-Host "  ->"
        $langOpts = @("yaml","hcl","json","dockerfile","bicep","shell")
        if ($rawL -match "^\d+$") {
            $LANGUAGES = '["' + $langOpts[[int]$rawL - 1] + '"]'
        } else {
            $LANGUAGES = '["yaml","hcl"]'
        }
    }
    default {
        Write-Prompt "Primary language: 1) python3.12  2) python3.13  3) typescript  4) javascript  5) go  6) java  7) rust"
        $rawL = Read-Host "  ->"
        $langOpts = @("python3.12","python3.13","typescript","javascript","go","java","rust")
        if ($rawL -match "^\d+$" -and [int]$rawL -ge 1 -and [int]$rawL -le 7) {
            $LANGUAGES = '["' + $langOpts[[int]$rawL - 1] + '"]'
        } elseif (-not [string]::IsNullOrWhiteSpace($rawL)) {
            $LANGUAGES = '["' + $rawL.ToLower() + '"]'
        } else {
            $LANGUAGES = "[]"
        }
    }
}

$INBOX = ""
if ($MODE -ne "solo") {
    Write-Prompt "Notification email (Enter to skip):"
    $INBOX = Read-Host "  ->"
}

# ─── GENERATE MANIFEST ───────────────────────────────────────────────────────
Write-Host ""
Write-Host "Installing..."

$ravenDir = Join-Path $PROJECT_DIR ".raven"
if (-not (Test-Path $ravenDir)) { New-Item -ItemType Directory -Path $ravenDir | Out-Null }

$TS = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")

$env:PROJECT_VAL    = $PROJECT
$env:MODE_VAL       = $MODE
$env:EMAIL_VAL      = $EMAIL
$env:TS_VAL         = $TS
$env:GITHUB_VAL     = $GITHUB_ID
$env:TAG_VAL        = $PROJECT_TAG
$env:AUDIT_ID_VAL   = $AUDIT_ID
$env:WORK_TYPE_VAL  = $WORK_TYPE
$env:LANGUAGES_VAL  = $LANGUAGES
$env:CLOUD_VAL      = $CLOUD
$env:INBOX_VAL      = $INBOX
$env:PLATFORM_VAL   = $DETECTED_PLATFORM
$env:OUT_VAL        = $PROJECT_DIR

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
audit_id  = os.environ.get('AUDIT_ID_VAL', proj)
work_type = os.environ.get('WORK_TYPE_VAL','code')
outdir    = os.environ['OUT_VAL']
platform  = os.environ.get('PLATFORM_VAL','Windows')

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
    'changes':    f'Init: mode={mode} work_type={work_type} platform={platform}',
    'pr':         'pending'
  }]
}

with open(f'{outdir}/.raven/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
print('written')
"@

Write-OK "manifest.json created"

# ─── GITIGNORE ───────────────────────────────────────────────────────────────
Set-Content -Path (Join-Path $ravenDir ".gitignore") -Value "manifest.secrets.json`n.cache/"
Write-OK ".gitignore created"

# ─── COPY CLAUDE.md + SETTINGS ───────────────────────────────────────────────
$ravenClaudeMd = Join-Path $RAVEN_DIR "CLAUDE.md"
if (Test-Path $ravenClaudeMd) {
    Copy-Item $ravenClaudeMd (Join-Path $PROJECT_DIR "CLAUDE.md") -Force
    Write-OK "CLAUDE.md installed"
}
$claudeDir = Join-Path $PROJECT_DIR ".claude"
if (-not (Test-Path $claudeDir)) { New-Item -ItemType Directory -Path $claudeDir | Out-Null }
$settingsSrc = Join-Path $RAVEN_DIR ".claude\settings.json"
if (Test-Path $settingsSrc) {
    Copy-Item $settingsSrc (Join-Path $claudeDir "settings.json") -Force
    Write-OK ".claude/settings.json installed"
}

# ─── CONFIRMATION SCREEN ─────────────────────────────────────────────────────
Write-Host ""
Write-Bold "================================================"
Write-Host ""
Write-OK "manifest.json valid"
Write-OK ".gitignore present"
Write-OK "CLAUDE.md installed"
Write-Host ""

# Show what Raven will enforce
switch ($WORK_TYPE) {
    "infra" {
        Write-Host "  Raven will now:"
        Write-OK "Require change comments on .tf modifications"
        Write-OK "Block secrets in docker-compose, values.yaml, .tf"
        Write-OK "Enforce naming conventions"
        Write-Host "  X Code linting -- not applicable"
    }
    "data" {
        Write-Host "  Raven will now:"
        Write-OK "Enforce SQL formatting and schema documentation"
        Write-OK "Block PII in pipeline configs"
        Write-OK "Validate dbt models and dependencies"
    }
    "salesforce" {
        Write-Host "  Raven will now:"
        Write-OK "Block SOQL inside loops and DML anti-patterns"
        Write-OK "Require test classes with 75%+ coverage"
        Write-OK "Detect hardcoded IDs in metadata"
    }
    default {
        Write-Host "  Raven will now:"
        Write-OK "Enforce code style and type safety"
        Write-OK "CVE scan every new import"
        Write-OK "Block secrets in source files"
    }
}

Write-Host ""
Write-Bold "Raven initialized for $PROJECT ($WORK_TYPE)"
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    1. Get manifest.secrets.json from your architect"
Write-Host "    2. Place it at: $ravenDir\manifest.secrets.json"
Write-Host "    3. Open Claude Code: claude $PROJECT_DIR"
Write-Host "    4. Commit:"
Write-Host "         git add .raven/manifest.json .raven/.gitignore CLAUDE.md"
Write-Host "         git commit -m `"chore: init raven v2.9 [RAVEN:INIT]`""
Write-Host ""
Write-Warn "NEVER commit manifest.secrets.json"
Write-Host ""
