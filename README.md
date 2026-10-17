<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# Raven v6.0 — The Open-Source Solution to AI Comprehension Debt.

**Raven is the open-source solution to AI comprehension debt — a local AI Engineering Control Plane built to fight the two things AI coding actually breaks: discipline (code shipping faster than the thinking behind it) and comprehension debt (nobody remembering what the AI wrote, or why). One governed local layer routes each prompt to the right expert, blocks secrets and vulnerable code at the source, meters every token and dollar with verified math, and keeps your team's decisions in a memory that outlives the session.**

AI codes fast. Raven enforces Discipline — Strategic Thinking, Scalable Structure, Security at Source. How, in simple terms:

- **Strategic Thinking** — done by two orchestrators, picked automatically based on what you're doing:
  - **Andie** — for an enhancement or a new feature. Validates first, then the guided explanation, then waits for your go before touching code.
  - **Andie-Jr** — for a bug, error, or fix. Finds the root cause first, then the guided explanation. It does not take new design.
- **Scalable Structure** — every prompt is routed to the right expert automatically. 61 specialists, one per domain, picked by deterministic rules — and you always see a one-line note saying who's handling it and why. Works the same on one repo or a hundred.
- **Security at Source** — guards run on your machine, at the moment code is written and committed: secrets are blocked, vulnerable libraries are blocked, and edits are blocked until the thinking actually happened. Not a report after the damage — a gate before it.

All local. Zero telemetry. MIT.

`#comprehension_debt` `#ai_coding` `#claude_code` `#grok` `#codex` `#cursor` `#discipline_engine` `#token_cost` `#secret_scan` `#cve` `#mcp` `#obsidian` `#agent_memory`

## Plugin — what you can do

One plugin for every host. Build it with `bash plugin/make-plugin.sh`. The zip is `plugin/raven-plugin-v6.0.zip`. Same artifact for Claude Code, Claude Desktop, and the other hosts (`install-host.sh`).

| You want to | In the plugin |
|---|---|
| Plan new work | **Andie** — 3-angle plan, wait for go-ahead |
| Debug existing code | **Andie-Jr** — 2-round root cause → fix |
| Route every prompt | `model-router.py` — visible `🔀` + cheapest adequate tier |
| See spend | Local dashboard + `/run-costs` (calculator; billed $ if API keys in env) |
| See the repo | OKF **Graph** (files/commits, search, open file) |
| Stop secrets / CVEs | Pre-commit + skills: secret scan, CVE gate |
| Work in Grok / Codex / Cursor / AntiGravity | `/raven-init` or `/raven-debug` runs `host-ensure.py --open` (python wrapper + `.agents/agents.md` + dashboard) |
| Slash commands | `/raven-init`, `/raven-debug`, `/run-costs`, `/andie`, `/andie-jr`, … |

Calculator spend is local. Check **actual billed** cost on the Costs pane or `/run-costs`.

## Install

Raven is **not** in an Anthropic-hosted plugin marketplace — `/plugin marketplace add giggsoinc/raven` will not work. Pick one:

1. **Clone + install (Claude Code)** — `git clone https://github.com/giggsoinc/raven.git && claude plugin install ./raven/plugin`
2. **One zip** — build `plugin/raven-plugin-v6.0.zip` with `bash plugin/make-plugin.sh`. Claude: unzip then `claude plugin install <dir>`. Other hosts: `bash install-host.sh /path/to/project` (see [plugin/HOSTS.md](plugin/HOSTS.md)).
3. **Let Claude do it** — inside a Claude Code session, ask Claude to clone the repo and run the install command for you (same two steps as Option 1, just delegated)

Full walkthrough (enterprise admin upload, org-wide managed deployment, troubleshooting): [claude_plugin_readme.md](./claude_plugin_readme.md)

Then restart your session. You should see the Raven greeting:

```
🪶 Raven ✅  |  {your-project}  |  {stack}
   Andie is your discipline layer. What are you working on?
```

## Getting Started — After Install

