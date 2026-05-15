#Requires -RunAsAdministrator
# Raven — Enterprise Installer for Windows (PowerShell)
# Run as Administrator in an elevated PowerShell session.
#
# What this does:
#   1. Installs Raven to C:\Program Files\Raven\ (system-wide, all users)
#   2. Creates managed-mcp.json at the Claude Code managed path
#      -> every developer on this machine gets Raven MCP auto-loaded
#   3. Creates managed-settings.json (hooks, permissions)
#   4. Interactively creates manifest.org.json (org-level locked rules)
#   5. Optionally provisions %USERPROFILE%\.claude\ for all existing users
#   6. Adds raven-setup.ps1 to the system PATH
#
# Usage (interactive):
#   powershell -ExecutionPolicy Bypass -File install-enterprise.ps1
#
# Usage (MDM / GPO silent mode):
#   powershell -ExecutionPolicy Bypass -File install-enterprise.ps1 `
#     -Silent -OrgName "Acme Corp" -OrgEmail "it@acme.com"
#
# Requirements: git, python, Claude Code (claude)

[CmdletBinding()]
param(
    [switch]$Silent,
    [string]$OrgName  = "",
    [string]$OrgEmail = ""
)

$ErrorActionPreference = "Stop"

# ─── SILENT MODE VALIDATION ──────────────────────────────────────────────────
if ($Silent) {
    if ([string]::IsNullOrWhiteSpace($OrgName)) {
        Write-Host "ERROR: -OrgName is required when using -Silent mode." -ForegroundColor Red
        Write-Host "Usage: install-enterprise.ps1 -Silent -OrgName `"Acme Corp`" -OrgEmail `"it@acme.com`"" -ForegroundColor Yellow
        exit 1
    }
    if ([string]::IsNullOrWhiteSpace($OrgEmail)) {
        Write-Host "ERROR: -OrgEmail is required when using -Silent mode." -ForegroundColor Red
        Write-Host "Usage: install-enterprise.ps1 -Silent -OrgName `"Acme Corp`" -OrgEmail `"it@acme.com`"" -ForegroundColor Yellow
        exit 1
    }
}

