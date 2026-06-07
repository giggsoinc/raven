# Raven Plugin — v4.1.0

Upload this folder via Claude Desktop to install Raven as a plugin.

## How to install

1. Clone or download [giggsoinc/raven](https://github.com/giggsoinc/raven)
2. Open **Claude Desktop → Settings → Extensions → Add plugin**
3. Upload `raven-plugin-v4.1.0.zip` — or select the `raven/plugin/` folder directly
4. Done — 61 skills and 10 guard agents load automatically

## What's included

- **61 skills** — Andie v6.3 with mode splitting, 6 Kaizen methods, Guru, capability routing. All domain specialists including ML, Graph DB, Workflow, MLOps. Raven core skills.
- **10 guard agents** — manifest-checker, stack-validator, style-enforcer, architecture-guard, db-guard, skill-guard, claude-mem, guard-git-watch, odoo-guard, salesforce-guard
- **10 slash commands** — /raven-debug, /raven-review, /raven-approve, /raven-harden, /raven-incident, and more
- **Scripts** — CVE check, secret scan, audit log, work-mode detection

## What's new in v4.0.0 (major)

- **Honesty pass** — docs now match code: event-driven guards (not "always-on"),
  previous-session token meter, cross-session memory (not "token reduction"),
  verified **61 skills** (was mislabelled 60/46/55).
- **Onboarding fork** — Andie greets with Tour / Setup / Guru on first install.
- **Force-path commands** — `/andie` + `/andie-jr`; the plugin now bundles **12 commands**
  (previous versions shipped none).
- **Notifications** — `notify.py` SMTP + Slack at commit; `install-claudemd.py` safe installer.
- **Plain-English guards** — help-toned messages with remediation, not "VIOLATION".
- 61 skills · 10 guard agents · 15 scripts.

## Previously — v4.0.0

- **Andie v6.3** — mode splitting (-56% per-message tokens), 6 Kaizen methods, Guru explainer, capability routing
- **4 Tier 1 specialists** — ml-specialist, graph-db-specialist, workflow-specialist, ml-ops-specialist
- **Domain packs** — agent-frameworks, local-dev (loaded by dynamic-specialist)
- **Oracle version matrix** — 19c/21c/23ai capability awareness
- **Docker-compose patterns** — local dev support in devops-specialist

## Update

Re-download the repo and re-upload `raven-plugin-v4.1.0.zip` — or pull latest and re-select the folder.
