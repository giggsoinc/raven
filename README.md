<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

<h1 align="center">Raven v4.0</h1>

<p align="center">
  <strong>AI-native engineering discipline for Claude Code · GitHub Copilot · OpenAI Codex</strong><br/>
  61 domain skills · 10 guard agents · CVE scanning · secret detection · audit logs · cross-session memory<br/>
  Andie greets you on install. ≤2 questions. No bash. No 8-question wizard.
</p>

<p align="center">
  <a href="https://github.com/giggsoinc/raven/releases/tag/v4.0.0">v4.0.0</a> ·
  <a href="docs/HOW-TO-USE.md">Full Documentation</a> ·
  MIT License ·
  Built by <a href="https://giggso.com">Giggso</a>
</p>

---

## What Raven Is — In One Line

Raven is a **routing + security-gate + decision-documentation layer** for AI coding assistants. It is not a universal reasoning engine. It earns its keep in three specific places: **brownfield debugging, regulated-domain governance, and commit-time security.**

---

## The Three Things Raven Does Well

### 🔧 1. Brownfield Debugging — `andie-jr`

When something is broken, `andie-jr` runs a focused 2-round triage: asks the few questions that matter, then returns **problem → root cause → fix → why → audit note**. In practice this is meaningfully faster than open-ended back-and-forth, because it forces the root-cause question before the fix.

> Try it: *"Why is my auth timing out?"* — it asks 2 clarifying questions, then pinpoints the cause.

### 🧠 2. Architecture Decisions — `andie`

For design and tradeoff decisions, Andie loads a **Specialist Triad** — Functional, Technical, Data — so you see the problem from three angles instead of one. Every recommendation is a **proposal you approve, modify, or reject** (HITL). It plans and hands off; it does not write the code itself.

