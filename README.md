# Raven Enterprise v3.1

**Raven Enterprise is a superset of [Raven](https://github.com/giggsoinc/raven).**

Everything in Raven — 56 domain skills, 12 guard agents, 9 always-on hooks, 11 raven-core engine scripts — plus an enterprise governance layer: MCP guard, model routing, org risk signals, and the Raven Hub control plane.

Enforces policy on every developer machine. Surfaces risk to leadership. No new login. No log system. Runs inside Claude Code.

---

## Performance

Token cost and developer orientation are first-class design constraints across all Raven products.

### RAVEN
- **Skills load on invocation only.** 56 domain skills stay out of context until a domain match fires — nothing pre-loaded.
- **Skill reminder fires once per session.** Domain enforcement prompt runs on the first message only (~10 tok), not on every message.

### RAVEN-ENTERPRISE
- **Skill footprint −57%.** Andie, db-router, ui-router, and agent-chaining collectively shrunk from ~22K tok to ~9.5K tok. Session context pressure drops ~53% in a typical Andie + specialist session.
- **Brownfield survey.** `/raven-init` on an existing project auto-scans the repo and emits a structured project card — entry points, auth layer, DB setup, open security issues, entity map — in ~10 seconds. Replaces 5 minutes of manual spelunking.
- **Model routing.** Auto-routes to the cheapest adequate model across Anthropic, OpenAI, Groq, Gemini, Ollama, and LM Studio. Cost opportunity surfaced on the Hub dashboard.
- **200-byte daily signal.** No raw events, no prompts, no code reaches the Hub.

### ANDIE v6.1
- **Multi-platform.** Same skill, same behaviour across Claude Code, OpenAI, Gemini, Perplexity, and Manus.
- **Compressed −69%.** 39K → 12K bytes. Smaller footprint on every invocation.
- **Plan-mode gate.** Forces a structured plan before any implementation. No drift into code without an approved plan.

### RAVEN-CODEX
- **MCP-native.** Runs inside Copilot, Codex, and any MCP-compatible editor — no Claude Code required.
- **Lightweight server.** Single `mcp/server.py` — no plugin install, no hooks, minimal surface area.

---

## Install

### Prerequisites

- [Claude Code](https://claude.ai/code) installed and authenticated
- Python 3.11+
- Git

---

### Developer Setup (every developer machine)

**Step 1 — Install the plugin**

```bash
# Download from GitHub Releases and install:
claude plugin install raven-enterprise-plugin-v3.1.0.zip
```

Get the ZIP from [github.com/giggsoinc/raven-enterprise/releases](https://github.com/giggsoinc/raven-enterprise/releases) or from your platform team.

**Step 2 — Open your repo in Claude Code**

```bash
cd your-repo
claude
```

Raven auto-boots on session open. You'll see:

```
Raven ✅  BROWNFIELD · Python · Odoo → raven:odoo-specialist · ollama
```

**Step 3 — Initialize Raven for the project** (first time only)

If no `.raven/manifest.json` exists, Raven will prompt you. Or run it manually:

```
/raven-init
```

This asks 5 questions and writes:
- `.raven/manifest.json` — project config
- `.claude/CLAUDE.md` — session boot instructions

Commit both:

```bash
git add .raven/manifest.json .claude/CLAUDE.md
git commit -m "chore: init raven-enterprise v3.1 [RAVEN:INIT]"
```

**Step 4 — Verify**

```
/raven-debug
```

---

### Alternative: CLI Hooks Only (no plugin)

For repos where you want hooks but not the Claude Code plugin:

```bash
bash agent/raven-init.sh --hub-url https://raven.your-org.com --org your-org
```

This wires git pre-commit hooks, secret scan, CVE check, and audit log. Does NOT install skills or guard agents (those require the plugin).

---

### Platform / IT Setup — Hub (one per org)

The Hub receives 200-byte daily summaries from all developer agents and surfaces org-level risk.

**Self-hosted:**

```bash
cd hub
cp .env.example .env        # set SMTP, webhook URL, auth config
docker compose up -d
```

Required env vars in `.env`:

```
HUB_SECRET_KEY=<random 32+ chars>
DATABASE_URL=postgresql://...
HUB_ALERT_WEBHOOK=https://hooks.slack.com/...   # optional
HUB_ALERT_EMAIL=security@your-org.com            # optional
```

**SaaS:** `hub.raven.giggso.com` — contact [giggso.com](https://giggso.com)

Once the Hub is running, point developer agents at it via `/raven-init` — it will ask for the Hub URL on first run.

---

## What's Included

### Everything from Raven v3.0

**56 Domain Skills** — andie v6.1 · andie-jr · andie-frames · db-router · ui-router · Oracle (6) · AWS · GCP · Azure · OCI · Kafka · Postgres · Redis · K8s · Terraform · FastAPI · Salesforce · Odoo · and more

**10 Guard Agents — Always On**

| Agent | Protects |
|---|---|
| `manifest-checker` | Verifies Raven is configured before any work starts |
| `stack-validator` | Catches wrong-stack libraries — warns during coding, hard blocks at commit |
| `style-enforcer` | Enforces code style — advises during coding, blocks at commit |
| `architecture-guard` | Ensures architectural decisions are documented |
| `db-guard` | Catches inline SQL, missing ERDs, broken migration numbering |
| `skill-guard` | Prevents skills from reading secrets or acting outside scope |
| `claude-mem` | Writes structured session memory to `.raven/memory/` |
| `guard-git-watch` | Hard blocks unexpected reads of `.env`, SSH keys, secrets |
| `odoo-guard` | Odoo-specific: hardcoded IDs, raw SQL in ORM, broken module structure |
| `salesforce-guard` | SF-specific: SOQL/DML inside loops, hardcoded IDs, missing bulk patterns |

**11 Always-On Hooks**

| Event | Hook | Type | What it does |
|---|---|---|---|
| `SessionStart` | `policy-sync.py` | Context | Pulls org policy from Hub, caches locally |
| `SessionStart` | `session-start.py` | Context | Brownfield/greenfield · domain skill · model routing · in-session metrics |
| `UserPromptSubmit` | `raven-skill-reminder.py` | Context | Per-prompt domain skill enforcement |
| `UserPromptSubmit` | `cve-prompt-guard.py` | Warn | Injects CVE reminder on install intent |
| `PreToolUse` any | `tool-guard.py` | **BLOCK** | Blocks restricted actions (rm -rf, sudo, etc.) |
| `PreToolUse` Bash | `schema-guard.py` | **BLOCK** | Stops DROP TABLE / TRUNCATE / DELETE without WHERE |
| `PreToolUse` mcp__* | `mcp-guard.py` | **BLOCK** | Enforces org MCP policy (shadow/soft/hard) |
| `PostToolUse` Write/Edit | `secret-scan.py` | Async warn | Scans every written file for secrets immediately |
| `PostToolUse` any | `audit-log.py` | Async | Encrypted audit trail → S3/GCS/Azure/OCI |
| `Stop` | `stream-signal.py` | Async | Session summary to developer + 200-byte signal to Hub |
| `Stop` | `obsidian-log.py` | Async | Three-layer session log → Obsidian vault |

**13 raven-core Engine Scripts**

`audit-log.py` · `approval-request.py` · `cve-check.py` · `cve-prompt-guard.py` · `db-guard.py` · `emit-violation.py` · `mcp-guard.py` · `obsidian-log.py` · `policy-sync.py` · `pr-gate.py` · `schema-guard.py` · `secret-scan.py` · `session-start.py` · `stream-signal.py`

---

### Enterprise-Only Layer

**MCP Governance**

Every MCP server use is tracked. Three enforcement modes:
- `shadow` — log only, no prompts
- `soft` — first-use prompt (Always / Session / Never), continue automatically
- `hard` — explicit approval required per use

**Model Routing**

Auto-discovers available models (Anthropic, OpenAI, Groq, Gemini, Ollama, LM Studio). Routes tasks to the cheapest adequate model. Writes `.model.env` routing table locally.

```bash
python3 agent/scripts/model-discover.py   # run manually to refresh
```

**Signal Streaming**

200-byte daily summary posted to Hub. Queued locally if Hub unreachable. No prompts, no raw events, no PII.

**Hub — Five numbers. One screen.**

- Org Risk Score (0–100, trend, reason)
- Ungoverned MCPs (count + dev count)
- Policy compliance (% of sessions fully governed)
- Secrets blocked (any = investigate)
- Cost opportunity ($/month savings from model routing)

---

## Architecture

```
Developer's Claude Code
┌──────────────────────────────────────────────────────┐
│  SessionStart      → policy-sync.py  (Hub → cache)  │
│                    → session-start.py                │
│                      (brownfield/greenfield · domain │
│                       skill · model routing · banner)│
│  UserPromptSubmit  → raven-skill-reminder.py         │
│                    → cve-prompt-guard.py             │
│  PreToolUse        → tool-guard.py + schema-guard.py │
│                    → mcp-guard.py  (shadow/soft/hard)│
│  PostToolUse       → secret-scan.py + audit-log.py  │
│  PreCompact        → token-guard.py (backup + alert) │
│  Stop              → stream-signal.py → dev summary  │
│                    → obsidian-log.py → ~/RavenVault/ │
│                                                      │
│  10 guard agents (always-on, silent)                 │
│  56 domain skills (load on domain match)             │
└─────────────────────┬────────────────────────────────┘
                      │ HTTPS POST (200 bytes/day)
                      ▼
        RAVEN HUB (FastAPI + Postgres)
        Posture · Devs · Deployment · Shadow · Approvals
                      │
                      │ MCP (raven-hub)
                      ▼
        Admin's Claude Code — queries Hub inline
        No dashboard login required
```

## Signal Schema (one per developer per day)

```json
{
  "date", "user", "org", "project",
  "sessions", "commits",
  "secrets_blocked", "cve_blocked",
  "mcp_ungoverned", "mcp_override", "policy_mode",
  "model_cost_usd", "model_optimal_usd",
  "lines_generated", "lines_accepted",
  "tokens_estimated",
  "raven_version", "plugin_type"
}
```

No prompts. No raw events. No PII.

---

## Hub API

| Endpoint | What it returns |
|---|---|
| `GET /api/v1/posture?org=X` | 5-number risk screen |
| `GET /api/v1/posture/detail?org=X` | Per-project breakdown |
| `GET /api/v1/devs?org=X` | Per-developer cost, tokens, MCPs, compliance |
| `GET /api/v1/deployment?org=X` | Who has Raven installed + which version |
| `GET /api/v1/shadow?org=X` | Ungoverned MCP report + candidate allow list |
| `GET /api/v1/approvals?org=X` | Pending developer approval requests |
| `POST /api/v1/approvals/{id}/approve` | Approve request (auto-updates policy for MCPs) |
| `POST /api/v1/approvals/{id}/deny` | Deny request |
| `POST /api/v1/shadow/promote?org=X&mcp_name=Y` | Promote ungoverned MCP to allow list |
| `GET /api/v1/policy?org=X` | Current MCP policy |
| `POST /api/v1/policy?org=X` | Update + push to agents |
| `GET /api/v1/export/summary?org=X` | Compliance JSON |
| `GET /api/v1/export/csv?org=X` | Compliance CSV |
| `GET /api/v1/alerts?org=X` | Active alerts |
| `POST /api/v1/alerts/{id}/resolve` | Resolve alert |

## Alert Thresholds

| Trigger | Severity | Default |
|---|---|---|
| Risk score ≥ 60 | P2 | Configurable |
| Any secret blocked | P1 | Immediate |
| Any CVE blocked | P1 | Immediate |
| Unregistered MCP across ≥ 5 devs | P2 | Configurable |
| Model waste ≥ 50% | P3 | Configurable |

Notifications: `HUB_ALERT_WEBHOOK` (Slack/Teams) + `HUB_ALERT_EMAIL` (SMTP/SES)

---

## What is NOT stored

- Raw events
- Prompts (any length)
- Code content
- Credentials

---

## Companion Repos

| Repo | Purpose |
|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) | Open-source base — install for individual devs and teams |
| [giggsoinc/raven-enterprise](https://github.com/giggsoinc/raven-enterprise) | This repo — superset with Hub, MCP guard, model routing |
| [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex) | Codex / Copilot / multi-platform variant (MCP-based) |
| [giggsoinc/andie](https://github.com/giggsoinc/andie) | Andie v5.2 standalone — works on ChatGPT, Gemini, Manus too |

---

## Raven Hub MCP Tool

Admin queries the Hub from inside any Claude Code session — no dashboard to log into.

**Setup in `.mcp.json`:**

```json
{
  "mcpServers": {
    "raven-hub": {
      "command": "python3",
      "args": ["/path/to/raven-enterprise/hub/mcp_server.py"],
      "env": {
        "RAVEN_HUB_URL": "https://raven.your-org.com",
        "RAVEN_ORG": "your-org"
      }
    }
  }
}
```

**Available tools:**

| Tool | What it does |
|---|---|
| `raven_posture` | Org risk screen — 5 numbers |
| `raven_devs` | Per-developer breakdown (cost, tokens, MCPs) |
| `raven_deployment` | Who has Raven installed, which version |
| `raven_shadow` | Ungoverned MCP report |
| `raven_approvals` | Pending developer approval queue |
| `raven_approve` / `raven_deny` | Review approval requests |
| `raven_set_policy` | Switch enforcement mode (shadow/soft/hard) |
| `raven_promote_mcp` | Add ungoverned MCP to allow list |
| `raven_alerts` / `raven_resolve_alert` | Manage active alerts |

Example from Claude Code: *"Show me which developers have ungoverned MCPs this week"* → Claude calls `raven_shadow` + `raven_devs` and displays inline.

---

Commercial · Built by [Giggso](https://giggso.com) · Enterprise: [giggso.com/raven-enterprise](https://giggso.com/raven-enterprise)
