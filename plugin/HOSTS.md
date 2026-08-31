# Raven 5.5.5 — one plugin, every host

There is **one** artifact: `plugin/raven-plugin-v5.5.5.zip`.
It is not Claude-Desktop-only. Claude’s marketplace loader (`.claude-plugin/`) is included because Claude Code uses it. Other hosts load the **same zip contents** via `install-host.sh` (copies `hosts/` + `scripts/` into the project).

| Host | What the zip installs | How you load it |
|---|---|---|
| Claude Code | `.claude-plugin/`, `skills/`, `agents/`, `commands/`, `settings.json` | `claude plugin install ./plugin` **or** unzip zip and `claude plugin install <extracted>` |
| Claude Desktop | same + `.claude-plugin/plugin.json` | Settings → Extensions → Add plugin → zip or folder |
| Grok | `hosts/AGENTS.md` → project `AGENTS.md` + `scripts/` | `bash install-host.sh /path/to/project` |
| Codex | same `AGENTS.md` | same |
| Cursor | `.cursor/rules/raven-router.mdc` + `AGENTS.md` | same |
| AntiGravity | `.agents/agents.md` (same contract as Codex/Grok). **Must** use `bash scripts/raven-python.sh …` not Anaconda `python3`. | same |
| Windsurf | `.windsurf/rules/ide-boot.md` | same |
| VS Code / Copilot | `.vscode/raven-router.md` + `.github/copilot-instructions.md` | same |
| Replit | `replit.md` | same |
| Gemini CLI | `GEMINI.md` | same |

After host glue is in the repo, every turn still runs:

```bash
python3 scripts/ops/raven-first.py --prompt "<user message>"
```

Fallback: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --prompt "<user message>"` (copies the engine into the app repo when `scripts/` is missing). That is what fills dashboard Logs. Hosts without Claude PreToolUse (Grok/Codex/Cursor) will skip Logs if the agent skips that command.

**Not claimed:** a native Antigravity/Cursor “upload zip in their marketplace UI” that we have not implemented. 5.5 ships **files those hosts already read** (`AGENTS.md`, `.cursor/rules`, `.agents/agents.md`, …).
