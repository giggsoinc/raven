<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# Raven v4.1.0

**AI-native engineering discipline for Claude Code · GitHub Copilot · OpenAI Codex**

Raven is a **governance + orchestration layer** for AI-assisted coding. It routes prompts to the right specialist, documents decisions with a Triad panel, and gates commits with security scanning (secrets + CVEs). Built for teams shipping fast *and* safely.

---

## TL;DR — What Raven Does

- **Brownfield Fast-Triage** (andie-jr): 2-round debug flow for broken systems — problem → root cause → fix → why → audit.
- **Architecture Panel** (Andie): Functional + Technical + Data perspectives on design decisions. Every rec is a proposal you approve/modify/reject.
- **Commit-time Security**: Hard-block secrets (API keys, tokens) and critical CVEs (CVSS >7) before they land in Git.
- **61 Domain Skills** + **7 Guard Agents** + **cross-session memory**: Routing, style enforcement, DB patterns, infrastructure rules, secrets management.

---

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

## Features by Version

### **Raven v4.1.0** (Current) — Privacy + Routing Hardening

**New:**
- Privacy hardening: Changelog cleared from manifest, personal emails replaced with org email across all registries.
- **Critical routing fix**: Deterministic repo-state logic replaces regex classification. Brownfield →andie-jr, greenfield → Andie, data questions → direct. Fixes misclassification of debug as new-work.

**Maintained from v4.0:**
- Andie Drama mode (3-panelist debate on tradeoffs)
- Andie-jr fast triage (2-round root-cause flow)
- 61 domain skills (ML, Salesforce, Odoo, K8s, Terraform, etc.)
- Commit-time secret + CVE scanning
- Cross-session memory (`.raven/memory/`)
- SMTP + Slack notifications

### **Raven v4.0.0** — Honesty Pass + First Release

- Rewritten README: no false claims, honest ROI section, per-persona messaging.
- Verified 61 skills (corrected from earlier miscount).
- CLAUDE.md per-turn discipline contract at top; Raven/Lucky gate; real hook names.
- First onboarding in Andie: brownfield self-detect vs greenfield setup (≤2 questions).
- `/andie` + `/andie-jr` force-path commands; plugin now bundles 12 commands.
- `notify.py`: real SMTP + Slack wired into pre-commit.
- `install-claudemd.py`: append-only CLAUDE.md installer (never deletes user content).
- Session-start transparency banner.

### **Previous Versions**

See [CHANGELOG.md](CHANGELOG.md) for v3.x and earlier.

### Upgrade Path

- **v4.0 → v4.1**: Drop-in replacement. Run `/raven-sync` to sync manifests; no config changes needed.
- **v3.x → v4.0+**: Not backward-compatible. See migration guide in CONTRIBUTING.md.

---

## Installation

### 🖥️ **Claude Desktop** (most people)

1. Download [`raven-plugin-v4.1.0.zip`](plugin/raven-plugin-v4.1.0.zip)
2. Open Claude Desktop → Settings → Extensions → Add plugin
3. Drop the ZIP file
4. Restart Claude Desktop (~90 sec)

### 🔧 **Development / Local Setup**

```bash
git clone https://github.com/giggsoinc/raven.git
cd raven
bash plugin/make-plugin.sh
# → produces `plugin/raven-plugin-v4.1.0.zip`
# Upload this ZIP to Claude Desktop via Settings → Extensions
```

### ✅ Verify Install

After install, start a new Claude Code session and you should see:

```
🪶 Raven ✅  |  raven  |  python3.13
Andie is your discipline layer. What are you working on?
```

If you see Raven greeting → install worked. If no greeting → check plugin path in Claude Desktop settings.

---

## Contributing

Raven is MIT licensed. Contributions welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- How to add a skill
- How to write a guard agent
- Style standards (Giggso code style — type hints, docstrings, logging, ≤200 LOC per file)
- Pre-commit hook requirements

---

## Support & Issues

- **Bug reports**: [GitHub Issues](https://github.com/giggsoinc/raven/issues)
- **Questions**: Start a discussion in [GitHub Discussions](https://github.com/giggsoinc/raven/discussions)
- **Security vulnerabilities**: Email `rv@giggso.com` (do not open public issue)

---

<p align="center">
  <strong>Built by <a href="https://giggso.com">Giggso</a> · <a href="https://github.com/giggsoinc/raven">GitHub</a> · MIT License</strong>
</p>

*Raven v4.1.0 — Governance for AI coding at the speed of thought.*
