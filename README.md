<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

<h1 align="center">Raven v3.0</h1>

<p align="center">
  <strong>AI-native engineering discipline for Claude Code · GitHub Copilot · OpenAI Codex</strong><br/>
  46 domain skills · 10 always-on guard agents · 8 always-on hooks · CVE scanning · secret detection · audit logs<br/>
  Works for individual developers, entire engineering teams, and enterprise IT rollouts
</p>

<p align="center">
  <a href="https://github.com/giggsoinc/raven/releases/tag/v3.0">v3.0</a> ·
  <a href="HOW-TO-USE.md">Full Documentation</a> ·
  MIT License ·
  Built by <a href="https://giggso.com">Giggso</a>
</p>

---

## The Problem Raven Solves

AI coding assistants are powerful — but left unchecked, they ship secrets in commits, add CVE-laden libraries, skip tests, ignore your stack conventions, and produce code that the next developer can't follow.

**Raven is the discipline layer between your AI assistant and your codebase.** It doesn't slow you down. It makes sure what ships is actually good.

---

## What Raven Does

### 🧠 Andie — Your AI Architect (v5.2)

Every session starts with **Andie**, Raven's orchestration layer. Andie isn't a chatbot — it's a structured expert system that:

- **Detects your domain automatically** — Oracle ERP, Salesforce, AWS GenAI, Agentic AI, SAP, Kubernetes, Data Engineering, Security, and more
- **Loads a Specialist Triad for that domain** — every problem gets three experts: 🏢 Functional (business/process) · ⚙️ Technical (implementation/code) · 📊 Data (flows/schema/pipelines). Each one surfaces their domain's corner cases
- **Generates domain-specific questions** — not generic prompts. An Oracle O2C engagement gets O2C questions. An AWS ML project gets ML questions. Shown to you before asking, adjustable, one at a time
- **Proposes before proceeding** — every tech recommendation, framework pick, and team suggestion is a PROPOSAL (accept / modify / reject). Nothing proceeds without your explicit confirmation. This is HITL as a first-class design principle, not an afterthought
- **Runs OODA continuously** — Observe / Orient / Decide / Act fires after every round in every mode. When orientation shifts the picture, a PROPOSAL is issued before anything changes direction
- **Picks the right thinking mode** — Deep (expert explanation), Kaizen (improvement cycles), War (crisis triage), Drama (multi-stakeholder debate). Shows you what each mode would produce *for your specific problem* before you commit to one

### 🛡️ 10 Guard Agents — Always On

Guard agents run silently in the background. They don't interrupt typing. They fire at the right moments — before a commit, after a file save, before a tool executes.

| Guard Agent | What it protects |
|---|---|
| **manifest-checker** | Verifies Raven is properly configured before any work starts |
| **stack-validator** | Catches wrong-stack libraries before they get merged. Warns during coding, hard blocks at commit |
| **style-enforcer** | Enforces your team's code style. Advises during coding, blocks at commit |
| **architecture-guard** | Ensures architecture decisions are documented. No diagram = warn now, block in 24h |
| **db-guard** | Catches inline SQL in non-SQL files, missing ERDs, broken migration numbering |
| **skill-guard** | Prevents skills from reading secrets, modifying settings, or acting outside their scope |
| **claude-mem** | Writes structured session memory to `.raven/memory/`. Surfaces open questions at next session start |
| **guard-git-watch** | Hard blocks any unexpected read of `.env`, SSH keys, or secrets files |
| **odoo-guard** | Odoo-specific: catches hardcoded DB IDs, raw SQL in ORM context, broken module structure |
| **salesforce-guard** | Salesforce-specific: catches SOQL/DML inside loops, missing bulk patterns, hardcoded IDs |

### 🔒 Commit-Time Gates

Before any `git commit` lands, Raven runs a full gate:

- **Secret scan** — checks every staged file for API keys, tokens, passwords, private keys. Hard blocks if found. No exceptions.
- **CVE scan** — checks every library you've added against known vulnerabilities. CVSS > 7 = hard block. Unknown libraries go through an approval flow.
- **Style check** — enforces your configured style rules across changed files
- **Architecture check** — ensures any significant changes are reflected in architecture docs

```
Secrets in staged files    → hard block commit
CVE critical (CVSS >7)     → hard block commit
Force push to main         → hard block
>100 rows deleted          → approval flow required
Schema drop detected       → hard block + escalate
Port 0.0.0.0 opened        → hard block + escalate
```

### 📦 46 Domain Skills

Skills activate only when your work matches their domain — ~100 tokens each, never loaded all at once.

**Orchestration**
> `andie` — multi-modal architect (Deep · Kaizen · War · Drama)
> `andie-jr` — fast-burn debug assistant for brownfield + bug fixes (2 rounds, 150 words max, Obsidian-aware)

