# Raven — Global Installer for Windows (PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
#        OR: iwr https://raw.githubusercontent.com/giggsoinc/raven/main/install.ps1 | iex
#
# What this does (one command, done forever):
#   1. Downloads Raven to $HOME\.raven\
#   2. Wires ALL 35 skills + 10 agents into Claude Code globally ($HOME\.claude\)
#   3. Registers the MCP server globally
#   4. Makes raven-setup available as a command
#
# After this: open Claude Code in ANY project and Raven is already there.
# Per-project: run raven-setup once to create the manifest.
#
# Requires: Git, Python 3.10+
# Claude Code: https://claude.ai/download

$ErrorActionPreference = "Stop"

function Write-Bold   { param($msg) Write-Host $msg -ForegroundColor White }
function Write-OK     { param($msg) Write-Host "  v $msg" -ForegroundColor Green }
function Write-Info   { param($msg) Write-Host "  $msg" -ForegroundColor Cyan }
function Write-Warn   { param($msg) Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Err    { param($msg) Write-Host "  X $msg" -ForegroundColor Red; exit 1 }

$RAVEN_DIR  = "$env:USERPROFILE\.raven"
$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$REPO       = "https://github.com/giggsoinc/raven.git"

Write-Host ""
Write-Bold "================================================"
Write-Bold "  Raven -- Global Install v2.9 (Windows)"
Write-Bold "  Guardrails before you ship."
Write-Bold "================================================"
Write-Host ""

# ─── REQUIREMENTS ────────────────────────────────────────────────────────────
try { $null = git --version 2>&1 } catch { Write-Err "git not found. Install from git-scm.com" }
try { $null = python --version 2>&1 } catch { Write-Err "python not found. Install from python.org (check 'Add to PATH')" }

$CLAUDE_FOUND = $true
try { $null = claude --version 2>&1 } catch {
    Write-Warn "Claude Code not found."
    Write-Host "    Install: https://claude.ai/download"
    Write-Host "    Raven will still install -- run this again after Claude Code is set up."
    $CLAUDE_FOUND = $false
}

# ─── DOWNLOAD / UPDATE ───────────────────────────────────────────────────────
if (Test-Path "$RAVEN_DIR\.git") {
    Write-Info "Updating existing Raven install..."
    git -C $RAVEN_DIR pull --quiet
    Write-OK "Updated to latest"
} else {
    Write-Info "Downloading Raven..."
    git clone --quiet --depth=1 $REPO $RAVEN_DIR
    Write-OK "Downloaded to $RAVEN_DIR"
}

# ─── WIRE INTO CLAUDE CODE GLOBALLY ─────────────────────────────────────────
Write-Host ""
Write-Info "Installing into Claude Code ($CLAUDE_DIR)..."

foreach ($d in @("skills","agents","commands","scripts")) {
    New-Item -ItemType Directory -Path "$CLAUDE_DIR\$d" -Force | Out-Null
}

# ── All 35 skills ──
$SKILLS_INSTALLED = 0
foreach ($skillDir in (Get-ChildItem "$RAVEN_DIR\core\skills" -Directory)) {
    $skillMd = Join-Path $skillDir.FullName "SKILL.md"
    if (Test-Path $skillMd) {
        $destDir = "$CLAUDE_DIR\skills\$($skillDir.Name)"
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        Copy-Item $skillMd $destDir -Force
        # Copy rules/ subdirectory if exists
        $rulesDir = Join-Path $skillDir.FullName "rules"
        if (Test-Path $rulesDir) {
            New-Item -ItemType Directory -Path "$destDir\rules" -Force | Out-Null
            Copy-Item "$rulesDir\*.md" "$destDir\rules\" -Force -ErrorAction SilentlyContinue
        }
        $SKILLS_INSTALLED++
    }
}
Write-OK "$SKILLS_INSTALLED skills installed"

# ── All 10 agents ──
$AGENTS_INSTALLED = 0
foreach ($agentMd in (Get-ChildItem "$RAVEN_DIR\core\agents\*.md")) {
    Copy-Item $agentMd.FullName "$CLAUDE_DIR\agents\" -Force
    $AGENTS_INSTALLED++
}
Write-OK "$AGENTS_INSTALLED agents installed"

# ── Commands ──
$CMDS_INSTALLED = 0
foreach ($cmdMd in (Get-ChildItem "$RAVEN_DIR\core\commands\*.md")) {
    Copy-Item $cmdMd.FullName "$CLAUDE_DIR\commands\" -Force
    $CMDS_INSTALLED++
}
Write-OK "$CMDS_INSTALLED commands installed"

# ── Scripts ──
foreach ($py in (Get-ChildItem "$RAVEN_DIR\raven-core\*.py" -ErrorAction SilentlyContinue)) {
    Copy-Item $py.FullName "$CLAUDE_DIR\scripts\" -Force
}
foreach ($py in (Get-ChildItem "$RAVEN_DIR\core\scripts\*.py" -ErrorAction SilentlyContinue)) {
    Copy-Item $py.FullName "$CLAUDE_DIR\scripts\" -Force
}
# Detection script used by raven-debug
$detectScript = "$RAVEN_DIR\setup\sr-detect-workmode.py"
if (Test-Path $detectScript) {
    Copy-Item $detectScript "$CLAUDE_DIR\scripts\" -Force
}
Write-OK "Scripts installed"

# ── CLAUDE.md — global Raven instructions ──
$globalClaude  = "$CLAUDE_DIR\CLAUDE.md"
$ravenClaude   = "$RAVEN_DIR\CLAUDE.md"
$ravenMarker   = "# RAVEN GLOBAL CONFIG"

if (Test-Path $globalClaude) {
    $existing = Get-Content $globalClaude -Raw
    $ravenContent = Get-Content $ravenClaude -Raw
    if ($existing -like "*$ravenMarker*") {
        # Update in place
        $idx = $existing.IndexOf($ravenMarker)
        $pre = $existing.Substring(0, $idx)
        Set-Content $globalClaude ($pre + $ravenMarker + "`n`n" + $ravenContent)
    } else {
        Add-Content $globalClaude ("`n`n$ravenMarker`n`n" + $ravenContent)
    }
} else {
    Set-Content $globalClaude ("$ravenMarker`n`n" + (Get-Content $ravenClaude -Raw))
}
Write-OK "$env:USERPROFILE\.claude\CLAUDE.md configured"

# ── MCP server — register globally ──
$mcpServer = "$RAVEN_DIR\mcp\server.py"
if (-not (Test-Path $mcpServer)) { $mcpServer = "$RAVEN_DIR\raven-core\server.py" }

if ((Test-Path $mcpServer) -and $CLAUDE_FOUND) {
    try {
        claude mcp add raven -- python $mcpServer 2>$null
        Write-OK "MCP server registered (raven_status, raven_cve_check, raven_debug...)"
    } catch {
        Write-Warn "MCP auto-register skipped. Run manually: claude mcp add raven -- python $mcpServer"
    }
} elseif (Test-Path $mcpServer) {
    Write-Warn "MCP server ready but Claude Code not installed."
    Write-Host "    After installing Claude Code, run:"
    Write-Host "    claude mcp add raven -- python $mcpServer"
}

# ── raven-setup shortcut — add to user PATH ──
$binDir = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Path $binDir -Force | Out-Null

$setupScript = @"
# Raven per-project setup shortcut
powershell -ExecutionPolicy Bypass -File "$RAVEN_DIR\raven-setup.ps1" `$args
"@
Set-Content "$binDir\raven-setup.ps1" $setupScript

# Add to PATH if not already there
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$userPath;$binDir", "User")
    Write-OK "Added $binDir to user PATH"
}

# ─── DONE ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Bold "================================================"
Write-OK "Raven installed globally"
Write-Bold "================================================"
Write-Host ""
Write-Host "  What's now available in every Claude Code session:"
Write-Host "  * 35 skills (Andie, all 23 specialists, raven-core...)"
Write-Host "  * 10 guard agents (always on)"
Write-Host "  * All commands (/raven-debug, /raven-review...)"
Write-Host "  * MCP tools (raven_status, raven_cve_check...)"
Write-Host ""
Write-Host "  Per-project setup (run once per project):"
Write-Host "    cd YourProject"
Write-Host "    powershell -ExecutionPolicy Bypass -File $RAVEN_DIR\raven-setup.ps1"
Write-Host ""
Write-Host "  Then open Claude Code:"
Write-Host "    claude ."
Write-Host ""
Write-Host "  To update Raven later:"
Write-Host "    iwr https://raw.githubusercontent.com/giggsoinc/raven/main/install.ps1 | iex"
Write-Host "    (re-running updates and re-wires everything)"
Write-Host ""

if (-not $CLAUDE_FOUND) {
    Write-Warn "Install Claude Code then re-run this script to register the MCP server."
    Write-Host "    https://claude.ai/download"
    Write-Host ""
}