The plugin gives Claude the skills and guards. Each **project** still needs a one-time setup pass for hooks, engine scripts, and a manifest:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh)   # once per machine
cd your-project && raven-setup                                                         # once per project
```

Two files come out of this setup, in plain terms:
- **`.raven/manifest.json`** — your project's config card: what language/stack you use, solo or team mode, which guard rules are on. Andie and the guards read this before doing anything, so they act like a Postgres expert on a Postgres project instead of guessing.
- **`.raven/manifest.secrets.json`** — only needed if you want commit/block email or Slack alerts. It holds those notification credentials, is gitignored by default, and everything works fine without it (Raven just skips notifications silently).

### New repo (greenfield)

`raven-setup` finds no file signatures in an empty directory, so it asks 1–3 quick questions (mode: solo/team/enterprise, primary language, cloud provider) and builds `.raven/manifest.json` entirely from your answers. Start working normally — Andie routes every prompt and guards activate as soon as files exist.

### Existing repo (brownfield)

`raven-setup` runs a detector that auto-classifies the work type (code / infra / data / docs / salesforce / odoo / mixed) from file signatures already in your repo. **Known limitation:** that only sets the work-mode label — it does not read `package.json`/`requirements.txt`/etc. to auto-fill the manifest's stack fields, so you'll still be asked to manually pick languages, databases, and cloud provider even though that info is already in the repo. If `.raven/manifest.json` already exists, setup skips straight to "already configured."

This is also where **Andie-Jr** earns its keep: once the manifest is in place, any bug report on this existing codebase gets a 2-round root-cause triage instead of an open-ended investigation — faster than either a from-scratch plan (Andie) or no structure at all (plain Claude).

## Quick start

| You type | What happens |
|---|---|
| `why is auth failing since yesterday?` | routed to **andie-jr** — 2-round triage: root cause → fix → audit note |
| `should we use Postgres or Mongo here?` | routed to **andie** — one mode card, 3-angle review, you approve each step |
| `/andie` or `/andie-jr` | force the route explicitly |
| `git commit` with a staged API key | **hard block** at the pre-commit gate, with the line that triggered it |
| `rename this variable` | routed nowhere — trivial edits skip the ceremony |

## What's included

- **2 orchestrators** — Andie (plan-first, one hard gate, critic voice) and Andie-Jr (brownfield debug, max 2 rounds)
- **Deterministic routers** — repo-state + intent routing with visible one-line toasters; never routes silently
- **61 domain skills** — FastAPI, Postgres, K8s, Terraform, Salesforce, Odoo, Oracle, AWS/GCP/Azure, and more, loaded only when your work matches
- **Local guards** — secret scan + CVE check (CVSS >7 blocks) at every commit; optional edit gate (`raven-skill-gate`, shadow/soft/hard modes); style and architecture checks
- **Cost-aware model routing** — prompts classified to the cheapest adequate tier; secret-laden context forced to a local model
- **Educate (default guided)** — `.raven/educate.json` (missing = guided). Claude PreToolUse **denies** writes until `go ahead`. Other IDEs: same loop from the boot file (`educate=`). Off: `educate off` or `Lucky` (persists; SessionStart does not wipe the file). Read-only research always passes.
- **Audit + memory** — JSONL audit logs; **human** notes in `~/RavenVault` (Obsidian + dashboard); **agent** start is **not** the vault. First load is `scripts/memory/ide-boot.py` (`load=1` → Read `.raven/memory/CARD.md` only).

## Agent memory and IDE hosts

Agents do **not** inject `~/RavenVault` or `knowledge-graph.json` at boot. `vault-load.py` is a **manual** CLI only.

| Step | What |
|---|---|
| **Stop** | `obsidian-log.py` writes the vault session note **and** `.raven/memory/CARD.md` (schema 1, project from this `manifest.json`, open questions/decisions, dashboard path). |
| **First load** | `python3 scripts/memory/ide-boot.py` — prints `host`, `rules`, `load=0\|1`, `memory=`, `educate=`. If `load=1`, Read **only** that memory path. |
| **Map** | `.raven/boot.json` — env → host → native one-line rules file. |

| Host | Env (any) | Native file (one line: run `ide-boot.py`) |
|---|---|---|
| Claude Code | `CLAUDECODE`, `CLAUDE_PLUGIN_ROOT` | `CLAUDE.md` |
| Grok | `GROK_AGENT`, `GROK_SESSION_ID` | `AGENTS.md` |
| Codex | `CODEX_HOME`, `CODEX_THREAD_ID` | `AGENTS.md` |
| Cursor | `CURSOR_AGENT`, `CURSOR_TRACE_ID` | `AGENTS.md` |
| AntiGravity | `ANTIGRAVITY`, `ANTIGRAVITY_CLI_ALIAS` | `.agents/agents.md` |
| Windsurf | `WINDSURF`, `WINDSURF_IDE` | `.windsurf/rules/ide-boot.md` |
| Replit | `REPL_ID`, `REPL_OWNER` | `replit.md` |
| Gemini CLI | `GEMINI_CLI` | `GEMINI.md` |
| unknown | none of the above | `AGENTS.md` + card still if `load=1` |

Claude `SessionStart` runs `session-start.py` only (**no** `vault-load`). Codex/Grok/Cursor have no Claude hooks — they rely on `AGENTS.md` + the router. Dashboard for humans: `~/RavenVault/dashboard.html`. Details: [docs/RAVENVAULT-GRAPH-AND-MEMORY.md](docs/RAVENVAULT-GRAPH-AND-MEMORY.md). Later-removal candidates (shims, old digest, vault KG on the dashboard): [docs/DEPRECATIONS.md](docs/DEPRECATIONS.md) — **do not delete in this version**.

## When to Use Raven — Use Case Table

| Scenario | Raven | Plain Claude | Notes |
|----------|-------|-------------|-------|
| **Brownfield bug** — *"Why is auth timing out?"* | ✅ Faster | ❌ | 2-round triage beats open-ended; forces root cause before fix. |
| **Architecture decision** — *"Should we migrate to Postgres?"* | ✅ Better | ❌ | Triad (Functional/Tech/Data) catches angles one perspective misses. |
| **Commit-time security** — prevent secrets/CVEs shipping | ✅ Hard-block | ❌ | Pattern-based detection; reduces risk, not foolproof. |
| **Routine feature work** — *"Build me a login form"* | ❌ Slower | ✅ Faster | Raven adds ceremony; plain Claude is direct. |
| **Quick lookup** — *"What's the CloudRun pricing?"* | ❌ Overkill | ✅ Direct | No decision needed; Raven's routing overhead is wasted. |

---

## Andie + Andie-Jr: The Decision Duo

### Andie (Architecture, Design, Strategy)

Runs a **Drama panel debate** when your decision has tradeoffs:
- **Functional Lead** — business/domain owner perspective
- **Technical Lead** — system/implementation owner perspective
- **Data Lead** — metrics/integration owner perspective

Each panelist argues their angle. You steer the debate. Final output: **decision + rationale + rejected alternatives + risks**.

### Andie-Jr (Brownfield Triage)

For broken systems: **problem → diagnosis → fix → audit**.
- Round 1: 2 clarifying questions that isolate the root cause.
- Round 2: Root-cause explanation + fix + verification steps + audit note.

Not for greenfield builds; only for existing systems showing symptoms (errors, timeouts, regressions).

### Routing Table

| Scenario | Route | How |
|----------|-------|-----|
| **Brownfield bug** ("why is X broken?") | andie-jr | Repo >1 commit + symptom language detected |
| **Greenfield or architecture** ("should we...?") | Andie | Repo ≤1 commit OR Drama-mode intent |
| **Data question** ("what is...?", "list...", "show...") | Direct | No change verbs (build, fix, create); no routing overhead |
| **Force path** (`/andie`, `/andie-jr`) | Explicit | User typed the skill name — routing wins always |

---

## How Raven Works — The Full Stack

### Architecture Overview

```
UserPromptSubmit (every message)
  ↓
