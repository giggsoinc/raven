---
name: raven-dashboard
description: Generate tokenomics + usage dashboard with recommendations. Use when user asks for "dashboard", "tokenomics", "token usage", "cost report", "usage metrics", "Raven status", or "how much have I spent". Renders to CLI, Obsidian markdown, and static HTML with download buttons. Includes proper metadata (date, time, version, company, project, owner, user, git remote, manifest). Rule-based recommendations engine surfaces actionable savings.
allowed-tools: Bash, Read
---

# /raven-dashboard

Generates the Tokenomics & Usage Dashboard with a full metadata block and a rule-based recommendations engine.

---

## How to invoke

```bash
# CLI (terminal-friendly ASCII)
python3 .claude/scripts/dashboard.py --cli

# Obsidian markdown (writes ~/RavenVault/Dashboard.md)
python3 .claude/scripts/dashboard.py --obsidian

# Static HTML report with download buttons
python3 .claude/scripts/dashboard.py --html --open

# All three at once
python3 .claude/scripts/dashboard.py --all

# Raw metrics JSON (for piping)
python3 .claude/scripts/dashboard.py --json
```

---

## Filters

- `--days N` — reporting window in days (default 30)
- `--month YYYY-MM` — specific month
- `--project NAME` — filter to one project (default: all)

---

## What it includes

1. **Metadata block** — report timestamp (UTC + local), plugin version, project, company, owner, user, git branch, git remote, manifest presence, vault path
2. **Manifest snapshot** — project, owner, version, stack, standards, approval mode
3. **Last session** — tokens, cost, tier breakdown
4. **Cumulative window** — sessions, total tokens, total cost, avg/session
5. **Tier mix** — SIMPLE/MEDIUM/COMPLEX/LOCAL_ONLY share, cost, distribution bar
6. **Daily series** — sessions/tokens/cost per day
7. **Top skills + specialists** — invocation counts
8. **Guard events** — violation + approval breakdown
9. **Recommendations** — rule-based, severity-coded (🔴 high · 🟡 medium · 🔵 info), with estimated savings where applicable

---

## Recommendations engine — rules

| Rule | Trigger | Severity | Suggested action |
|------|---------|----------|------------------|
| Opus over-classification | COMPLEX share > 30% | 🔴 high | Review prompts, tune model.env |
| Opus zero rate | 0% COMPLEX over 5+ sessions | 🔵 info | Verify router wiring |
| High avg cost/session | > $1.00 | 🟡 medium | Use /clear, lower autocompact pct |
| High avg tokens/session | > 50,000 | 🟡 medium | Compress CLAUDE.md, trim skills |
| Guard violations trending | > 10 in window | 🔴 high | Address top violation root cause |
| Frequent approval overrides | > 5 | 🟡 medium | Codify exceptions in manifest |
| No vault sessions | sessions/ dir empty | 🔴 high | Check obsidian-log Stop hook |
| Specialist concentration | One spec > 70% | 🔵 info | Check router wiring |
| Missing manifest | `.raven/manifest.json` absent | 🔴 high | Run /raven-init (Andie auto-onboards) |

---

## Output locations

- CLI: stdout
- Obsidian: `~/RavenVault/Dashboard.md`
- HTML: `~/RavenVault/dashboard.html`
- JSON: stdout

---

## Privacy

All processing is local. No telemetry. No Hub. No external calls (no GitHub, no API).
HTML download buttons (JSON + CSV + Print/PDF) work offline.
