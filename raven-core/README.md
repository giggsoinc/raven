# raven-core — Source of Truth

⚠️  **DO NOT DELETE FILES FROM THIS FOLDER.**

Every `.py` script here is the **only real copy** of that engine script.
All other locations (`core/scripts/`, `plugin/scripts/`, `.claude/scripts/`)
are symlinks pointing here. Deleting a file here silently breaks all of them.

## Rule

> Edit scripts here → changes propagate everywhere automatically.
> Never edit scripts in any other location — you will be editing a symlink target anyway.

## Files

| Script | Hook event | Purpose |
|---|---|---|
| `cve-check.py` | pre-commit + UserPromptSubmit | Three-tier CVE gate — PyPI + GPT deep scan |
| `secret-scan.py` | PostToolUse Write/Edit + pre-commit | 11-pattern secret scanner — warns on write, hard blocks at commit |
| `schema-guard.py` | PreToolUse Bash | Blocks DROP TABLE / TRUNCATE / DELETE without WHERE — hard block |
| `cve-prompt-guard.py` | UserPromptSubmit | Detects install intent, injects CVE reminder before Claude responds |
| `audit-log.py` | PostToolUse + Stop | Encrypted audit trail → S3/GCS/Azure/OCI |
| `emit-violation.py` | on violation | Violation signal emitter → Raven Hub |
| `db-guard.py` | PostToolUse Write/Edit | Inline SQL and raw query detector |
| `obsidian-log.py` | Stop | Three-layer session logger — AI summary + transcript parse + git state → RavenVault |
| `session-start.py` | SessionStart | Brownfield/greenfield detection + model discovery → injects context at session open |
| `server.py` | — | Raven MCP server (5 tools) |

## Setup (new install)

```bash
bash raven-core/symlink-init.sh
```

Run once after cloning. Creates symlinks in all target locations. Never copies files.

## If a symlink breaks

```bash
bash raven-core/symlink-init.sh
```

Same command repairs broken symlinks. It checks source files exist before touching anything.