triage-router.py [deterministic repo-state]
  ├─ Brownfield (>1 commit) → andie-jr
  ├─ Greenfield (≤1 commit) → Andie
  ├─ Data question (read/list/explain, no change verbs) → direct
  └─ Force path (/andie, /andie-jr) → always wins
  ↓
[Specialist runs, edit/commit allowed]
  ↓
PostToolUse: secret-scan.py (after Write/Edit)
  ├─ AWS keys, OpenAI keys, GitHub tokens, SSH, bearer tokens → WARN
  └─ Send intent to audit log (`.raven/audit/YYYY-MM-DD.log`)
  ↓
Pre-commit hook (.git/hooks/pre-commit)
  ├─ secret-scan.py → HARD BLOCK if secrets staged
  ├─ cve-check.py (new imports) → HARD BLOCK if CVSS >7
  ├─ style-enforcer (line count, type hints, docstrings) → HARD BLOCK if violated
  ├─ architecture-guard (doc alignment) → WARN now, block in 24h
  ├─ db-guard (inline SQL, missing ERDs, migration order) → WARN
  └─ notify.py (SMTP + Slack) → send pass/fail summary + audit
  ↓
Commit lands (or blocked + approval flow starts)
```

### 7 Guard Agents — What They Check

| Guard | Fires | Detects | Action |
|-------|-------|---------|--------|
| **manifest-checker** | SessionStart | Missing `.raven/manifest.json` | Hard stop with setup guide |
| **secret-guard** | PostToolUse + pre-commit | AWS keys, tokens, SSH, PII in staged files | Warn on edit / hard block on commit |
| **cve-check** | New `import X` statement | Library vulnerabilities (CVSS >7) | Warn during coding / hard block at commit |
| **stack-validator** | Import detected + not in approved list | Unapproved libraries (Polars vs Pandas, etc.) | Warn / block at commit |
| **style-enforcer** | File edit | Line count >200, missing type hints, no docstrings | Advise / block at commit |
| **architecture-guard** | New file created | Missing `.raven/architecture.md` documentation | Warn / hard block after 24h grace |
| **db-guard** | File edit (SQL, migrations) | Inline SQL in non-SQL files, missing ERDs, broken migration numbering | Warn in audit log |

### Notifications (SMTP + Slack)

Fires from pre-commit hook on success or block:
- **Commit pass**: Confirmation email + Slack (to recipients in `.raven/manifest.secrets.json`)
- **Commit blocked**: Alert with violation count + Slack
- **Override used**: Log to audit trail + email
- **Token warning**: 75% / 90% thresholds

---

## Tokenomics — What Raven Costs Per Message

**Rule: enforcement runs in Python hooks, outside the model — it costs zero
tokens.** Gates, guards, scanners, audit logs, and the pre-commit pipeline
never enter Claude's context. Only the thin advisory layer does:

| Layer | Frequency | Tokens |
|---|---|---|
| Hooks: skill gate, secret scan, CVE, pre-commit, token guard | every tool call / commit | **0** |
| Skill-reminder + router toasters (context injection) | per message | ~100 |
| Session boot (greeting + transparency banner) | once per session | ~500 |
| Specialist SKILL.md load (when a skill actually runs) | once per session | ~1–2k |
| Violation messages (block/warn) | only on violation | ~50 |

Steady-state: **~2% overhead** on a typical session — and the model router
(0-token hook) claws that back by tiering simple prompts to cheaper models and
routing secret-laden context to a free local model. Full breakdown, including
where Raven saves tokens: [docs/TOKENOMICS.md](docs/TOKENOMICS.md) ·
diagrams: [business view](docs/Agent_token_architecture_business.html) ·
[technical view](docs/Agent_token_architecture_tech.html).

---

## Raven 6.0

Raven 6.0 is the current release. One plugin covers Claude, Grok, Codex, Cursor, Windsurf, VS Code, AntiGravity, Gemini, and Replit.

**Jev.** On first setup Raven asks if you have a Jev TypeSafe key. If you do, you paste it. The key is stored in `.raven/manifest.secrets.json` (gitignored, mode 600) and is never printed. If you do not, Raven keeps its default routing. Raven does not read or bill a Jev token balance. Before the paste, and again after the save, Raven tells you that path.

**Local and other models.** After the key question, Raven asks what you prefer. It checks Ollama at `127.0.0.1:11434` and LlamaCPP at `127.0.0.1:8080`. A detected server becomes the flash model (`SIMPLE`) and the thinking model (`MEDIUM` and `COMPLEX`). You can also name any other model and paste that provider’s key at the same step. Model names go in `.model.env`. Keys stay in the secrets file.

**Ask order.** A bug, error, or fix goes to Andie Jr, then the guided explanation. An enhancement or new feature goes to Andie, then the guided explanation. The skill gate blocks an edit until that reviewer and Guided are both stamped. The other reviewer does not unlock the edit.

**Still in this release.** Secret and CVE blocks at commit, local token and cost metering, the dashboard, and cross-session memory. Details of older releases stay in [VERSIONLOG.md](VERSIONLOG.md).

---

## Other Install Paths

**One ZIP (all hosts):** build `plugin/raven-plugin-v6.0.zip` with `bash plugin/make-plugin.sh`. Claude Desktop: Settings → Extensions → Add plugin. Other IDEs: `bash install-host.sh` (see [plugin/HOSTS.md](plugin/HOSTS.md)).

**From source:**

```bash
git clone https://github.com/giggsoinc/raven.git
cd raven && bash plugin/make-plugin.sh   # builds plugin/raven-plugin-v6.0.zip
```

---

## Contributing

Raven is MIT licensed. Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to add a skill
- How to write a guard agent
- Style standards (Giggso code style — type hints, docstrings, logging, ≤200 LOC per file)
- Pre-commit hook requirements

---

## Raven Enterprise

This repo is the **free tier — everything runs local**, MIT-licensed, complete as-is.

**Raven Enterprise** (paid, sold separately) adds what teams and compliance departments need on top: Hub dashboards across developers and repos, per-developer token attribution and chargeback, compliance/audit reporting, centralized policy sync, and commercial support.

→ [giggso.com](https://giggso.com)

---

## Support & Issues

- **Bug reports**: [GitHub Issues](https://github.com/giggsoinc/raven/issues)
- **Questions**: Start a discussion in [GitHub Discussions](https://github.com/giggsoinc/raven/discussions)
- **Security vulnerabilities**: Email `rv@giggso.com` (do not open public issue)

---

<p align="center">
  <strong>Built by <a href="https://giggso.com">Giggso</a> · <a href="https://github.com/giggsoinc/raven">GitHub</a> · MIT License</strong>
</p>

*Raven 6.0 — one plugin, every host.*


*Raven 6.0 — Governance for AI coding at the speed of thought.*
