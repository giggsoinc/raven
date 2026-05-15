<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# Raven

> Claude Code implementation of the Raven AI coding discipline engine.
> Part of the [Raven platform](https://github.com/giggsoinc/raven-core). MIT License.
> Built by [Giggso Inc](https://github.com/giggsoinc).

*Guardrails before you ship.*

## Install — One Command

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash
```

Then from **any project directory**:
```bash
cd YourProject && raven-setup
```

That's it. Two commands. No zip. No path hunting.

---

## What It Does

Enforces consistent coding standards, stack discipline, and production safety across distributed dev teams — without killing developer productivity.

| During coding | At git commit | At CI/CD |
|---|---|---|
| Agents advise | Pre-commit hook blocks | Pipeline validates |
| Skills guide | CVE check fires | Thin trigger only |
| No hard blocks | All violations caught | Last safety net |

---

## Components

### Core Agents — `.claude/agents/`

| Agent | Fires On | Action |
|---|---|---|
| manifest-checker | Every action | Hard block if manifest missing |
| style-enforcer | File edit | Advise during coding, block at commit |
| stack-validator | Import detected | CVE check, approval flow |
| architecture-guard | New file | Warn → 24h grace → block |
| claude-mem | PreCompact | Save session state, macOS toaster |

### Skills — `.claude/skills/`

Progressive disclosure — ~100 tokens at startup, rules load only when triggered.

**Core skills:** raven-core · raven-expert · raven-plan · raven-review · raven-security · raven-refactor · raven-test · raven-document · andie

**Specialist skills (23):** aws · gcp · azure · oci · kafka · postgres · redis · k8s · terraform · fastapi · nicegui · vault · security · aiml · dataeng · devops · bigdata · vector-db · dynamic · odoo · salesforce · log-management · agent-chaining

### Commands — `.claude/commands/`

| Command | Does |
|---|---|
| `/raven-scaffold` | Plan before code — dependency map + file structure |
| `/raven-approve {lib}` | Architect approves library request |
| `/raven-debug` | Full boot diagnostic |
| `/raven-mem` | Save session state before context reset |
| `/raven-sync` | Sync requirements.txt → manifest |

### Scripts — `.claude/scripts/`

| Script | Does |
|---|---|
| `cve-check.py` | Three-tier CVE — PyPI Safety + gpt-5.5 |
| `secret-scan.py` | Detects API keys, passwords, tokens in staged files |
| `sync-libraries.py` | Auto-discovers libs from requirements.txt |
| `token-guard.py` | PreCompact warning + session backup |
| `audit-log.py` | Encrypted audit → S3 / GCS / Azure / OCI |

### Pre-commit Hook — `.git/hooks/pre-commit`

5 checks — any failure = hard block:
1. Framework repo detection (skip if `.raven-framework` present)
2. Manifest valid
3. Secrets not staged
4. CVE check on all imports
5. Style violations (print, lines, type hints)

---

## Library Approval — Three Tiers

| Tier | Condition | Result |
|---|---|---|
| 1 | Org whitelist | Auto-approved, zero friction |
| 2 | Category whitelist | Auto-approved, zero friction |
| 3 | Unknown | Approval flow → Prism7 → PR |
| 3 | CVE CVSS >7 | Hard block, no override |

---

## MCP Plugin

```bash
# Install as Claude Code MCP plugin
claude mcp add raven -- python3 ~/.raven/mcp/server.py
```

Tools: `raven_status` · `raven_cve_check` · `raven_sync_libs` · `raven_debug` · `raven_violation`

---

## Works Alongside

```
Superpowers → dev methodology (TDD, planning, review)
GSD         → context management (long sessions)
Raven       → governance + security layer

All three stack. No conflicts.
```

---

## Install

```bash
cd YourProject
bash ../raven/raven-setup.sh
```

See [HOW-TO-USE.md](HOW-TO-USE.md) for full enterprise guide.

---

## Companion Repo

[giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) — Production protection.
Git watch · DB watch · Infra watch · Firewall watch · Incident management.
Install after Raven Core.

---

## License

MIT — [Giggso](https://giggso.com)
