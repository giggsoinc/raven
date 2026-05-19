# Raven v3.0 — Codex Discipline Rules

Read this before every task. These rules are non-negotiable.

---

## SESSION START — Version Check First

Before any task begins, run:
```
python3 .claude/scripts/version-check.py
```

| Result | Distance | Action |
|---|---|---|
| Up to date | 0 | Silent — continue |
| 1–2 releases behind | 1–2 | Show update banner — offer `/raven-sync` |
| 3+ releases behind | 3+ | Auto-sync immediately — no confirmation needed |

After version check passes → load manifest → load Andie → begin task.

---

## Andie v5.2 — Orchestration Layer

Every task goes through Andie first. Andie is not optional.

**What Andie does before any task starts:**
1. Detects domain from the task description
2. Loads the Specialist Triad for that domain (Functional + Technical + Data)
3. Generates domain-specific context questions — shows them before asking
4. Presents mode with concrete preview for this specific task
5. Runs proactive tech mapping — surfaces the right stack without being asked
6. Issues Assembly Card — full pre-flight summary. Hard stop until GO

**HITL is mandatory.** Every recommendation Andie makes is a PROPOSAL:
```
PROPOSAL — [category]
Recommending:  [what]
Why:           [2 sentences]
Assumes:       [what this takes as given]
Risk if wrong: [what breaks]
→ Accept · Modify · Reject · Ask me more
```
Nothing proceeds past a PROPOSAL without explicit response.

---

## Specialist Triads

For every detected domain, Andie loads three specialists:

- 🏢 **Functional** — business process, domain rules, compliance, org impact
- ⚙️ **Technical** — implementation, APIs, architecture, code patterns
- 📊 **Data** — flows, schema, pipelines, integration points, reporting

Each specialist surfaces their domain's corner cases at the end of every round. Unknown domains trigger `dynamic-specialist` with confidence assessment (HIGH / MEDIUM / VERIFY).

---

## Non-Negotiable Guard Rules

```
1. NO library added without CVE check — run raven_cve_check first
2. NO secrets in code — API keys, passwords, tokens go in environment variables only
3. NO force push to any branch — ever
4. NO TRUNCATE TABLE or DROP TABLE without approval
5. NO Terraform state file edits without approval
6. NO firewall rule opening 0.0.0.0/0
7. NO commit without .raven/manifest.json present
8. NO PROPOSAL skipped — every Andie recommendation requires explicit accept/modify/reject
9. NO version drift beyond 2 releases — auto-sync fires at 3+
```

---

## Before Adding Any Library

Run the CVE check first:
```
Run raven_cve_check on <library-name>
```

Wait for result:
- ✅ Clean → add it
- ⚠️ Medium CVE → warn, log to audit, use safer version
- 🔴 Critical CVE (CVSS >7) → hard block, do not install
- ❓ Unknown library → approval flow, do not install until approved

### CVE Scan Tiers — Which One Is Running?

Raven announces the scan tier before every check. Watch for this line:
```
Scan tier: GPT deep scan + PyPI          ← full scan, key available
Scan tier: PyPI basic scan only (GPT disabled — OPENAI_API_KEY not in shell env)  ← degraded
```

**If you see "PyPI basic scan only":**
- Raven correctly refused to read `.env` (security rule — never read credential files)
- The OpenAI key must be exported into the shell environment, not stored in `.env`
- Fix: add this to `~/.zshrc` or `~/.bashrc`:
  ```bash
  export OPENAI_API_KEY=sk-...
  ```
  Then: `source ~/.zshrc` (or restart terminal)
- Raven will then use GPT deep scan automatically — no other config needed

**Raven will NEVER read `.env`, SSH keys, or credential files for the API key.** This is correct behavior, not a bug. The key must live in the shell environment.

---

## Secret Detection

Never write these directly in code:
- API keys of any kind
- Passwords or tokens
- Private keys or certificates
- Database connection strings with credentials

Always use environment variables:
```python
import os
api_key = os.environ.get("OPENAI_API_KEY")
```

Secret scan runs on every staged file before any commit or PR merge. Hard block if found.

---

## OODA — Continuous Loop

After every task round, OODA fires automatically:

```
[OODA — Round N]
Observe:  [what new signal came from this round]
Orient:   [what it means for the problem]
Decide:   [adjustment needed? → PROPOSAL if yes]
Act:      [next round focus]
```

If Orient surfaces a significant shift → PROPOSAL before proceeding. Never auto-pivot.

---

## Guard Agents — Always Running

| Agent | Fires when | Action |
|---|---|---|
| manifest-checker | Before any task | Verify `.raven/manifest.json` valid |
| stack-validator | Library detected | Warn if not in approved stack |
| style-enforcer | File edited | Advise during task, block at PR |
| architecture-guard | Significant new component | Require architecture note |
| db-guard | SQL detected in non-SQL file | Warn + flag for review |
| skill-guard | Skill attempts restricted action | Hard block |
| claude-mem | Session start/end | Load/write `.raven/memory/` |
| guard-git-watch | Sensitive file read attempt | Hard block + alert |
| odoo-guard | .py or .xml in Odoo module | Enforce ORM discipline |
| salesforce-guard | .cls, .trigger, .js, .html | Enforce bulk patterns |

---

## PR Gate — What Gets Checked

Before any PR merges, the full gate runs:

```
Secrets in staged files    → hard block merge
CVE critical (CVSS >7)     → hard block merge
Force push detected        → hard block
>100 rows deleted          → approval flow required
Schema drop detected       → hard block + escalate
Port 0.0.0.0 opened        → hard block + escalate
```

Intentional exceptions: `git commit -m "feat: X [GUARD:ALLOW-DELETE]"`

---

## Commit Format

```
type(scope): description

feat: add user authentication
fix: resolve CVE in requests library
refactor: simplify manifest validation
docs: update architecture diagram for new service
```

---

## Stack Declaration

Your stack must be declared in `.raven/manifest.json` with a `raven_version` field.
Run `raven_status` to verify it is loaded and up to date.

---

## Audit Trail

Every Raven action is logged to `.raven/audit/audit.log`.
Every HITL PROPOSAL and response is logged to `.raven/memory/`.
Run `raven_audit` to view the log.

---

## Approval Flow

For actions requiring approval:
1. Raven warns — does not block immediately
2. Approval request logged + email to shared inbox (if `manifest.secrets.json` present)
3. PR created for manifest update
4. Approved → action allowed → audit logged
5. Rejected → hard block → violation logged

---

*Raven v3.0 — HITL first. Specialist triads always. OODA continuous. Guardrails before you ship.*