# ─── HELPER FUNCTIONS ────────────────────────────────────────────────────────
function Write-Bold  { param($msg) Write-Host $msg -ForegroundColor White }
function Write-OK    { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Info  { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Warn  { param($msg) Write-Host "  [!] $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "  [X] $msg" -ForegroundColor Red }

function Ask-Host {
    param(
        [string]$Prompt,
        [string]$Default = ""
    )
    Write-Host "  $Prompt" -ForegroundColor Cyan
    if ($Default) { Write-Host "  Default: $Default" -ForegroundColor Yellow }
    $val = Read-Host "  ->"
    if ([string]::IsNullOrWhiteSpace($val)) { return $Default }
    return $val
}

# ─── PATHS ───────────────────────────────────────────────────────────────────
$RAVEN_SYSTEM  = Join-Path $env:ProgramFiles "Raven"
$RAVEN_MCP     = Join-Path $RAVEN_SYSTEM "mcp\server.py"
$MANAGED_DIR   = Join-Path $env:ProgramData "ClaudeCode"
$REPO          = "https://github.com/giggsoinc/raven.git"

# ─── BANNER ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Bold "================================================"
Write-Bold "  Raven -- Enterprise Install v2.9 (Windows)"
Write-Bold "  IT / Admin deployment"
Write-Bold "================================================"
Write-Host ""

if ($Silent) {
    Write-Warn "Running in SILENT / MDM mode — prompts suppressed"
    Write-Host ""
}

# ─── REQUIREMENTS ────────────────────────────────────────────────────────────
Write-Info "Checking prerequisites..."

try { $null = git --version 2>&1 } catch {
    Write-Err "git not found. Install from https://git-scm.com and re-run."
    exit 1
}
Write-OK "git found"

try { $null = python --version 2>&1 } catch {
    Write-Err "python not found. Install from https://python.org (check 'Add to PATH') and re-run."
    exit 1
}
Write-OK "python found"

$CLAUDE_FOUND = $true
try { $null = claude --version 2>&1 } catch {
    Write-Warn "Claude Code (claude) not found in PATH."
    Write-Host "    Install: https://claude.ai/download" -ForegroundColor Yellow
    Write-Host "    Raven will install — re-run after Claude Code is set up if needed." -ForegroundColor Yellow
    $CLAUDE_FOUND = $false
}
if ($CLAUDE_FOUND) { Write-OK "Claude Code found" }

# ─── DOWNLOAD / UPDATE ───────────────────────────────────────────────────────
Write-Host ""
if (Test-Path (Join-Path $RAVEN_SYSTEM ".git")) {
    Write-Info "Updating Raven at $RAVEN_SYSTEM ..."
    git -C $RAVEN_SYSTEM pull --quiet
    Write-OK "Updated to latest"
} else {
    Write-Info "Installing Raven to $RAVEN_SYSTEM ..."
    if (-not (Test-Path $RAVEN_SYSTEM)) {
        New-Item -ItemType Directory -Path $RAVEN_SYSTEM -Force | Out-Null
    }
    git clone --quiet --depth=1 $REPO $RAVEN_SYSTEM
    Write-OK "Installed to $RAVEN_SYSTEM"
}

# ─── MANAGED-MCP.JSON ────────────────────────────────────────────────────────
Write-Host ""
Write-Info "Creating managed-mcp.json -> $MANAGED_DIR ..."

if (-not (Test-Path $MANAGED_DIR)) {
    New-Item -ItemType Directory -Path $MANAGED_DIR -Force | Out-Null
}

# Use forward slashes inside JSON for Python compatibility; escape backslashes.
$RAVEN_MCP_JSON = $RAVEN_MCP -replace "\\", "\\\\"

$mcpJson = @"
{
  "_comment": "Raven Enterprise MCP — auto-loaded for all Claude Code users on this machine. Do not edit manually. Re-run install-enterprise.ps1 to update.",
  "mcpServers": {
    "raven": {
      "type":    "stdio",
      "command": "python",
      "args":    ["$RAVEN_MCP_JSON"],
      "env":     {}
    }
  }
}
"@

Set-Content -Path (Join-Path $MANAGED_DIR "managed-mcp.json") -Value $mcpJson -Encoding UTF8
Write-OK "managed-mcp.json -> $MANAGED_DIR\managed-mcp.json"
Write-Info "MCP server path: $RAVEN_MCP"

# ─── MANAGED-SETTINGS.JSON ───────────────────────────────────────────────────
Write-Host ""
Write-Info "Creating managed-settings.json (hooks + permissions) ..."

$TOOL_GUARD = Join-Path $RAVEN_SYSTEM "raven-core\tool-guard.py"
$TOOL_GUARD_JSON = $TOOL_GUARD -replace "\\", "\\\\"

$settingsJson = @"
{
  "_comment": "Raven Enterprise — managed settings. Controls hooks and permissions for all users.",
  "permissions": {
    "deny": [
      "Bash(curl * | bash)",
      "Bash(curl * | sh)",
      "Bash(wget * | bash)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python $TOOL_GUARD_JSON"
          }
        ]
      }
    ]
  }
}
"@

Set-Content -Path (Join-Path $MANAGED_DIR "managed-settings.json") -Value $settingsJson -Encoding UTF8
Write-OK "managed-settings.json -> $MANAGED_DIR\managed-settings.json"

# ─── ORG MANIFEST ────────────────────────────────────────────────────────────
Write-Host ""
Write-Bold "================================================"
Write-Bold "  Org Manifest -- locked rules for all projects"
Write-Bold "================================================"
Write-Host ""

if (-not $Silent) {
    Write-Host "  These fields will be locked in every developer's project manifest." -ForegroundColor White
    Write-Host "  Developers cannot override them." -ForegroundColor White
    Write-Host ""
}

# Collect org name
if ($Silent) {
    $MANIFEST_ORG_NAME = $OrgName
} else {
    $MANIFEST_ORG_NAME = Ask-Host "Organisation name:" "MyOrg"
}

# Collect org email
if ($Silent) {
    $MANIFEST_ORG_EMAIL = $OrgEmail
} else {
    $MANIFEST_ORG_EMAIL = Ask-Host "IT / architect email (audit trail author):" "it@example.com"
}

