# raven-core — Source of Truth

⚠️  **DO NOT DELETE FILES FROM THIS FOLDER.**

Every `.py` script here is the **only real copy** of that engine script.
All other locations (`core/scripts/`, `plugin/scripts/`, `codex/scripts/`, `.claude/scripts/`)
are symlinks pointing here. Deleting a file here silently breaks all of them.

## Rule

> Edit scripts here → changes propagate everywhere automatically.
> Never edit scripts in any other location — you will be editing a symlink target anyway.

## Files

| Script | Purpose |
|---|---|
| `cve-check.py` | Three-tier CVE gate — PyPI + GPT deep scan |
| `secret-scan.py` | 11-pattern secret scanner — pre-commit hard block |
| `audit-log.py` | Encrypted audit trail → S3/GCS/Azure/OCI |
| `emit-violation.py` | Violation signal emitter → Raven Hub |
| `db-guard.py` | Inline SQL and raw query detector |
| `server.py` | Raven MCP server (5 tools) |

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
