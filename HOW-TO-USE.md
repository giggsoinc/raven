<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# How to Use Raven — v2.9

> Claude Code · GitHub Copilot · OpenAI Codex · MIT License · [Giggso](https://giggso.com)

---

## Choose Your Path

<table>
<thead>
<tr>
<th>Who are you?</th>
<th>OS</th>
<th>Jump to</th>
</tr>
</thead>
<tbody>
<tr>
<td rowspan="2">
  <b>Individual developer</b><br>
  <sub>Installing for yourself on your own machine</sub>
</td>
<td>macOS or Linux</td>
<td><a href="#dev-mac-linux">→ Dev Install — macOS & Linux</a></td>
</tr>
<tr>
<td>Windows</td>
<td><a href="#dev-windows">→ Dev Install — Windows</a></td>
</tr>
<tr>
<td rowspan="2">
  <b>IT admin / architect</b><br>
  <sub>Deploying for your whole team, zero dev action needed</sub>
</td>
<td>macOS or Linux</td>
<td><a href="#enterprise-mac-linux">→ Enterprise — macOS & Linux</a></td>
</tr>
<tr>
<td>Windows</td>
<td><a href="#enterprise-windows">→ Enterprise — Windows</a></td>
</tr>
<tr>
<td>
  <b>Codex / GitHub Copilot user</b><br>
  <sub>No terminal, no install script — plugin only</sub>
</td>
<td>Any</td>
<td><a href="#codex-copilot">→ Codex & Copilot Plugin</a></td>
</tr>
</tbody>
</table>

---

<a id="dev-mac-linux"></a>

## Dev Install — macOS & Linux

### What you need first

| | Check |
|---|---|
| Claude Code | `claude --version` — [download](https://claude.ai/download) if missing |
| Git | `git --version` |
| Python 3.10+ | `python3 --version` |

### Step 1 — Install Raven globally (one command, one time per machine)

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash
```

**What this does:**
- Downloads Raven to `~/.raven/`
- Copies all 35 skills + 10 agents into `~/.claude/` — available in every Claude Code session from now on
- Registers the MCP server globally
- Makes `raven-setup` available as a command anywhere

**Manual install (no curl):**
```bash
git clone https://github.com/giggsoinc/raven.git ~/.raven
bash ~/.raven/install.sh
```

### Step 2 — Per-project setup (one time per project)

```bash
cd YourProject
raven-setup
```

Raven scans the directory silently, shows what it found, and asks **one question**. Done in under 2 minutes.

**Example — Terraform project:**
```
─────────────────────────────────────────────────
  RAVEN — first run
─────────────────────────────────────────────────
  Scanned this directory. Here's what I see:

    Terraform configs      ✓  (14 files)
    Helm charts            ✓
    Docker Compose         ✓
    Platform               macOS (auto-detected)
    No source code         —

  This looks like a pure infrastructure workspace.
  Code linting rules will not apply.

  What's the main thing you want enforced?
    1) No undocumented infrastructure changes
    2) Secrets never in config files
    3) Consistent naming conventions
    4) All of the above (recommended)

  → 4
─────────────────────────────────────────────────
```

Two more questions follow (project name, email), then the manifest is created.

### Step 3 — Open Claude Code

```bash
claude .
```

Raven greets you immediately — no blank screen, no setup needed.

### Step 4 — Update later

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash
```

Re-running install updates Raven and re-wires `~/.claude/`. Project manifests are untouched.

---

<a id="dev-windows"></a>

## Dev Install — Windows

### What you need first