# Approval mode
if ($Silent) {
    $APPROVAL_MODE = "first_responder"
} else {
    Write-Host ""
    Write-Host "  Approval mode:" -ForegroundColor Cyan
    Write-Host "  1) first_responder  -- first to approve wins (default)"
    Write-Host "  2) majority_vote    -- majority of architects must agree"
    Write-Host "  3) owner_only       -- only the project owner can approve"
    $AM = Read-Host "  ->"
    switch ($AM) {
        "2" { $APPROVAL_MODE = "majority_vote" }
        "3" { $APPROVAL_MODE = "owner_only" }
        default { $APPROVAL_MODE = "first_responder" }
    }
}

# Token control
if ($Silent) {
    $TOKEN_CONTROL = "per_developer"
} else {
    Write-Host ""
    Write-Host "  Token control:" -ForegroundColor Cyan
    Write-Host "  1) per_developer  -- each dev has their own quota (default)"
    Write-Host "  2) per_project    -- project pool shared by all devs"
    Write-Host "  3) per_team       -- team pool"
    $TC = Read-Host "  ->"
    switch ($TC) {
        "2" { $TOKEN_CONTROL = "per_project" }
        "3" { $TOKEN_CONTROL = "per_team" }
        default { $TOKEN_CONTROL = "per_developer" }
    }
}

$TS = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$ORG_MANIFEST_PATH = Join-Path $RAVEN_SYSTEM "manifest.org.json"

# Write manifest via python inline (mirrors bash version exactly)
$env:ORG_NAME_VAL      = $MANIFEST_ORG_NAME
$env:ORG_EMAIL_VAL     = $MANIFEST_ORG_EMAIL
$env:APPROVAL_MODE_VAL = $APPROVAL_MODE
$env:TOKEN_CONTROL_VAL = $TOKEN_CONTROL
$env:TS_VAL            = $TS
$env:RAVEN_SYSTEM_VAL  = $RAVEN_SYSTEM

python -c @"
import json, os

org_name      = os.environ['ORG_NAME_VAL']
org_email     = os.environ['ORG_EMAIL_VAL']
approval_mode = os.environ['APPROVAL_MODE_VAL']
token_control = os.environ['TOKEN_CONTROL_VAL']
ts            = os.environ['TS_VAL']
raven_system  = os.environ['RAVEN_SYSTEM_VAL']

org_manifest = {
  '_layer':  'org',
  '_locked': [
    'standards',
    'approval_mode',
    'guard.enabled',
    'tokens.control'
  ],
  'project':       org_name,
  'version':       '1.0',
  'standards':     'raven-v2.9',
  'approval_mode': approval_mode,
  'guard': {
    'enabled': True,
    'git':      {'force_push': 'hard_block'},
    'infra':    {'terraform_state': 'hard_block'},
    'firewall': {'open_world': 'hard_block'},
    'db':       {'mass_deletion_threshold': 100, 'truncation': 'hard_block'}
  },
  'tokens': {
    'control':   token_control,
    'warnings':  [25, 50, 75, 80, 90, 95]
  },
  'style': {
    'max_lines_per_file':      150,
    'require_type_hints':      True,
    'require_docstrings':      True,
    'forbid_print_statements': True
  },
  'changelog': [{
    'version':    '1.0',
    'changed_by': org_email,
    'changed_at': ts,
    'changes':    f'Enterprise org manifest init -- {org_name}',
    'pr':         'pending'
  }]
}

org_manifest_path = os.path.join(raven_system, 'manifest.org.json')
with open(org_manifest_path, 'w') as f:
    json.dump(org_manifest, f, indent=2)

print(f'written to {org_manifest_path}')
"@

Write-OK "manifest.org.json -> $ORG_MANIFEST_PATH"

# ─── PROVISION EXISTING USERS ────────────────────────────────────────────────
Write-Host ""

if ($Silent) {
    $PROVISION = $true
} else {
    Write-Host "  Provision skills/agents to existing users' .claude\ directories?" -ForegroundColor Cyan
    Write-Host "  This wires all 35 skills for every existing developer on this machine." -ForegroundColor Yellow
    Write-Host "  1) Yes -- provision all users now"
    Write-Host "  2) No  -- developers run install.ps1 themselves on first login"
    $PROV_INPUT = Read-Host "  ->"
    $PROVISION = ($PROV_INPUT -eq "1")
}

