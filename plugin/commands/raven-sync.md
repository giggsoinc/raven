---
name: raven-sync
description: Use when requirements.txt or pyproject.toml has changed and you
  want to sync all libraries into manifest.json. CVE checks each one.
  Approved libraries are auto-added. Blocked ones are flagged. Run after
  pip install or when onboarding a new project.
allowed-tools: Bash
---

# /raven-sync

Syncs all libraries from requirements files into manifest.json.

## Steps
1. Run: `python3 .claude/scripts/sync-libraries.py`
2. Show summary: approved / blocked / skipped
3. If blocked libs found — report to developer with reason
4. If all clean — confirm manifest.json updated

## Options
- `/raven-sync` — full sync with CVE check
- `/raven-sync --dry-run` — show what would change, don't write
- `/raven-sync --no-cve` — skip CVE check, approve all found libs

## When to run
- After pip install of new libraries
- When onboarding existing project to Raven
- After pulling a branch with new dependencies