| | How to install |
|---|---|
| Python 3.10+ | [python.org](https://python.org) — **check "Add to PATH"** during install |
| Git | [git-scm.com](https://git-scm.com) |
| Claude Code | `winget install Anthropic.Claude` or [claude.ai/download](https://claude.ai/download) |

> All commands below run in **PowerShell**. Not Command Prompt.

### Step 1 — Install Raven globally (one command, one time per machine)

```powershell
iwr https://raw.githubusercontent.com/giggsoinc/raven/main/install.ps1 | iex
```

**What this does:**
- Downloads Raven to `$env:USERPROFILE\.raven\`
- Copies all 35 skills + 10 agents into `$env:USERPROFILE\.claude\`
- Registers the MCP server globally
- Makes `raven-setup.ps1` available

**Manual install (no iwr):**
```powershell
git clone https://github.com/giggsoinc/raven.git $env:USERPROFILE\.raven
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\.raven\install.ps1
```

### Step 2 — Per-project setup (one time per project)

```powershell
cd YourProject
raven-setup.ps1
```

Same detection and 1-question flow as macOS/Linux. Works natively — no WSL needed.

### Step 3 — Open Claude Code

```powershell
claude .
```

### Execution policy note

If PowerShell blocks the script:
```powershell
powershell -ExecutionPolicy Bypass -File $env:USERPROFILE\.raven\install.ps1
```

---

<a id="enterprise-mac-linux"></a>

## Enterprise — macOS & Linux

> **For IT admins and architects deploying to a team.**
> Run this once on each managed machine. Developers need zero installation steps.

### What this deploys

| Component | Where | Effect |
|---|---|---|
| Raven source | `/usr/local/raven/` | System-wide, all users |
| `managed-mcp.json` | `/Library/Application Support/ClaudeCode/` (mac) or `/etc/claude-code/` (linux) | Every Claude Code session auto-loads Raven MCP tools |
| `managed-settings.json` | Same managed path | Hooks and permission policy enforced for all users |
| `manifest.org.json` | `/usr/local/raven/` | Org-level locked rules — devs cannot override |
| All 35 skills + agents | Each user's `~/.claude/` | Provisioned at install time (optional) |
| `raven-setup` command | `/usr/local/bin/` | Available system-wide |

### Run the enterprise installer

```bash
sudo bash install-enterprise.sh
```

The script asks 4 questions:
1. Organisation name
2. IT / architect email (audit trail)
3. Approval mode — `first_responder` / `majority_vote` / `owner_only`
4. Token control — `per_developer` / `per_project` / `per_team`

Then it asks: **"Provision all existing users now?"**
- Say yes → all current users on the machine get skills in `~/.claude/` immediately
- Say no → users run `install.sh` themselves on first login (add to onboarding script)

### Developer experience after enterprise deploy

Developer opens a new machine. No install steps. No README to read. They just:

```bash
cd MyProject
raven-setup        # 2-minute project manifest setup
claude .           # Raven greets them immediately
```

If IT provisioned `~/.claude/` for them, even `raven-setup` may be skipped if the project already has a manifest checked into git.

### Org manifest — locked fields

`/usr/local/raven/manifest.org.json` locks fields every project manifest must comply with. Example:

```json
{
  "_layer": "org",
  "_locked": ["standards", "approval_mode", "guard.enabled", "tokens.control"],
  "standards": "raven-v2.9",
  "approval_mode": "majority_vote",
  "guard": { "enabled": true },
  "tokens": { "control": "per_developer" }
}
```

Developers can't change these. Their project manifest inherits them.

### For new hires

Add to your onboarding provisioning script:

```bash
sudo bash /usr/local/raven/install.sh
# installs and wires ~/.claude/ for the new user
```

### Update all users

```bash
sudo bash /usr/local/raven/install-enterprise.sh
# pulls latest, regenerates managed files, re-provisions all users
```

---

<a id="enterprise-windows"></a>

## Enterprise — Windows

> Windows enterprise script (`install-enterprise.ps1`) is in progress.
> Current workaround below covers the same outcome manually.

### Managed MCP — deploy to all users now

1. Clone Raven to a shared location (e.g. `C:\Program Files\Raven\`):

```powershell
git clone https://github.com/giggsoinc/raven.git "C:\Program Files\Raven"
```

2. Create `managed-mcp.json` and drop it at the system Claude Code path:

```powershell
$managedDir = "C:\ProgramData\ClaudeCode"
New-Item -ItemType Directory -Path $managedDir -Force | Out-Null

@{
  mcpServers = @{
    raven = @{
      type    = "stdio"
      command = "python"
      args    = @("C:\Program Files\Raven\mcp\server.py")
    }
  }
} | ConvertTo-Json -Depth 5 | Set-Content "$managedDir\managed-mcp.json"
```

Every Claude Code session on this machine now auto-loads Raven MCP tools.

3. Provision skills for each developer via MDM/GPO login script:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Program Files\Raven\install.ps1"
```

### Org manifest

Create `C:\Program Files\Raven\manifest.org.json` with your locked org fields (same JSON structure as the macOS/Linux version above).

### Developer experience

Same as macOS/Linux enterprise — developer opens Claude Code, Raven is already there.

---

<a id="codex-copilot"></a>

## Codex & Copilot Plugin

> No terminal. No install script. Plugin install only.
> Works with OpenAI Codex and GitHub Copilot (any OS, any machine).

### Install

1. Go to [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex)
2. Install the plugin in your Codex or Copilot interface
3. That's it — all 49 skills load automatically

### What's different from Claude Code

| Feature | Claude Code | Codex / Copilot |
|---|---|---|
| All 35 skills | ✅ | ✅ (49 in plugin) |
| Andie orchestration | ✅ | ✅ — mandatory first step |
| Pre-commit hook | ✅ | ❌ — no hook system |
| Secret detection at save | ✅ | Conversational only |
| CVE hard block | ✅ | Warn only |
| MCP tools | ✅ | ❌ |
| Audit log | ✅ | ❌ — no persistence |
| Manifest | Per project | Per session |

### How sessions work

Every session starts with Andie automatically — this is enforced via `AGENTS.md` and the plugin's `systemPrompt`:

```
Step 1: Andie loads
Step 2: Andie runs PRE-FLIGHT (detects context, recommends framework, assembles team)
Step 3: Andie routes to the right specialist
Step 4: Work begins
```

You never interact with a specialist directly. Andie picks it based on what you're working on.

### Manifest in Codex

Codex doesn't have a file system hook for manifest creation. If your project has `.raven/manifest.json` checked into git, Andie reads it. If not, Andie runs a lightweight inline setup (3 questions) at the start of the first session.

---

## After Any Install — What To Expect

When you open Claude Code in a project for the first time after installing:

**Project has a manifest:**
```
─────────────────────────────────────────────────
  Raven ✅  |  MyProject  |  infra
─────────────────────────────────────────────────
  I'm Andie — your AI discipline layer.
  Guards active. 35 skills loaded.

  What are you working on today?

  Try:
  • "Review my changes before I commit"
  • "I'm adding a new feature — help me plan it"
  • "Scan this file for security issues"
  • /raven-debug  to run a full diagnostic
─────────────────────────────────────────────────
```

**No manifest yet:**
```
─────────────────────────────────────────────────
  Raven — not set up yet for this project
─────────────────────────────────────────────────
  I scanned this directory. Here's what I see:

    Terraform configs    ✓  (14 files)
    Helm charts          ✓

  Want me to set it up? It takes 2 minutes.
    1) Yes — set up Raven now
    2) No  — just help me with my work anyway
    3) What exactly does Raven do here?
─────────────────────────────────────────────────
```

---

## Setup Questions — What Gets Asked

Raven asks the **minimum questions needed** based on what it detected in your directory.

| Work type detected | Language question | DB questions | Other |
|---|---|---|---|
| `code` | Full language list | Yes | Cloud |
| `infra` | yaml / hcl / dockerfile | Yes | Cloud |
| `data` | sql / python / yaml | Yes | Cloud |
| `salesforce` | Auto-set (apex + xml) | Skipped | Cloud |
| `odoo` | Auto-set (python + xml) | Yes | Cloud |
| `docs` | Auto-set (markdown) | Skipped | Skipped |
| `review` | Skipped entirely | Skipped | Skipped |
| `mixed` | Full list | Yes | Cloud |

Maximum questions across any flow: **5** (project name, email, cloud, language, notification email).
Typical: **3**.

---

## What Gets Created

```
YourProject/
├── CLAUDE.md                          ← Raven boot instructions for Claude Code
├── .raven/
│   ├── manifest.json                  ← Your project config (commit this)
│   ├── manifest.secrets.json          ← Secrets (NEVER commit)
│   ├── architecture.md               ← Living diagram template
│   └── ci/                           ← github-actions.yml / gitlab-ci.yml
├── .claude/
│   ├── settings.json                  ← Hooks: PreToolUse, PostEdit, PreCommit
│   ├── agents/                        ← 10 guard agents
│   ├── skills/                        ← 35 skills
│   ├── commands/                      ← Slash commands
│   └── scripts/                       ← cve-check.py secret-scan.py audit-log.py
└── .git/hooks/pre-commit              ← 5-check gate before every commit
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Claude Code blank screen after install | Re-run `install.sh` / `install.ps1` — rewires `~/.claude/` |
| `raven-setup` command not found | Run `source ~/.zshrc` or restart terminal |
| Stack validator blocks `.tf` / `.yaml` files | Set `work_type: infra` in manifest, or re-run `raven-setup` |
| Pre-commit not firing | `chmod +x .git/hooks/pre-commit` |
| CVE check skipped | Add `openai_api_key` to `.raven/manifest.secrets.json` |
| Agents not loading | Check `.claude/agents/` — each file needs valid YAML frontmatter |
| Enterprise: MCP not auto-loading | Verify `managed-mcp.json` is at the correct system path for your OS |
| Windows: `python3` not found | Windows uses `python` — `install.ps1` handles this automatically |
| Windows: execution policy error | `powershell -ExecutionPolicy Bypass -File install.ps1` |
| Codex: Andie not firing first | Check `AGENTS.md` is present and `systemPrompt` is set in `.codex-plugin/plugin.json` |

---

## File Reference

| File | Commit? | Who manages |
|---|---|---|
| `CLAUDE.md` | ✅ | Architects |
| `.raven/manifest.json` | ✅ | Architects / raven-setup |
| `.raven/architecture.md` | ✅ | Dev lead |
| `.raven/manifest.secrets.json` | ❌ Never | Architects only |
| `.claude/agents/` | ✅ | Architects |
| `.claude/skills/` | ✅ | Architects |
| `.claude/settings.json` | ✅ | Architects |
| `.git/hooks/pre-commit` | ❌ Local only | raven-setup installs |

---

*Raven v2.9 — MIT — [github.com/giggsoinc/raven](https://github.com/giggsoinc/raven)*