if ($PROVISION) {
    Write-Host ""
    Write-Info "Provisioning all users..."

    # Users to skip
    $SKIP_USERS = @("Public", "Default", "Default User", "All Users", "defaultuser0", "WDAGUtilityAccount")

    $PROVISIONED = 0
    $RAVEN_MARKER = "# RAVEN GLOBAL CONFIG"

    $usersRoot = Join-Path $env:SystemDrive "Users"
    if (-not (Test-Path $usersRoot)) {
        Write-Warn "Could not find C:\Users\ — skipping user provisioning."
    } else {
        foreach ($userDir in (Get-ChildItem -Path $usersRoot -Directory -ErrorAction SilentlyContinue)) {
            $username = $userDir.Name

            # Skip system/special accounts
            if ($SKIP_USERS -contains $username) { continue }
            if ($username -like ".*")            { continue }

            $userClaude = Join-Path $userDir.FullName ".claude"

            try {
                # Create directory structure
                foreach ($subDir in @("skills", "agents", "commands", "scripts")) {
                    $target = Join-Path $userClaude $subDir
                    if (-not (Test-Path $target)) {
                        New-Item -ItemType Directory -Path $target -Force | Out-Null
                    }
                }

                # Copy all 35 skills
                $skillsSource = Join-Path $RAVEN_SYSTEM "core\skills"
                if (Test-Path $skillsSource) {
                    foreach ($skillDir in (Get-ChildItem -Path $skillsSource -Directory -ErrorAction SilentlyContinue)) {
                        $skillMd = Join-Path $skillDir.FullName "SKILL.md"
                        if (-not (Test-Path $skillMd)) { continue }

                        $destSkillDir = Join-Path $userClaude "skills\$($skillDir.Name)"
                        if (-not (Test-Path $destSkillDir)) {
                            New-Item -ItemType Directory -Path $destSkillDir -Force | Out-Null
                        }
                        Copy-Item $skillMd $destSkillDir -Force

                        $rulesDir = Join-Path $skillDir.FullName "rules"
                        if (Test-Path $rulesDir) {
                            $destRules = Join-Path $destSkillDir "rules"
                            if (-not (Test-Path $destRules)) {
                                New-Item -ItemType Directory -Path $destRules -Force | Out-Null
                            }
                            Copy-Item (Join-Path $rulesDir "*.md") $destRules -Force -ErrorAction SilentlyContinue
                        }
                    }
                }

                # Agents
                $agentsSource = Join-Path $RAVEN_SYSTEM "core\agents"
                if (Test-Path $agentsSource) {
                    Copy-Item (Join-Path $agentsSource "*.md") (Join-Path $userClaude "agents\") -Force -ErrorAction SilentlyContinue
                }

                # Commands
                $commandsSource = Join-Path $RAVEN_SYSTEM "core\commands"
                if (Test-Path $commandsSource) {
                    Copy-Item (Join-Path $commandsSource "*.md") (Join-Path $userClaude "commands\") -Force -ErrorAction SilentlyContinue
                }

                # Scripts — raven-core .py files
                $ravenCoreSource = Join-Path $RAVEN_SYSTEM "raven-core"
                if (Test-Path $ravenCoreSource) {
                    Copy-Item (Join-Path $ravenCoreSource "*.py") (Join-Path $userClaude "scripts\") -Force -ErrorAction SilentlyContinue
                }
                # Scripts — core/scripts .py files
                $coreScriptsSource = Join-Path $RAVEN_SYSTEM "core\scripts"
                if (Test-Path $coreScriptsSource) {
                    Copy-Item (Join-Path $coreScriptsSource "*.py") (Join-Path $userClaude "scripts\") -Force -ErrorAction SilentlyContinue
                }
                # Detection script
                $detectScript = Join-Path $RAVEN_SYSTEM "setup\sr-detect-workmode.py"
                if (Test-Path $detectScript) {
                    Copy-Item $detectScript (Join-Path $userClaude "scripts\") -Force -ErrorAction SilentlyContinue
                }

                # CLAUDE.md — idempotent update with RAVEN GLOBAL CONFIG marker
                $globalClaude  = Join-Path $userClaude "CLAUDE.md"
                $ravenClaudeSrc = Join-Path $RAVEN_SYSTEM "CLAUDE.md"

                if (Test-Path $ravenClaudeSrc) {
                    $ravenContent = Get-Content $ravenClaudeSrc -Raw -Encoding UTF8

                    if (Test-Path $globalClaude) {
                        $existing = Get-Content $globalClaude -Raw -Encoding UTF8
                        if ($existing -like "*$RAVEN_MARKER*") {
                            # Update the raven block in place, preserve content before marker
                            $idx = $existing.IndexOf($RAVEN_MARKER)
                            $pre = $existing.Substring(0, $idx)
                            Set-Content $globalClaude ($pre + $RAVEN_MARKER + "`n`n" + $ravenContent) -Encoding UTF8
                        } else {
                            # Append raven block after existing content
                            Add-Content $globalClaude ("`n`n$RAVEN_MARKER`n`n" + $ravenContent) -Encoding UTF8
                        }
                    } else {
                        Set-Content $globalClaude ("$RAVEN_MARKER`n`n" + $ravenContent) -Encoding UTF8
                    }
                }

                Write-Host "  [OK] $username" -ForegroundColor Green
                $PROVISIONED++

            } catch {
                Write-Warn "Could not fully provision $username : $_"
            }
        }
    }

    Write-Host ""
    Write-OK "Provisioned $PROVISIONED users"
    Write-Info "New users: add 'powershell -ExecutionPolicy Bypass -File `"$RAVEN_SYSTEM\install.ps1`"' to your onboarding script"
}

# ─── ADD RAVEN-SETUP TO SYSTEM PATH ──────────────────────────────────────────
Write-Host ""
Write-Info "Adding raven-setup.ps1 to system PATH ..."

$ravenBin = $RAVEN_SYSTEM

$currentMachinePath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
if ($currentMachinePath -notlike "*$ravenBin*") {
    $newPath = $currentMachinePath.TrimEnd(";") + ";" + $ravenBin
    [Environment]::SetEnvironmentVariable("PATH", $newPath, "Machine")
    Write-OK "Added $ravenBin to system PATH (Machine scope)"
    Write-Warn "Open a new terminal session for PATH changes to take effect."
} else {
    Write-OK "$ravenBin already in system PATH"
}

# ─── DONE ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Bold "================================================"
Write-Host "  [OK] Raven Enterprise deployed" -ForegroundColor Green
Write-Bold "================================================"
Write-Host ""
Write-Bold "  What's deployed:"
Write-Host "  * Raven installed at:    $RAVEN_SYSTEM" -ForegroundColor Cyan
Write-Host "  * MCP auto-loads from:   $MANAGED_DIR\managed-mcp.json" -ForegroundColor Cyan
Write-Host "  * Settings deployed to:  $MANAGED_DIR\managed-settings.json" -ForegroundColor Cyan
Write-Host "  * Org manifest at:       $ORG_MANIFEST_PATH" -ForegroundColor Cyan
Write-Host "  * raven-setup command:   $RAVEN_SYSTEM\raven-setup.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Bold "  Developer day 1 -- nothing to install:"
Write-Host "  cd MyProject" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File raven-setup.ps1" -ForegroundColor Cyan
Write-Host "  claude ." -ForegroundColor Cyan
Write-Host ""
Write-Bold "  Update Raven for all users:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$RAVEN_SYSTEM\install-enterprise.ps1`"" -ForegroundColor Cyan
Write-Host ""
Write-Bold "  For new users joining the org:"
Write-Host "  Add to your onboarding script:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$RAVEN_SYSTEM\install.ps1`"" -ForegroundColor Cyan
Write-Host ""
Write-Bold "  MDM / GPO silent re-deployment:"
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$RAVEN_SYSTEM\install-enterprise.ps1`" ``" -ForegroundColor Cyan
Write-Host "    -Silent -OrgName `"$MANIFEST_ORG_NAME`" -OrgEmail `"$MANIFEST_ORG_EMAIL`"" -ForegroundColor Cyan
Write-Host ""
