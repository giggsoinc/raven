# Raven — Claude Enterprise Plugin Installation Guide

## Overview

Raven is a Claude Code plugin that installs engineering discipline into every Claude session:
33 specialist skills · 10 guard agents · 10 slash commands · dynamic expert generation.

There are three ways to install Raven depending on your setup.

---

## Option 1 — Claude Code CLI (Per Developer)

For individual developers or small teams where each person installs themselves.

```bash
claude plugin install giggsoinc/raven
```

That's it. Claude Code fetches the plugin directly from GitHub.

---

## Option 2 — Claude Enterprise Admin Upload (Recommended for Orgs)

For organisations using Claude Enterprise where an admin controls which plugins are available.

### Step 1 — Download the plugin ZIP

Go to the latest release:
```
https://github.com/giggsoinc/raven/releases/latest
```
Download `raven-plugin.zip`.

### Step 2 — Log in to Claude Enterprise admin console

Go to your organisation's Claude Enterprise URL and sign in as an admin.

### Step 3 — Navigate to Plugins

```
Settings → Integrations → Plugins → Upload Plugin
```

### Step 4 — Upload the ZIP

Click **Upload Plugin** and select `raven-plugin.zip`.

The console will validate the plugin. If validation passes, the plugin appears in your org's plugin library.

### Step 5 — Enable for your org

Toggle **Enable for organisation** to make Raven available to all members.
Or assign it to specific teams or roles if your console supports scoped access.

### Step 6 — Verify

Ask Claude: *"What Raven skills do you have available?"*
Expected response: lists the 33 specialists and 10 guard agents.

---

## Option 3 — Enterprise-Wide Managed Deployment (IT/Admin)

For organisations that manage Claude Code configuration centrally via system policy.

Deploy this file to all machines:

**macOS:** `/Library/Application Support/ClaudeCode/managed-settings.json`
**Windows:** `C:\ProgramData\ClaudeCode\managed-settings.json`

```json
{
  "plugins": ["giggsoinc/raven"]
}
```

Claude Code reads this at startup and installs the plugin automatically for every user on the machine.

---

## What Gets Installed

| Component | Count | What it does |
|---|---|---|
| Specialist skills | 33 | Expert-level guidance per platform — DB, cloud, security, Salesforce, Odoo, AI/ML, Kafka, K8s, Terraform and more |
| Guard agents | 10 | Always-on discipline — blocks inline SQL, secrets, undeclared stacks, fat triggers, missing architecture |
| Slash commands | 10 | `/raven-init` `/raven-harden` `/raven-debug` `/raven-incident` `/raven-registry-sync` and more |
| Dynamic specialist | 1 | Generates an expert profile on demand for any platform not yet curated — caches and promotes at 3 uses |
| Task-Observer | 1 | Silent session watcher — logs corrections, vulnerabilities, and patterns for weekly hardening |

---

## One-Time Project Setup (Per Project)

The plugin gives Claude the skills and guards. To also install hooks, engine scripts, and your project manifest:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh)
```

This runs once per project. It installs:
- `.raven/manifest.json` — your project config
- `.claude/settings.json` — hooks (PreToolUse, PostEdit, PreCommit)
- `.claude/scripts/` — engine scripts (CVE check, secret scan, db-guard, audit log)
- `.git/hooks/pre-commit` — commit gate

---

## Keeping Raven Up to Date

New releases are published at:
```
https://github.com/giggsoinc/raven/releases
```

**CLI users:** `claude plugin update raven`

**Enterprise upload users:** download the new `raven-plugin.zip` from the latest release and re-upload via the admin console.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Plugin validation failed — YAML error | Download the latest release ZIP — older ZIPs may have stale frontmatter |
| Duplicate agent name error | Same as above — get the latest release |
| Skills not appearing after install | Restart Claude Code and start a new session |
| Guard agents not firing | Run the one-time project setup to install hooks |
| `/raven-init` not found | Plugin not installed — run `claude plugin install giggsoinc/raven` |

---

## Support

- Issues: [github.com/giggsoinc/raven/issues](https://github.com/giggsoinc/raven/issues)
- Releases: [github.com/giggsoinc/raven/releases](https://github.com/giggsoinc/raven/releases)
- Architecture: [raven-architecture.html](https://htmlpreview.github.io/?https://github.com/giggsoinc/raven/blob/main/docs/raven-architecture.html)