**Database Thin Router** *(auto-detects DB type, loads one specialist)*
> `db-router` — Postgres/pgvector · MySQL/MariaDB · MongoDB · Qdrant · Databricks · Snowflake

**Frontend & Design Thin Router** *(auto-detects framework, design tool default: claude-design/stitch)*
> `ui-router` — React/Next.js · Vue/Nuxt · Angular · Vanilla JS · UI/UX Design

**Cloud Platforms**
> `aws` · `gcp` · `azure` · `oci`

**Data & Streaming**
> `kafka` · `postgres` · `redis` · `bigdata` · `dataeng` · `vector-db`

**Infrastructure & DevOps**
> `k8s` · `terraform` · `devops` · `vault`

**Frameworks & APIs**
> `fastapi` · `nicegui`

**AI & ML**
> `aiml` · `dynamic` (on-demand expert for any unknown domain)

**Enterprise Platforms**
> `odoo` · `salesforce`

**Oracle**
> `oracle-apex` · `oracle-apexlang` · `oracle-db` · `oracle-fusion` · `oracle-graal` · `oracle-oci`

**Engineering Practice**
> `raven-core` · `raven-plan` · `raven-review` · `raven-refactor` · `raven-test` · `raven-security` · `raven-document` · `raven-expert`

**Tooling**
> `security` · `log-management` · `agent-chaining` · `tools-landscape` · `task-observer`

### 🪝 8 Always-On Hooks — Fire Without Being Asked

Unlike skills (which activate on domain match), hooks fire automatically at specific lifecycle events. You cannot forget to run them.

| Event | Hook | Type | What it does |
|---|---|---|---|
| `SessionStart` | `session-start.py` | Context | Detects brownfield/greenfield · discovers available models · writes `.model.env` if missing |
| `PreToolUse` any tool | `tool-guard.py` | **BLOCK** | Blocks restricted actions (rm -rf, sudo, etc.) |
| `PreToolUse` Bash | `schema-guard.py` | **BLOCK** | Stops DROP TABLE / TRUNCATE / DELETE without WHERE before execution |
| `UserPromptSubmit` | `cve-prompt-guard.py` | Warn | Detects install intent (`pip install`, `npm install`, etc.) — injects CVE reminder before Claude responds |
| `PostToolUse` Write/Edit | `secret-scan.py` | Async warn | Scans every written file for secrets immediately — not just at commit |
| `PostToolUse` any tool | `audit-log.py` | Async | Encrypted audit entry for every tool use |
| `PreCompact` | `token-guard.py` | Warn | Token budget warnings at 25/50/75/90% |
| `Stop` | `session-gate.py` | Async | Git status + recent commits + open observations at session end |

**INTEGRITY hooks** (BLOCK type) fire before execution and stop dangerous actions.
**CONTEXT hooks** (Warn/Async) inform without blocking — so they never kill adoption.

### 🔄 Version Check — Every Session

Raven checks its own version against the latest release every time a session opens:

- **Up to date** → silent, no interruption
- **1–2 releases behind** → version banner in session opener: "Update available — say 'update raven' to sync"
- **3+ releases behind** → **auto-syncs automatically**, no action needed. You see a banner and it's done.

This means teams on shared codebases never silently drift onto old versions.

---

## Who It's For

**Individual developers** — install once, works across all your projects. Raven detects the project type and loads the right skills automatically. No per-project configuration required.

**Engineering teams** — shared manifest in the repo means every developer on the team has the same guards, the same skills, the same commit gates. Consistent quality without a style guide nobody reads.

**Tech leads and architects** — architecture-guard ensures decisions are documented. HITL gates in Andie mean recommendations are proposals, not auto-actions. The session memory in `.raven/memory/` gives you an audit trail of what was decided and why.

**Enterprise IT and DevOps** — silent MDM install on macOS (Jamf, Ansible), Windows (Intune, GPO, SCCM). Managed MCP config pushed org-wide. New hire workstations provisioned automatically.

**CISOs and security teams** — CVE scanning on every library addition, secret detection on every commit, escalation paths for critical violations, audit logs for every action Raven takes.

---

## Specialist Triads — How Andie Handles Any Domain

For each domain, Andie loads three specialists instead of one generalist. This surfaces blind spots that a single expert would miss.

