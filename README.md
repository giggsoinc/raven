<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# Raven

> AI coding discipline for Claude Code, GitHub Copilot, and OpenAI Codex.
> 35 skills · 10 guard agents · CVE scanning · secret detection · audit logs.
> MIT License · Built by [Giggso](https://giggso.com)

*Guardrails before you ship.*

---

## Choose Your Install

Pick your situation. Each links to the full guide.

<table>
<thead>
<tr>
<th>Who</th>
<th>OS</th>
<th>One command</th>
<th>Guide</th>
</tr>
</thead>
<tbody>
<tr>
<td rowspan="2"><b>Individual developer</b><br><sub>installs for yourself</sub></td>
<td>macOS / Linux</td>
<td><code>curl -fsSL .../install.sh | bash</code></td>
<td><a href="HOW-TO-USE.md#dev-mac-linux">→ Full guide</a></td>
</tr>
<tr>
<td>Windows</td>
<td><code>iwr .../install.ps1 | iex</code></td>
<td><a href="HOW-TO-USE.md#dev-windows">→ Full guide</a></td>
</tr>
<tr>
<td rowspan="2"><b>IT / Admin</b><br><sub>deploys for the whole team</sub></td>
<td>macOS / Linux</td>
<td><code>sudo bash install-enterprise.sh</code></td>
<td><a href="HOW-TO-USE.md#enterprise-mac-linux">→ Full guide</a></td>
</tr>
<tr>
<td>Windows</td>
<td><code>install-enterprise.ps1</code> (coming soon)</td>
<td><a href="HOW-TO-USE.md#enterprise-windows">→ Full guide</a></td>
</tr>
<tr>
<td><b>Codex / Copilot</b><br><sub>plugin, no terminal needed</sub></td>
<td>Any</td>
<td>Install plugin from <code>giggsoinc/raven-codex</code></td>
<td><a href="HOW-TO-USE.md#codex-copilot">→ Full guide</a></td>
</tr>
</tbody>
</table>

---

## What It Does

Enforces consistent quality, stack discipline, and security across your team — without blocking developer flow.

| During coding | At git commit | At CI/CD |
|---|---|---|
| Agents advise in real time | Pre-commit hook fires | Pipeline thin-check |
| Skills guide by work type | CVE scan on every import | Last safety net |
| No hard blocks during typing | Secret detection on staged files | Blocks unreviewed code |

**Works for any project type — not just code:**

| Project type | Examples | Raven enforces |
|---|---|---|
| Software | Python, TypeScript, Go, Java | Style, CVE, secrets, tests |
| Infrastructure | Terraform, Kubernetes, Helm | Change docs, naming, secret hygiene |
| Data | dbt, Airflow, Jupyter, SQL | Query quality, schema docs, PII |
| Salesforce | Apex, SFDC metadata | Bulk patterns, test coverage, hardcoded IDs |
| Odoo | Python modules, XML views | Module structure, ORM discipline |
| Documentation | Markdown, architecture diagrams | Structure, broken links, sync |

---

## What's Included

**35 Skills** — load at startup (~100 tokens each), rules fire only when triggered

> Andie (orchestration) · raven-core · raven-expert · raven-plan · raven-review ·
> raven-security · raven-refactor · raven-test · raven-document ·
> aws · gcp · azure · oci · kafka · postgres · redis · k8s · terraform ·
> fastapi · nicegui · vault · security · aiml · dataeng · devops · bigdata ·
> vector-db · dynamic · odoo · salesforce · log-management · agent-chaining ·
> tools-landscape · task-observer

**10 Guard Agents** — always on, fire silently

> manifest-checker · stack-validator · style-enforcer · architecture-guard ·
> db-guard · skill-guard · claude-mem · guard-git-watch · odoo-guard · salesforce-guard

**MCP Tools** — `raven_status` · `raven_cve_check` · `raven_sync_libs` · `raven_debug` · `raven_violation`

**Slash Commands** — `/raven-scaffold` · `/raven-debug` · `/raven-review` · `/raven-approve` · `/raven-harden` · `/raven-incident`

---

## Companion Repos

| Repo | For | Does |
|---|---|---|
| [giggsoinc/raven](https://github.com/giggsoinc/raven) | Developers | This repo — Claude Code |
| [giggsoinc/raven-codex](https://github.com/giggsoinc/raven-codex) | Codex / Copilot users | Plugin version |
| [giggsoinc/raven-guard](https://github.com/giggsoinc/raven-guard) | DevOps / architects | Production protection |

---

## License

MIT — [Giggso](https://giggso.com) · [HOW-TO-USE.md](HOW-TO-USE.md) for full documentation
