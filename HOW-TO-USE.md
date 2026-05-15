<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# How to Use Raven — v2.8

> Claude Code implementation of the Raven AI coding discipline engine.
> Part of the [Raven platform](https://github.com/giggsoinc/raven-core). MIT License.
> Built by [Giggso Inc](https://github.com/giggsoinc).

*Guardrails before you ship.*

---

## Two Repos — Two Audiences

| Repo | Audience | Job |
|---|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) (Core) | Developers | Coding discipline |
| [giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) | DevOps / Architects | Production protection |

---

## Prerequisites

| Requirement | Check |
|---|---|
| Claude Code | `claude --version` |
| Git | `git --version` |
| Python 3.10+ | `python3 --version` |
| OpenAI API key | Optional — enables gpt-5.5 CVE deep scan |

---

## Install — One Command

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/install.sh | bash
```

This clones Raven to `~/.raven/` and makes `raven-setup` available globally.

Then from **any project directory**:

```bash
cd YourProject && raven-setup
```

### Manual install (no curl)

```bash
git clone https://github.com/giggsoinc/raven.git ~/.raven
cd YourProject
bash ~/.raven/raven-setup.sh
```

---

## Setup — 7 Questions

| Question | Notes |
|---|---|
| Project name | Letters, numbers, hyphens |
| Your email | Audit trail |
| Language(s) | Pick numbers or type freely (`python3.13`) |
| Cloud | Number or freeform |
| Database(s) | Multi-select — `1,3` |
| Shared inbox | Prism7 approval email |
| Escalation email | P1 incidents |
| OpenAI API key | Blank = PyPI Safety only (still works) |

---

## What Gets Created

```
YourProject/
├── CLAUDE.md
├── .claude/
│   ├── settings.json                      ← Hooks: PreToolUse, PostToolUse, PreCompact
│   ├── agents/                            ← 5 Core agents
│   ├── skills/
│   │   ├── raven-core/                    ← Progressive disclosure (~100 tokens at startup)
│   │   │   ├── SKILL.md
│   │   │   └── rules/                    ← Loaded only when triggered
│   │   │       ├── stack.md
│   │   │       ├── style.md
│   │   │       ├── architecture.md
│   │   │       └── commit.md
│   │   ├── raven-expert/                   ← L99 deep expertise mode
│   │   ├── raven-plan/                     ← Architecture-first planning
│   │   ├── raven-review/                   ← Manifest-aware code review
│   │   ├── raven-security/                 ← Threat model + CVE analysis
│   │   ├── raven-refactor/                 ← Style enforcement
│   │   ├── raven-test/                     ← Test-first discipline
│   │   ├── raven-document/                 ← Doc enforcement
│   │   ├── andie/                         ← Multi-modal AI expert (4 modes)
│   │   └── [23 specialist skills]/        ← aws gcp azure oci kafka postgres odoo salesforce log-management agent-chaining ...
│   ├── commands/                          ← /raven-scaffold /raven-debug /raven-approve ...
│   ├── scripts/                           ← cve-check.py secret-scan.py audit-log.py ...
│   └── mcp/server.py                      ← MCP plugin server (5 tools)
├── .git/hooks/pre-commit
└── .raven/
    ├── manifest.json                      ← Public config (Git tracked)
    ├── manifest.secrets.json              ← NEVER commit
    ├── architecture.md                    ← Living diagram template
    └── ci/                               ← github-actions.yml gitlab-ci.yml on-prem-pipeline.sh
```

---

## Hooks — Always On

Raven registers 4 hooks in `.claude/settings.json` automatically:

| Hook | Fires | Action |
|---|---|---|
| `PreToolUse` | Before any Claude tool | `tool-guard.py` — blocks restricted actions |
| `PostToolUse` | After every tool | `audit-log.py` — encrypted log to S3/GCS/Azure/OCI (async) |
| `PreCompact` | Before context compacts | `token-guard.py` — session backup + macOS notification |
| `Notification` | Claude session events | `token-guard.py` (async) |

---

## Skills — Progressive Disclosure

Only metadata loads at startup (~100 tokens per skill). Rules load only when triggered.

```
Session starts → raven-core SKILL.md scanned (~100 tokens)

Dev adds: import pandas
      ↓
Claude loads rules/stack.md
rules/stack.md reads live manifest: !`cat .raven/manifest.json`
      ↓
Checks import → flags if not in approved libraries
rules/style.md, rules/architecture.md → untouched (zero tokens wasted)
```

**Routing table** (raven-core detects intent and routes):

| Prompt contains... | Routes to |
|---|---|
| `"expert"` / `"deep dive"` / `"L99"` | `raven-expert` |
| `"security"` / `"CVE"` / `"threat"` | `raven-security` |
| `"plan"` / `"architecture"` / `"scaffold"` | `raven-plan` + `/raven-scaffold` |
| `"review"` / `"PR"` | `raven-review` |
| `"refactor"` / `"clean"` | `raven-refactor` |
| `"test"` / `"coverage"` | `raven-test` |
| `"document"` / `"README"` | `raven-document` |
| `"drama"` / `"debate"` / `"stress-test"` | `andie` Drama Mode |
| new `import X` in code | CVE check via `cve-check.py` |
| `"commit"` / `"push"` | Pre-commit gate — all 5 checks fire |

---

## Slash Commands

| Command | Use When |
|---|---|
| `/raven-scaffold` | Starting a new feature — forces plan before code |
| `/raven-debug` | Something not working — full boot diagnostic |
| `/raven-approve {lib} {version}` | Architect approves a library request |
| `/raven-incident {p1\|p2\|p3} {description}` | Manual incident creation |
| `/raven-sync` | Sync requirements.txt → manifest libraries |
| `/raven-search {query}` | Find a skill for a capability |
| `/raven-mem` | Save session state before context reset |

---

## Pre-commit Hook — 5 Checks

Every `git commit` runs all 5. Any failure = hard block.

| Check | What It Does |
|---|---|
| 1. Framework detection | Skips if `.raven-framework` present (Raven's own repos) |
| 2. Manifest valid | JSON valid, all required fields present |
| 3. Secrets not staged | No API keys, passwords, or tokens in staged files |
| 4. CVE check | Scans all imports — three-tier approval system |
| 5. Style check | Line count, print statements, type hints, docstrings |

---

## CVE Check — Three Tiers

| Tier | Condition | Action | Friction |
|---|---|---|---|
| 1 | Org whitelist (fastapi, httpx, boto3...) | Auto-approve | Zero |
| 2 | Category whitelist (HTTP clients, test libs) | Auto-approve | Zero |
| 3 Clean | Unknown, no CVE | Approval flow | Low |
| 3 Moderate | CVE CVSS 4–7 | Approval flow + warn | Medium |
| 3 Critical | CVE CVSS >7 | Hard block — no override | Full |

Engines: PyPI Safety DB (fast, always) + gpt-5.5 (deep, requires OpenAI key).

---

## MCP Plugin

```bash
claude mcp add raven -- python3 ~/.raven/mcp/server.py
```

MCP tools: `raven_status` · `raven_cve_check` · `raven_sync_libs` · `raven_debug` · `raven_violation`

---

## Enterprise Deploy (Zero-Click)

IT drops `managed-mcp.json` at the system path — every developer gets Raven auto-loaded:

| Platform | Path |
|---|---|
| macOS | `/Library/Application Support/ClaudeCode/managed-mcp.json` |
| Windows | `C:\ProgramData\ClaudeCode\managed-mcp.json` |
| Linux | `/etc/claude-code/managed-mcp.json` |

The `managed-mcp.json` in this repo is ready to deploy.

---

## Install Guard (architects / DevOps only)

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-guard/main/install.sh | bash
cd YourProject && raven-guard-setup
```

Requires Raven Core installed first.

---

## Developer Flow

```
Write code → agents advise, skills guide (no blocks during coding)
Add library → Tier 1/2: instant | Tier 3: email Prism7 + auto PR
git commit → pre-commit fires:
  ✅ Manifest  ✅ Secrets  ✅ CVE  ✅ Style  ✅ Guard → CLEARED or BLOCKED
git push → CI/CD thin check → merged
```

---

## CI/CD Setup

Copy from `.raven/ci/`:

| Platform | File | Destination |
|---|---|---|
| GitHub | `github-actions.yml` | `.github/workflows/raven.yml` |
| GitLab | `gitlab-ci.yml` | `.gitlab-ci.yml` |
| On-prem | `on-prem-pipeline.sh` | Add to Jenkins/Gitea pipeline |

---

## Open Claude Code

```bash
claude .
```

Then run `/raven-debug` to verify everything loaded:

```
✅ CLAUDE.md
✅ manifest.json valid
✅ 5 agents loaded
✅ Skills: raven-core + 8 core skills + 23 specialists
✅ pre-commit hook executable
✅ Hooks: PreToolUse PostToolUse PreCompact Notification
✅ CLEARED
```

---

## First Commit

```bash
git add .raven/manifest.json .raven/.gitignore \
        .raven/architecture.md CLAUDE.md .claude/
git commit -m "chore: init raven v2.8 [RAVEN:INIT]"
git push
```

---

## File Reference

| File | Commit? | Who Edits |
|---|---|---|
| `CLAUDE.md` | ✅ | Architects |
| `.raven/manifest.json` | ✅ | Architects |
| `.raven/architecture.md` | ✅ | Dev lead |
| `.raven/manifest.secrets.json` | ❌ Never | Architects only |
| `.claude/agents/*.md` | ✅ | Architects |
| `.claude/skills/` | ✅ | Architects |
| `.claude/commands/` | ✅ | Architects |
| `.claude/settings.json` | ✅ | Architects |
| `.git/hooks/pre-commit` | ❌ Local only | raven-setup installs |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Agents not loading | Check `.claude/agents/` — valid YAML frontmatter required |
| raven-core not found | Check `.claude/skills/raven-core/SKILL.md` exists |
| Manifest not loading | Run `/raven-debug` |
| Pre-commit not firing | `chmod +x .git/hooks/pre-commit` |
| CVE check skipped | Add `openai_api_key` to `.raven/manifest.secrets.json` |
| Hooks not running | Check `.claude/settings.json` has all 4 hooks registered |

---

## Works Alongside

```
Superpowers → dev methodology (TDD, planning, review)
GSD         → context management (long sessions)
Raven       → governance + security layer

All three stack. No conflicts.
```

---

## Updating Raven

```bash
cd ~/.raven && git pull
```

Re-run `raven-setup` in any project to get new hooks, skills, and scripts.

---

## Security Audit — Before Installing Any Public Skill

Skills execute inside your dev environment — they can read files, run bash, make network calls. Treat them like untrusted code.

| Step | Check | Red flag |
|---|---|---|
| 1 | Read every line of `SKILL.md` | Instructions to read `.env`, secrets, or SSH keys |
| 2 | Check `allowed-tools` in frontmatter | `Write`, `Edit`, `Bash` without justification |
| 3 | Check bundled scripts | Any `curl` or `wget` to unknown URL |
| 4 | Check for hidden instructions | Whitespace, encoded text, obfuscated content |
| 5 | Verify source repo | Recent commits? Active maintainer? Known author? |
| 6 | Add to `manifest.approved_skills` | Never leave skill list open |

Raven protection: `skill-guard` agent monitors and blocks restricted file access. `manifest.approved_skills` is the only whitelist.

---

*Raven v2.8 — MIT — [github.com/giggsoinc/raven](https://github.com/giggsoinc/raven)*