| Domain | 🏢 Functional | ⚙️ Technical | 📊 Data |
|---|---|---|---|
| Oracle ERP Fusion (O2C/P2P/R2R) | Functional Consultant — process, compliance, org rules | Fusion Dev — FBDI, BIP, REST, OIC integrations | Data Specialist — OTBI, FRS, ADW, lineage |
| Salesforce | Domain Expert / BA — process, GTM, revenue ops | Dev — LWC, APEX, Flow, Platform Events | Agentforce + Data Cloud Architect |
| AWS GenAI / ML | Use Case Strategist — product, ROI, adoption | GenAI Engineer — Bedrock, SageMaker, Agents | Data Engineer — Glue, Athena, Lake Formation |
| Agentic AI / MoE / GraphRAG | AI Product Strategist — agent design, use cases | AI Engineer — LangGraph, CrewAI, A2A, MoE routing | AI Data Engineer — vector DBs, graph, ontology |
| SAP S/4HANA | Functional Consultant — FI/CO/MM/SD | ABAP / BTP / CAP Developer | BW / Analytics Cloud / Datasphere |
| Data Engineering | Data Product Owner — requirements, SLAs | Pipeline Engineer — streaming, orchestration | Data Architect — schema, lineage, governance |
| Security | CISO Advisor — threats, compliance, posture | Security Engineer — AppSec, CloudSec, SIEM | Security Analyst — logs, threat intel |
| Kubernetes / DevOps | Platform Product Owner | SRE Engineer — k8s, CI/CD, GitOps | Observability Specialist — metrics, tracing |
| Odoo ERP | Functional Consultant — modules, flows | Developer — Python, OWL, XML | Reporting / BI / OCA Specialist |

Unknown or mixed domains trigger `dynamic-specialist` — a 9-step on-demand expert construction with confidence assessment (HIGH / MEDIUM / VERIFY), live search when VERIFY, and profile caching after first use.

---

## Install

### Quickest — Plugin (no terminal needed)

1. Download [`raven-plugin-v3.0.0.zip`](plugin/raven-plugin-v3.0.0.zip)
2. Open Claude Desktop → Settings → Extensions → Add plugin
3. Upload the ZIP
4. Done — 41 skills and 10 guard agents load automatically

### Individual Developer

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash
```

**Windows:**
```powershell
iwr https://raw.githubusercontent.com/giggsoinc/raven/main/install.ps1 | iex
```

### Enterprise (IT / Admin)

**macOS / Linux — interactive or MDM (Jamf, Ansible):**
```bash
# Interactive
sudo bash install-enterprise.sh

# Silent for MDM
sudo bash install-enterprise.sh --silent --org "AcmeCorp" --email "it@acme.com"
```

**Windows — interactive or MDM (Intune, GPO, SCCM):**
```powershell
# Interactive
.\install-enterprise.ps1

# Silent for MDM / Intune
.\install-enterprise.ps1 -Silent -OrgName "AcmeCorp" -OrgEmail "it@acme.com"
```

[→ Full enterprise guide](HOW-TO-USE.md#enterprise-mac-linux)

---

## How It Feels in Practice

**You're adding a new AWS Lambda function:**
Raven detects AWS. `aws-specialist` loads. When you `import requests`, the CVE check runs. At commit, secret scan checks your staged files. Style enforcer validates naming. Architecture guard checks if this is a significant new component that needs a decision record.

**You ask Andie to help design a Salesforce order management flow:**
Andie detects Salesforce domain. Loads: SF Domain Expert + SF Dev (LWC/APEX/Flow) + SF Agentforce + Data Cloud Architect. Generates 8 Salesforce-specific questions. Shows them to you before asking. After your answers, proposes the architecture as a PROPOSAL — you accept, modify, or push back before anything is designed. OODA runs after each round and flags if the approach needs to shift.

**A CVE is found in a library you just added:**
Pre-commit hook fires. CVSS score shown. If > 7, commit hard-blocked. You see the alternative. If it's a known false positive or approved dependency, the approval flow is triggered with one command: `git commit -m "feat: X [GUARD:ALLOW-CVE]"`.

**It's 2am and production is down:**
You open Claude Code. Andie detects "production down" signal. War mode fires. No framework discussion, no diagram selection. Triage block in 10 seconds. OODA at T+0 gives you the first action. Incident log builds automatically. One command transitions to Kaizen when you're stable.

---

## Companion Repos

| Repo | For | Does |
|---|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) | Claude Code · Codex · Copilot | This repo — full install, plugin ZIP, all skills |
| [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex) | Codex / Copilot users | Plugin-only version |
| [giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) | DevOps / architects | Production-grade guard layer |
| [giggsoinc/andie](https://github.com/giggsoinc/andie) | All AI platforms | Andie v5.2 standalone — works on ChatGPT, Gemini, Manus, Perplexity too |

---

## License

MIT — [Giggso](https://giggso.com)

[HOW-TO-USE.md](HOW-TO-USE.md) · [CLAUDE.md](CLAUDE.md) · [plugin/README.md](plugin/README.md)
