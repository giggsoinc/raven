<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

<h1 align="center">Raven-Codex v3.0</h1>

<p align="center">
  <strong>AI-native engineering discipline for OpenAI Codex · GitHub Copilot · Claude Code</strong><br/>
  55 domain skills · 10 always-on guard agents · CVE scanning · secret detection · audit logs<br/>
  Andie v5.2 — specialist triads · HITL gates · continuous OODA · domain-adaptive questions
</p>

<p align="center">
  <a href="https://github.com/giggsoinc/raven">Raven Core</a> ·
  <a href="HOW-TO-USE.md">Full Documentation</a> ·
  MIT License ·
  Built by <a href="https://giggso.com">Giggso</a>
</p>

---

## What Is Raven-Codex?

Raven-Codex is the OpenAI Codex / GitHub Copilot implementation of the [Raven discipline engine](https://github.com/giggsoinc/raven). It enforces the same guardrails — CVE scanning, secret detection, commit gates, guard agents — adapted for the Codex/Copilot execution model (PR gates + pre-task hooks instead of pre-commit hooks).

Same engine. Same skills. Same Andie v5.2. Different delivery layer.

---

## The Problem It Solves

AI coding assistants are powerful — but left unchecked, they ship secrets in commits, add CVE-laden libraries, skip tests, ignore stack conventions, and produce code the next developer can't follow.

**Raven-Codex is the discipline layer between Codex and your codebase.** It doesn't slow you down. It makes sure what ships is actually good.

---

## What's Included

### 🧠 Andie v5.2 — AI Architect

Every session starts with Andie. It detects your domain, loads the right specialist triad, generates domain-specific questions, and holds at every decision until you confirm.

- **Specialist Triads** — every domain loads 3 experts: 🏢 Functional · ⚙️ Technical · 📊 Data
- **HITL gates** — every recommendation is a PROPOSAL (accept / modify / reject). Nothing proceeds without your explicit response
- **Domain-adaptive questions** — detects your domain, generates the right 5-8 questions, shows them before asking
- **Mode previews** — Deep / Kaizen / War / Drama shown with concrete per-problem previews before you pick
- **Continuous OODA** — fires after every round. Pivots are gated, never auto-applied

### 🛡️ 10 Guard Agents

| Agent | What it protects |
|---|---|
| **manifest-checker** | Verifies `.raven/manifest.json` exists and is valid before any task runs |
| **stack-validator** | Catches wrong-stack libraries. Warns during coding, hard blocks at PR merge |
| **style-enforcer** | Enforces code style. Advises during task, blocks at PR |
| **architecture-guard** | Ensures architecture decisions are documented. Missing diagram = warn, block after 24h |
| **db-guard** | Catches inline SQL in non-SQL files, missing ERDs, broken migration numbering |
| **skill-guard** | Prevents skills from reading secrets, modifying settings, or acting outside scope |
| **claude-mem** | Writes structured session memory to `.raven/memory/`. Surfaces open items at session start |
| **guard-git-watch** | Hard blocks any unexpected read of `.env`, SSH keys, or credential files |
| **odoo-guard** | Odoo: catches hardcoded DB IDs, raw SQL in ORM context, broken module structure |
| **salesforce-guard** | Salesforce: catches SOQL/DML inside loops, missing bulk patterns, hardcoded IDs |

### 🔒 PR Gate — What Gets Checked

Before any PR merges:

```
Secrets in staged files    → hard block merge
CVE critical (CVSS >7)     → hard block merge
Force push detected        → hard block
>100 rows deleted          → approval flow required
Schema drop detected       → hard block + escalate
Port 0.0.0.0 opened        → hard block + escalate
```

### 📦 55 Domain Skills

Skills load at session start and activate when your work matches their domain.

**Orchestration:** `andie` v5.2 — multi-modal architect (Deep · Kaizen · War · Drama · specialist triads · HITL)

**Raven Core:** `raven-core` · `raven-plan` · `raven-review` · `raven-refactor` · `raven-test` · `raven-security` · `raven-document` · `raven-expert` · `raven-debug` · `raven-init` · `raven-scaffold` · `raven-search` · `raven-sync` · `raven-approve` · `raven-audit` · `raven-harden` · `raven-incident` · `raven-status` · `raven-cve-check` · `raven-secret-scan` · `raven-registry-register` · `raven-registry-sync`

**Cloud:** `aws` · `gcp` · `azure` · `oci`

**Data & Streaming:** `kafka` · `postgres` · `redis` · `bigdata` · `dataeng` · `vector-db`

**Infrastructure:** `k8s` · `terraform` · `devops` · `vault`

**Frameworks:** `fastapi` · `nicegui`

**AI & ML:** `aiml` · `dynamic` (on-demand expert for any unknown domain)

**Enterprise:** `odoo` · `salesforce`

**Oracle:** `oracle-db` · `oracle-apex` · `oracle-apexlang` · `oracle-graal` · `oracle-fusion` · `oracle-oci` — thin dynamic-fetch routers; content pulled from [giggsoinc/skills](https://github.com/giggsoinc/skills) at runtime

**Tooling:** `security` · `log-management` · `agent-chaining` · `tools-landscape` · `task-observer`

### 🔄 Version Check — Every Session

Raven-Codex checks its version at every session start:

- **Up to date** → silent
- **1–2 releases behind** → banner: "Update available — say 'update raven' to sync"
- **3+ releases behind** → **auto-syncs automatically**, no action needed

---

## Enforcement Model

| | Claude Code | Codex / Copilot |
|---|---|---|
| **Enforcement point** | Pre-commit hook | PR gate + pre-task hook |
| **CVE scan** | On import detection | On PR open |
| **Secret scan** | On file save | On PR open |
| **Audit log** | Every tool call | Every PR event |
| **HITL** | In-session PROPOSAL gates | PROPOSAL gates in Andie |
| **Guard agents** | Background, always on | Background, always on |
| **Version check** | Session start | Session start |
| **Engine** | raven-core v3.0 | raven-core v3.0 |

---

## Specialist Triads

For every domain, Andie loads three specialists — Functional + Technical + Data — surfacing blind spots a single expert would miss.

| Domain | 🏢 Functional | ⚙️ Technical | 📊 Data |
|---|---|---|---|
| Oracle ERP Fusion | Functional Consultant (O2C/P2P/R2R) | Fusion Dev (FBDI, BIP, REST, OIC) | Data Specialist (OTBI, FRS, ADW) |
| Oracle DB | DBA / Schema Architect | PL/SQL Developer | Performance & Analytics Engineer |
| Oracle APEX | App Architect | APEX Developer (pages, plug-ins, REST) | Data Modeler |
| Oracle APEXLang | Language Strategist | APEXLang Engineer | Data Flow Specialist |
| Oracle GraalVM | Polyglot Architect | GraalVM Engineer (native-image, Truffle) | Performance Analyst |
| Oracle OCI | Cloud Architect | OCI Engineer (compute, networking, storage) | Data & AI Services Specialist |
| Salesforce | Domain Expert / BA | Dev (LWC, APEX, Flow) | Agentforce + Data Cloud Architect |
| AWS GenAI / ML | Use Case Strategist | GenAI Engineer (Bedrock, SageMaker) | Data Engineer (Glue, Athena) |
| Agentic AI / GraphRAG | AI Product Strategist | AI Engineer (LangGraph, A2A, MoE) | AI Data Engineer (vector, graph) |
| SAP S/4HANA | Functional Consultant | ABAP / BTP / CAP Developer | BW / Analytics Cloud |
| Data Engineering | Data Product Owner | Pipeline Engineer | Data Architect (schema, lineage) |
| Security | CISO Advisor | Security Engineer | Security Analyst (SIEM, logs) |

Unknown domains → `dynamic-specialist` (HIGH / MEDIUM / VERIFY confidence, live search on VERIFY).

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/codex/install.sh | bash
cd YourProject && raven-codex-setup
```

See [HOW-TO-USE.md](HOW-TO-USE.md) for full setup, PR gate wiring, and enterprise MDM options.

---

## Companion Repos

| Repo | For |
|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) | Claude Code full install + plugin ZIP |
| [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex) | This repo — Codex / Copilot |
| [giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) | Production-grade guard layer |
| [giggsoinc/andie](https://github.com/giggsoinc/andie) | Andie v5.2 standalone (ChatGPT, Gemini, Manus, Perplexity) |

---

## License

MIT — [Giggso](https://giggso.com)
