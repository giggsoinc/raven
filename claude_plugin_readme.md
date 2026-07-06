# Raven — Claude Enterprise Plugin Installation Guide

## Overview

Raven is a Claude Code plugin that installs engineering discipline into every Claude session:
61 skills · 10 guard agents · 12 slash commands · dynamic expert generation.

Raven is **not** listed in an Anthropic-hosted plugin marketplace — you install from a local copy, not `claude plugin install giggsoinc/raven`.

---

## Install — 3 Ways

1. **Clone + local path (CLI, per developer)** — `git clone https://github.com/giggsoinc/raven.git && claude plugin install ./raven/plugin`
2. **Download zip + upload (Enterprise admin)** — download `raven-plugin.zip` from [releases](https://github.com/giggsoinc/raven/releases/latest), upload via `Settings → Integrations → Plugins → Upload Plugin`, then enable for your org
3. **Managed deployment (IT/Admin, org-wide)** — push a `managed-settings.json` pointing at the cloned/extracted plugin path to every machine (see below)

---

## Option 1 — Claude Code CLI (Per Developer)

```bash
git clone https://github.com/giggsoinc/raven.git
claude plugin install ./raven/plugin
```

Or download `raven-plugin-v4.1.0.zip` from the [latest release](https://github.com/giggsoinc/raven/releases/latest), unzip it, and point `claude plugin install` at the extracted `plugin/` folder.

---

## Option 2 — Claude Enterprise Admin Upload (Recommended for Orgs)

1. Download `raven-plugin.zip` from the [latest release](https://github.com/giggsoinc/raven/releases/latest)
2. Log in to your org's Claude Enterprise admin console
3. `Settings → Integrations → Plugins → Upload Plugin`
4. Upload the zip — the console validates it and adds it to your org's plugin library
5. Toggle **Enable for organisation** (or scope it to specific teams/roles)
6. Verify: ask Claude *"What Raven skills do you have available?"* — expect a list of 61 skills and 10 guard agents

---

## Option 3 — Enterprise-Wide Managed Deployment (IT/Admin)

For orgs that manage Claude Code config centrally via system policy. Deploy this file to every machine:

**macOS:** `/Library/Application Support/ClaudeCode/managed-settings.json`
**Windows:** `C:\ProgramData\ClaudeCode\managed-settings.json`

```json
{
  "plugins": ["/path/to/shared/raven/plugin"]
}
```

Point the path at a shared network/mounted location containing the cloned or extracted plugin — Claude Code reads this at startup and installs it automatically for every user on the machine.

---

## What Gets Installed

| Component | Count | What it does |
|---|---|---|
| Skills | 61 | Andie orchestration + specialists across DB, cloud, security, Salesforce, Odoo, AI/ML, Kafka, K8s, Terraform, and more |
| Guard agents | 10 | manifest-checker, stack-validator, style-enforcer, architecture-guard, db-guard, skill-guard, claude-mem, guard-git-watch, odoo-guard, salesforce-guard |
| Slash commands | 12 | `/raven-init` `/raven-harden` `/raven-debug` `/raven-incident` `/raven-registry-sync` and more |
| Dynamic specialist | 1 | Generates an expert profile on demand for any platform not yet curated — caches and promotes at 3 uses |
| Task-Observer | 1 | Silent session watcher — logs corrections, vulnerabilities, and patterns for weekly hardening |

---

## After Installing — Getting Started

The plugin gives Claude the skills and guards, but each **project** still needs a one-time setup pass to get hooks, engine scripts, and a manifest:

```bash
cd your-project
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh)   # global, once per machine
raven-setup                                                                            # per-project, run inside the repo
```

This installs `.raven/manifest.json`, `.claude/settings.json` (hooks), `.claude/scripts/`, and the git `pre-commit` hook. Then open the repo in Claude Code (`claude .`) — Andie is now your first responder for every prompt.

### Greenfield (new/empty repo)

- `raven-setup` scans the empty directory, finds no file signatures, and asks 1–3 quick questions (mode: solo/team/enterprise, primary language, cloud provider).
- Nothing to detect yet — the manifest is built entirely from your answers.
- Start working normally; Andie routes every request and the guards activate as soon as you write files.

### Brownfield (existing repo)

- `raven-setup` runs `sr-detect-workmode.py` first, which **does** scan the directory and auto-classifies the work type (code / infra / data / docs / salesforce / odoo / mixed) from file signatures (e.g. `sfdx-project.json`, `.tf` files, `dbt_project.yml`).
- **Known limitation:** that detection only sets the *work mode/platform* label. It does **not** inspect `package.json`, `requirements.txt`, `go.mod`, etc. to auto-fill the manifest's actual stack fields — you're still asked to manually pick languages, databases, and cloud provider via the prompts, even though that information already exists in the repo. Expect to answer those questions yourself on a brownfield import.
- If a `.raven/manifest.json` already exists, setup skips straight to "already configured" — safe to re-run.

---

## Keeping Raven Up to Date

New releases: [github.com/giggsoinc/raven/releases](https://github.com/giggsoinc/raven/releases)

**CLI users (already cloned):** `cd` into your existing clone, `git pull`, then re-run `claude plugin install ./plugin` to reload the refreshed folder — no need to re-clone. There is no registry to `update` against, so `claude plugin update raven` will not work.

**CLI users (only have the zip):** download the newer `raven-plugin.zip`, unzip over (or replace) the old one, then `claude plugin install /path/to/raven/plugin` again.

**Enterprise upload users:** download the new `raven-plugin.zip` and re-upload via the admin console.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Plugin validation failed — YAML error | Download the latest release ZIP — older ZIPs may have stale frontmatter |
| Duplicate agent name error | Same as above — get the latest release |
| Skills not appearing after install | Restart Claude Code and start a new session |
| Guard agents not firing | Run the one-time project setup (`raven-setup`) to install hooks |
| `/raven-init` not found | Plugin not installed — clone/download the repo and run `claude plugin install /path/to/raven/plugin` |
| Brownfield manifest has wrong/empty stack fields | Expected — re-run `raven-setup` and answer the language/db/cloud prompts manually; detection doesn't auto-fill these yet |

---

## Support

- Issues: [github.com/giggsoinc/raven/issues](https://github.com/giggsoinc/raven/issues)
- Releases: [github.com/giggsoinc/raven/releases](https://github.com/giggsoinc/raven/releases)
- Architecture: [raven-architecture.html](https://htmlpreview.github.io/?https://github.com/giggsoinc/raven/blob/main/docs/raven-architecture.html)
