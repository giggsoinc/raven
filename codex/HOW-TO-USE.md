<p align="center">
  <img src="../assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# How to Use Raven for Codex — v2.8

> OpenAI Codex implementation of the Raven AI coding discipline engine.
> Part of the [Raven platform](https://github.com/giggsoinc/raven). MIT License.
> Built by [Giggso Inc](https://github.com/giggsoinc).

*Guardrails before you ship.*

---

## What This Does

Raven brings enterprise coding discipline to OpenAI Codex. Two layers of protection:

| Layer | Where | When |
|---|---|---|
| **AGENTS.md** | In your repo | Before every Codex task — rules Codex reads first |
| **MCP tools** | In Codex session | During coding — CVE check, secret scan, audit log |
| **PR gate** | In GitHub CI | On every PR — catches anything that slipped through |

No layer relies on the others. If a developer skips the MCP tools, the PR gate still runs. That's the point.

---

## Prerequisites

| Requirement | Check |
|---|---|
| OpenAI account (Pro / Enterprise / Business) | [platform.openai.com](https://platform.openai.com) |
| Codex access | [chatgpt.com/codex](https://chatgpt.com/codex) |
| Python 3.10+ | `python3 --version` |
| Git | `git --version` |
| OpenAI API key | Optional — enables GPT-4o CVE deep scan |

---

## Install — One Command

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/codex/install.sh | bash
```

This:
1. Clones `giggsoinc/raven` and copies the `codex/` folder to `~/.raven-codex/`
2. Installs Python dependencies (`openai`, `requests`, `packaging`)
3. Registers the MCP server in `~/.codex/config.toml`
4. Adds `raven-codex-setup` alias to your shell profile

---

## Setup — Per Project

Run once in each project you want Raven to protect:

```bash
cd YourProject && raven-codex-setup
```

Answers 5 questions:

| Question | Notes |
|---|---|
| Project name | Used in manifest and audit log |
| Your email | Audit trail — stored locally only |
| Stack | python / node / go / java / ruby / other |
| Cloud | aws / gcp / azure / oci / none |
| OpenAI API key | Blank = PyPI Safety only (still catches most CVEs) |

---

## What Gets Created

```
YourProject/
├── AGENTS.md                    ← Raven rules — Codex reads this before every task
└── .raven/
    ├── manifest.json            ← Project config (commit this)
    ├── .env.template            ← Copy to .env, fill in keys (never commit .env)
    └── audit/
        └── audit.log            ← Encrypted audit trail (never commit)
```

**Plus in `~/.codex/config.toml`:**
```toml
[mcp_servers.raven]
command = "python3"
args    = ["/Users/YOU/.raven-codex/mcp/server.py"]
```

---

## AGENTS.md — Codex Reads This First

Codex reads `AGENTS.md` before every task. Raven's `AGENTS.md` tells Codex:
- Never hardcode secrets
- Run CVE check before adding any library
- No force push, no DROP TABLE, no open firewall rules
- Stack and commit format rules

You can extend it. Add project-specific rules at the bottom. Codex will follow them.

---

## MCP Tools — Available in Every Codex Session

Once the MCP server is registered, these tools are available in every Codex task:

| Tool | What It Does | When to Use |
|---|---|---|
| `raven_status` | Check manifest is loaded, version, mode | Start of any session |
| `raven_cve_check` | CVE scan a library before adding it | Before any `pip install` or `npm install` |
| `raven_sync_libs` | Sync requirements.txt → manifest | After adding libraries |
| `raven_debug` | Full project health check | When something seems wrong |
| `raven_violation` | Emit a manual violation to audit log | When you spot something Raven missed |

**Verify MCP is active:**
```
In Codex: "Run raven_status"
Expected: ✅ manifest.json loaded · stack declared · version 2.8 · mode active
```

---

## CVE Check — Three Tiers

Before adding any library, ask Codex:
```
Run raven_cve_check on requests
```

| Tier | Result | Action |
|---|---|---|
| 1 — Org whitelist | Auto-approved | Zero friction |
| 2 — Category whitelist | Auto-approved | Zero friction |
| 3 — Clean | No CVE found | Approval flow |
| 3 — Medium | CVE CVSS 4–7 | Warn + log + suggest safe version |
| 3 — Critical | CVE CVSS >7 | Hard block — do not install |

Engines: PyPI Safety (fast, always) + GPT-4o deep scan (requires API key).
Node.js projects: runs `npm audit` automatically when `package.json` is detected.

---

## PR Gate — Automatic on Every PR

Add to your repo once. Never think about it again.

Create `.github/workflows/raven.yml`:

```yaml
name: Raven Discipline Check
on: [pull_request]

jobs:
  raven:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: giggsoinc/raven-action@main
        with:
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
          manifest-path: .raven/manifest.json
```

Every PR gets a visible status check:
```
✅ raven/discipline-check — passed
🔴 raven/discipline-check — blocked (CVE: requests 2.6.0 CVSS 9.8)
⚠️ raven/discipline-check — did not run (manifest missing)
```

This runs on **every PR regardless of who wrote the code** — Codex, Claude Code, humans, anyone.

---

## Daily Developer Flow

```
Codex task starts
      ↓
Codex reads AGENTS.md — rules loaded
      ↓
Dev adds a library
      ↓
Codex runs raven_cve_check → ✅ clean or 🔴 blocked
      ↓
Code written → Codex commits
      ↓
PR opened → raven-action fires:
  ✅ Secrets clean  ✅ CVE clean  ✅ Manifest valid
      ↓
PR merges — audit log written
```

---

## Add Production Guard (optional)

For hard blocks on destructive operations (DROP TABLE, force push, open firewall):

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/guard/codex/install.sh | bash
cd YourProject && raven-guard-codex-setup
```

Requires Raven Codex installed first.

---

## File Reference

| File | Commit? | Who Edits |
|---|---|---|
| `AGENTS.md` | ✅ | Architects |
| `.raven/manifest.json` | ✅ | Architects |
| `.raven/.env.template` | ✅ | Architects |
| `.raven/.env` | ❌ Never | Each developer locally |
| `.raven/audit/audit.log` | ❌ Never | Written by Raven |
| `.github/workflows/raven.yml` | ✅ | DevOps / architects |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `raven_status` returns error | Check `~/.codex/config.toml` has `[mcp_servers.raven]` entry |
| MCP not showing in Codex | Re-run `raven-codex-setup` — it writes `config.toml` automatically |
| CVE check not firing | Verify `OPENAI_API_KEY` is set in `.raven/.env` |
| PR gate not showing | Check GitHub Actions is enabled on the repo |
| Manifest missing | Re-run `raven-codex-setup` in your project directory |
| Audit log empty | Check write permissions on `.raven/audit/` |

---

## Updating Raven

```bash
cd ~/.raven-codex && git pull
```

Or reinstall cleanly:
```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/codex/install.sh | bash
```

---

## Platform Comparison

| | Claude Code | OpenAI Codex |
|---|---|---|
| Rules file | `CLAUDE.md` | `AGENTS.md` |
| Enforcement point | Pre-commit hook | PR gate + AGENTS.md |
| MCP config | `claude mcp add` | `~/.codex/config.toml` |
| CVE scan | On import detected | On library add + on PR |
| Secret scan | On file save | On PR open |
| Setup command | `raven-setup` | `raven-codex-setup` |
| Install dir | `~/.raven/` | `~/.raven-codex/` |
| Engine | [raven/raven-core](https://github.com/giggsoinc/raven/tree/main/raven-core) | [raven/raven-core](https://github.com/giggsoinc/raven/tree/main/raven-core) |

---

*Raven v2.8 — MIT — [github.com/giggsoinc/raven](https://github.com/giggsoinc/raven)*
