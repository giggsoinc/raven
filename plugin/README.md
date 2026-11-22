# Raven Plugin — v6.1.3

**One current plugin.** File: `raven-plugin-v6.1.3.zip` (built by `bash plugin/make-plugin.sh`, ideally from a clean clone so uncommitted skills are not packed). The previous zip in this folder is `raven-plugin-v6.1.2.zip`. Older plugin zips are in `version.archive.zip`. Do not install from the archive or from an `_old` zip.

**This folder is not a plugin root.** The plugin root is the repository root (`.claude-plugin/marketplace.json`, `source: "./"`). `plugin/scripts/*` are symlinks to `../../raven-core/` and `../../scripts/`, so they only resolve inside a full checkout.

Not Claude-Desktop-only. The zip contains Claude’s `.claude-plugin/` loader **and** `hosts/` + `install-host.sh` for Grok, Codex, Cursor, AntiGravity, Windsurf, Replit, and Gemini CLI. Details: [HOSTS.md](HOSTS.md).

## Install

**Claude Code**

```bash
claude plugin marketplace add giggsoinc/raven
claude plugin install raven@raven
```

Or unzip `raven-plugin-v6.1.3.zip` and `claude plugin install /path/to/extracted`. The zip has real files only (no symlinks) and does not include the MCP server.

**Claude Desktop:** Settings → Extensions → Add plugin → drop the zip.

**Grok / Codex / Cursor / AntiGravity / Windsurf / Replit / Gemini**

```bash
unzip raven-plugin-v6.1.3.zip -d raven-plugin
bash raven-plugin/install-host.sh /path/to/your-project
```

That copies `AGENTS.md` / `.cursor/rules` / `.agents/agents.md` / `GEMINI.md` / `replit.md` / `scripts/` as required. There is no second zip.

Then in a project: `/raven-init` (Claude) or copy `.raven/manifest.json` from the engine repo.

## What you can do with this plugin

| You want to | Command / path |
|---|---|
| Plan | Andie (`/andie`) |
| Debug | Andie-Jr (`/andie-jr`) |
| Route + cost toast | `scripts/routing/model-router.py` |
| Spend (local calc) | Dashboard Costs, `/run-costs` |
| Graph | `scripts/dashboard` OKF |
| Init a project | `/raven-init` |
| Other IDEs | `bash install-host.sh <project>` |

`#comprehension_debt` `#ai_coding` `#claude_code` `#grok` `#codex` `#discipline_engine` `#token_cost`
