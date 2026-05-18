<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# How to Use Raven-Codex — v3.0

> Raven discipline engine for OpenAI Codex · GitHub Copilot · Claude Code
> Part of the [Raven platform](https://github.com/giggsoinc/raven). MIT License.
> Built by [Giggso](https://giggso.com)

*HITL first. Specialist triads always. OODA continuous. Guardrails before you ship.*

---

## Prerequisites

| Requirement | Check |
|---|---|
| Git | `git --version` |
| Python 3.10+ | `python3 --version` |
| Claude Code, Codex, or Copilot | Active session |
| OpenAI API key | Optional — enables GPT CVE deep scan |

---

## Install — One Command

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/codex/install.sh | bash
```

Then in your project:
```bash
raven-codex-setup
```

This creates `.raven/manifest.json`, wires the PR gate, installs guard agents, and deploys `version-check.py`.

---

## What Happens at Session Start

Every session runs this sequence automatically, before waiting for your input:

### 1. Version Check
```
python3 .claude/scripts/version-check.py
```
- **Up to date** → silent
- **1–2 releases behind** → update banner shown
- **3+ releases behind** → auto-sync fires immediately, no action needed

### 2. Manifest Check
Reads `.raven/manifest.json`. If missing → guided setup (2 minutes, no hard stop).

### 3. Andie v5.2 Loads
Domain detection → specialist triad → domain-adaptive questions → mode preview → Assembly Card → GO.

---

## How Andie Works

Andie is the orchestration layer. Every task goes through Andie before any code is written.

### Step 0 — Mode Selection with Previews
Andie detects the right mode and shows what it would produce *for your specific task* — not generic descriptions. Four modes:

- **Deep** — domain expert explains with Feynman clarity. Default.
- **Kaizen** — root cause → fix hypothesis → verify → retrospective. For recurring failures.
- **War** — rapid triage, incident log, action owners. For production down or crisis.
- **Drama** — expert panel debates options to a conclusion. On-demand, for major architectural decisions.

### Domain Detection + Specialist Triad
Andie detects your domain and loads three specialists:

- 🏢 **Functional** — business process, domain rules, compliance
- ⚙️ **Technical** — implementation, APIs, architecture, code
- 📊 **Data** — flows, schema, pipelines, integration, reporting

**Example — Oracle ERP Fusion Order-to-Cash:**
```
DOMAIN DETECTED: Oracle ERP Fusion — Order to Cash

SPECIALIST TRIAD LOADING:
🏢 Functional  → Fusion O2C Functional Consultant
                 (process, compliance, exception handling)
⚙️  Technical   → Fusion Tech Specialist
                 (FBDI, BIP, REST, OIC integrations)
📊 Data        → Fusion Data Engineer
                 (OTBI, FRS, ADW staging, lineage)

Adjust triad, rename, or GO?
```

**Example — AWS GenAI:**
```
DOMAIN DETECTED: AWS GenAI / ML

SPECIALIST TRIAD LOADING:
🏢 Functional  → ML Use Case Strategist
                 (product, ROI, adoption, risk)
⚙️  Technical   → AWS GenAI Specialist
                 (Bedrock, SageMaker, Agents for Bedrock)
📊 Data        → AWS Data Engineer
                 (Glue, Athena, Lake Formation, S3)

Adjust triad, rename, or GO?
```

### Domain-Adaptive Questions
Context questions generated from your domain — shown to you before being asked, adjustable, one at a time.

**AWS ML project gets:**
1. What's the use case — RAG, fine-tuning, agents, or inference at scale?
2. Which AWS services are already in play?
3. What are the latency and throughput requirements?
4. What's the security and compliance posture?
5. What model(s) are you targeting?

Not: "What is your goal?" — that tells Andie nothing useful.

### HITL Gates
Every recommendation is a PROPOSAL. Nothing proceeds without your explicit response:

```
PROPOSAL — [Tech / Framework / Team / Approach]
Recommending:  [what]
Why:           [2 sentences]
Assumes:       [what this takes as given]
Risk if wrong: [what breaks]
→ Accept · Modify · Reject · Ask me more
```

HITL fires at: mode selection · domain/triad confirmation · question set · framework pick · tech stack · team assembly · every OODA pivot · every action after T+0 in War.

### OODA — After Every Round
```
[OODA — Round N]
Observe:  [what surfaced this round]
Orient:   [what it means for the problem]
Decide:   [stay course / PROPOSAL to pivot]
Act:      [next round focus]
```

---

## Guard Agents

Guard agents run in the background — no manual activation needed.

| Agent | When it fires | What it does |
|---|---|---|
| manifest-checker | Task start | Verify manifest valid |
| stack-validator | Library detected | Warn / block unapproved stack |
| style-enforcer | File saved | Advise during task, block at PR |
| architecture-guard | New significant component | Require architecture note |
| db-guard | SQL in non-SQL file | Flag and warn |
| skill-guard | Skill restricted action | Hard block |
| claude-mem | Session start/end | Load/write `.raven/memory/` |
| guard-git-watch | Sensitive file read | Hard block + alert |
| odoo-guard | Odoo .py/.xml | ORM discipline enforcement |
| salesforce-guard | SF .cls/.trigger/.js | Bulk pattern enforcement |

---

## PR Gate Setup

Wire the PR gate in your CI:

**GitHub Actions:**
```yaml
- name: Raven PR Gate
  run: python3 .claude/scripts/pr-gate.py
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**GitLab CI:**
```yaml
raven-gate:
  script:
    - python3 .claude/scripts/pr-gate.py
```

The gate checks: secrets · CVE · force push · mass deletion · schema drops · port exposure.

---

## CVE Check

Before adding any library:
```
Run raven_cve_check on <library-name>
```

- ✅ Clean → proceed
- ⚠️ Medium → warn + log + use safer version
- 🔴 Critical (CVSS >7) → hard block
- ❓ Unknown → approval flow required

---

## Session Memory

After every session, Andie writes a structured note to `.raven/memory/sessions/YYYY-MM-DD-{topic}.md`:

- Goal, domain, triad, framework used
- HITL log — every PROPOSAL and your response
- Decisions table, open questions, carry-forwards
- Obsidian-compatible frontmatter + DataView

At next session start: prior context surfaced. Open items only, no noise.

---

## Version Management

Raven self-checks at every session:

```bash
# Manual check
python3 .claude/scripts/version-check.py

# Manual sync
/raven-sync
```

- 0 behind → silent
- 1–2 behind → banner + on-demand sync offer
- 3+ behind → auto-sync, banner shown, done

---

## Slash Commands

| Command | What it does |
|---|---|
| `/raven-debug` | Full diagnostic — manifest, guards, skills, version |
| `/raven-review` | Review staged changes before commit |
| `/raven-approve` | Approve a pending library or action |
| `/raven-harden` | Review and address open security observations |
| `/raven-incident` | Switch Andie to War mode — incident triage |
| `/raven-scaffold` | Scaffold a new project with Raven manifest |
| `/raven-search` | Search skills for a domain or topic |
| `/raven-sync` | Sync Raven to latest version |
| `/raven-init` | Initialize Raven for a new project |

---

## MCP Tools

| Tool | What it does |
|---|---|
| `raven_status` | Show version, manifest, guards |
| `raven_cve_check` | CVE check a library |
| `raven_sync_libs` | Sync all project libraries against CVE database |
| `raven_debug` | Full diagnostic dump |
| `raven_violation` | Log a manual violation |

---

## Companion Repos

| Repo | For |
|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) | Claude Code full install + plugin ZIP |
| [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex) | This repo — Codex / Copilot |
| [giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) | Production protection layer |
| [giggsoinc/andie](https://github.com/giggsoinc/andie) | Andie v5.2 standalone for all platforms |

---

## License

MIT — [Giggso](https://giggso.com)
