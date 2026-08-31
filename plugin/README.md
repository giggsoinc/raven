# Raven Plugin — v5.5.5

**One plugin.** File: `raven-plugin-v5.5.5.zip` (built by `bash plugin/make-plugin.sh`).

Not Claude-Desktop-only. The zip contains Claude’s `.claude-plugin/` loader **and** `hosts/` + `install-host.sh` for Grok, Codex, Cursor, AntiGravity, Windsurf, Replit, and Gemini CLI. Details: [HOSTS.md](HOSTS.md).

## Install

**Claude Code**

```bash
git clone https://github.com/giggsoinc/raven.git
claude plugin install ./raven/plugin
```

Or unzip `raven-plugin-v5.5.5.zip` and `claude plugin install /path/to/extracted`.

**Claude Desktop:** Settings → Extensions → Add plugin → drop the zip.

**Grok / Codex / Cursor / AntiGravity / Windsurf / Replit / Gemini**

```bash
unzip raven-plugin-v5.5.5.zip -d raven-plugin
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