> Best for multi-team or regulated decisions where a missed angle is expensive. For routine feature work, plain Claude is faster — see [Honest ROI](#honest-roi--when-to-use-raven-and-when-not-to).

### 🛡️ 3. Commit-Time Security — Guards

Before a commit lands, Raven scans staged files for **secrets** (API keys, tokens, private keys) and added libraries for **CVEs** (CVSS > 7 = hard block). This is the layer that prevents the expensive mistakes.

---

## How Guards & Hooks Actually Fire

> **Honesty note:** Guards and hooks are **event-driven, not "always on."** They fire when their trigger condition matches. Detection is pattern-based and can miss edge cases — they reduce risk, they do not guarantee catching everything.

### Commit-time gate

```
Secrets in staged files    → hard block commit
CVE critical (CVSS >7)     → hard block commit
Force push to main         → hard block
>100 rows deleted          → approval flow required
Schema drop detected       → hard block + escalate
Port 0.0.0.0 opened        → hard block + escalate
```

### Guard agents (fire on matching conditions)

| Guard | Fires when | Action |
|---|---|---|
| **manifest-checker** | Before work starts | Verifies Raven config present |
| **stack-validator** | Wrong-stack library detected | Warn coding / block commit |
| **style-enforcer** | Style rule violated | Advise coding / block commit |
| **architecture-guard** | Structural change, no diagram | Warn now / block in 24h |
| **db-guard** | Inline SQL, missing ERD, bad migration order | Warn |
| **skill-guard** | Skill tries to read secrets / change settings | Block |
| **guard-git-watch** | Unexpected read of `.env` / SSH keys | Block |
| **claude-mem** | Session end | Write memory to `.raven/memory/` |
| **odoo-guard** | Odoo anti-patterns (hardcoded IDs, raw SQL) | Warn |
| **salesforce-guard** | SOQL/DML in loops, hardcoded IDs | Warn |

### Lifecycle hooks (fire on Claude Code events)

| Event | Hook | Type | What it does |
|---|---|---|---|
| `SessionStart` | `session-start.py` | Context | Brownfield/greenfield + model detection |
| `UserPromptSubmit` | `triage-router.py` | Route | Detects brownfield symptoms → suggests `andie-jr` |
| `UserPromptSubmit` | `architect-router.py` | Route | Detects design decisions → suggests `andie` |
| `UserPromptSubmit` | `model-router.py` | Route | Classifies complexity tier |
| `UserPromptSubmit` | `cve-prompt-guard.py` | Warn | Flags `pip/npm install` intent |
| `PostToolUse` Write/Edit | `secret-scan.py` | Async warn | Scans written files for secrets |
| `PreToolUse` Bash | `schema-guard.py` | **Block** | Stops DROP/TRUNCATE/DELETE-without-WHERE |
| `Stop` | `obsidian-log.py` | Async | Writes session summary to vault |
| `Stop` | `token-guard.py` | Async | Records session token usage |

**The git pre-commit gate is a separate mechanism** (`.git/hooks/pre-commit`), not a Claude Code hook. It runs the secret + CVE + style gate and fires `notify.py` (SMTP + Slack) on pass/block.

---

## Andie — Auto-Triggered, Conditionally

Andie does **not** load on every prompt. Routers on `UserPromptSubmit` decide via pattern match:

| Your prompt | What loads |
|---|---|
| "design a multi-tenant API" / "should I use X or Y?" | ✅ `andie` (architecture) |
| "why is auth timing out?" / "this is broken" | ✅ `andie-jr` (debug) |
| "write a helper function" | ❌ neither — plain Claude (or invoke a skill directly) |
| "add this feature" | ⚠️ only if it reads as multi-component |

Routing is **regex-based**, so it can miss edge cases. When a router doesn't fire but you want Andie anyway, use the **force-path commands**: `/andie` (planning/architecture) and `/andie-jr` (bugs/debugging) load them unconditionally. You can also invoke any skill by name.

Andie's modes — **Deep** (explain), **Kaizen** (improve), **War** (incident), **Drama** (debate) — are **selected by you**, not auto-detected. Each generation is capped at 200 words to keep a human pace, and ends with a Feynman-style recap. OODA runs as structured checkpoints (Observe → Orient → Decide → Act) per round — it is a linear framework, not an adaptive loop that restarts on new information.

---

## Cost-Aware Model Routing

Raven classifies each prompt and routes to the cheapest adequate model:

| Tier | Triggers | Model |
|------|----------|-------|
| **SIMPLE** | typo, rename, single-file edit | Haiku |
| **MEDIUM** | tests, docs, debug, refactor | Sonnet |
| **COMPLEX** | architecture, security audit, multi-file | Opus |
| **LOCAL_ONLY** | secrets in prompt, offline | Ollama (on-machine) |

- **Token usage from your *previous* session** is shown in the session-start banner (not a live in-session meter — a live meter is on the roadmap).
- **Secrets in your prompt** → forced to local Ollama. Cloud never sees them.
- **No telemetry. Local-only.** All cost data stays on your machine.

Configure via `.raven/.model.env` — raven-init writes it for you.

---

## Cross-Session Memory (Obsidian-Compatible)

On session end, `obsidian-log.py` writes a summary — AI recap, files touched, git state — to `~/RavenVault/sessions/`. The **next** session can read it for carry-forward context.

> This is **session continuity / audit trail**, not a current-session token optimisation. It helps the next session start warm and gives teams a searchable decision log. It does not reduce tokens in the session that's running.

---

## 61 Domain Skills

Skills load when your work matches their domain — not all at once. A skill stays in context once invoked, so a 5+ message session accumulates the skills you've used; the benefit is **not loading all 61**, not zero-cost skills.

**Orchestration** · `andie` · `andie-jr` · `andie-guru` (plain-English explainer)
**Database router** · `db-router` → Postgres · MySQL · MongoDB · Qdrant · Databricks · Snowflake
**Frontend router** · `ui-router` → React · Vue · Angular · Vanilla JS · UI/UX
**Cloud** · `aws` · `gcp` · `azure` · `oci`
**Data & Streaming** · `kafka` · `postgres` · `redis` · `bigdata` · `dataeng` · `vector-db`
**Infra & DevOps** · `k8s` · `terraform` · `devops` · `vault`
**Frameworks** · `fastapi` · `nicegui`
**AI & ML** · `aiml` · `dynamic` (on-demand expert for unknown domains)
**Enterprise** · `odoo` · `salesforce`
**Oracle** · `oracle-apex` · `oracle-apexlang` · `oracle-db` · `oracle-fusion` · `oracle-graal` · `oracle-oci`
**Engineering Practice** · `raven-core` · `raven-plan` · `raven-review` · `raven-refactor` · `raven-test` · `raven-security` · `raven-document` · `raven-expert`
**Tooling** · `security` · `log-management` · `agent-chaining` · `tools-landscape` · `task-observer`

---

## Honest ROI — When To Use Raven (and When Not To)

### ✅ Worth it

| You are… | Why |
|---|---|
| Debugging a brownfield codebase | `andie-jr` finds root cause fast |
| A team of 10–50 with governance needs | Shared guards + audit trail across everyone |
| In a regulated domain (finance/health/gov) | Decision documentation pays for itself |
| Making a high-risk decision | Three expert angles catch blind spots |
| New to a domain | Forced structure catches gaps you can't see yet |

### ❌ Not worth it

| You are… | Use instead |
|---|---|
| A solo dev moving fast | Plain Claude + good prompting (~4× faster on routine work) |
| A <5-person startup optimising for velocity | HITL gates add friction you don't need yet |
| A mature team with strong code review | You already have the discipline |
| Doing 99% routine feature work | Plain Claude wins |

### Per-task reality

| Task | Best tool |
|---|---|
| Production incident triage | **andie-jr** |
| Brownfield bug | **andie-jr** |
| Design an integration | Plain Claude (faster) or Andie (if multi-team) |
| Add a feature | **Plain Claude** |
| Multi-team architecture decision | **Andie** (replaces an alignment meeting) |
| Compliance audit trail | **Andie** (decision log built in) |

---

## Who It's For — Plain English

- **Fresh grads / juniors:** *"I ask clarifying questions before diving in, and I check your code for secrets and known-vulnerable libraries before you commit."*
- **Teams 10–50:** *"Everyone gets the same guardrails and the same reasoning framework, with an audit trail for compliance."*
- **Enterprises:** *"A governance layer with decision documentation and commit-time security scanning."*
- **Solo devs:** *"Honestly? Plain Claude with good habits is faster. Use Raven for the security gates if you want them."*

---

## Specialist Triads — How Andie Handles a Domain

For each domain, Andie loads three specialists instead of one generalist — so a single expert's blind spot doesn't become yours.

| Domain | 🏢 Functional | ⚙️ Technical | 📊 Data |
|---|---|---|---|
| Oracle ERP Fusion | Functional Consultant | Fusion Dev (FBDI, BIP, OIC) | OTBI / FRS / ADW |
| Salesforce | Domain Expert / BA | Dev (LWC, APEX, Flow) | Agentforce + Data Cloud |
| AWS GenAI / ML | Use Case Strategist | GenAI Engineer (Bedrock, SageMaker) | Data Engineer (Glue, Athena) |
| Agentic AI / GraphRAG | AI Product Strategist | AI Engineer (LangGraph, CrewAI) | AI Data Engineer (vector/graph) |
| SAP S/4HANA | Functional (FI/CO/MM/SD) | ABAP / BTP / CAP Dev | BW / Analytics Cloud |
| Data Engineering | Data Product Owner | Pipeline Engineer | Data Architect |
| Security | CISO Advisor | Security Engineer | Security Analyst |
| Kubernetes / DevOps | Platform Product Owner | SRE Engineer | Observability Specialist |
| Odoo ERP | Functional Consultant | Developer (Python, OWL, XML) | Reporting / BI / OCA |

Unknown or mixed domains trigger `dynamic-specialist` — on-demand expert construction with a confidence rating (HIGH / MEDIUM / VERIFY) and live search when VERIFY.

---

## Install — Start Here

**Pick the one row that's you. Most people are the first row.**

| You are… | Do this | Time |
|---|---|---|
| 🟢 **Using Claude Desktop** (most people) | Download [`raven-plugin-v4.0.0.zip`](plugin/raven-plugin-v4.0.0.zip) → Settings → Extensions → Add plugin → drop the zip | ~90 sec |
| 🔵 **On the terminal / a team repo** | `curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh \| bash` | ~2 min |
| 🟣 **Setting up for an enterprise/org** | See [Enterprise Install](docs/raven-enterprise-install.md) | ~10 min |

Then **open your project and type anything.** Andie greets you, scans the project,
and builds the manifest — at most 2 questions.

> 👋 *"Hey, I'm Andie. I noticed you don't have a manifest yet — to get Raven working, I need to scan your project and build one. OK to proceed?"*

That's the whole install. Everything below is reference — you don't need it to start.

<details>
<summary>Windows terminal · what the script does · other docs</summary>

```powershell
# Windows
iwr https://raw.githubusercontent.com/giggsoinc/raven/main/install.ps1 | iex
```

- The terminal installer does the same thing the plugin does, **plus** writes
  project-level git hooks (pre-commit secret/CVE gate).
- Deeper references: [How to Use](docs/HOW-TO-USE.md) ·
  [Plugin Install detail](docs/raven-plugin-install.md) ·
  [Enterprise](docs/raven-enterprise-install.md)
- You should not need to read those to get started. If you do, that's a docs bug —
  tell us.
</details>

---

## How It Feels in Practice

**Adding an AWS Lambda:** Raven detects AWS, `aws-specialist` loads on a matching prompt. `import requests` triggers a CVE reminder. At commit, the secret scan checks staged files and the CVE scan checks added libraries.

**Designing a Salesforce flow:** Andie detects the domain, loads the SF triad, asks domain-specific questions, and proposes the architecture as a PROPOSAL you approve or modify.

**A CVE in a library you added:** Pre-commit hook fires, CVSS shown, > 7 hard-blocks. Approved dependency? `git commit -m "feat: X [GUARD:ALLOW-CVE]"`.

**2am, production down:** You invoke War mode. No ceremony — a triage block and a first action fast, with an incident log building as you go.

---

## Companion Repos

| Repo | For |
|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) | This repo — full install, plugin ZIP, all skills |
| [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex) | Codex / Copilot — plugin-only version |
| [giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) | DevOps / architects — production guard layer |
| [giggsoinc/andie](https://github.com/giggsoinc/andie) | Andie v6.3 standalone — ChatGPT, Gemini, Perplexity |

---

## License

MIT — [Giggso](https://giggso.com)

[docs/HOW-TO-USE.md](docs/HOW-TO-USE.md) · [CLAUDE.md](CLAUDE.md) · [plugin/README.md](plugin/README.md)
