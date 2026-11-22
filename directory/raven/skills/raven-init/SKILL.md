---
name: raven-init
description: "Initialize Raven for a new project. Andie-conversational — auto-scans project, asks at most 2 questions, generates manifest.json, validates, and commits with audit trail."
---
# /raven init — Andie-Conversational Setup

Replaces the legacy 7-step interactive wizard with an Andie-driven conversation. Auto-detects everything possible, asks only what cannot be inferred.

---

## Entry Points

This skill is invoked by:
1. **Andie Branch A onboarding** — fires automatically when no manifest exists and user confirms "OK to proceed".
2. **Explicit `/raven init`** — user runs the command directly.
3. **`andie init`** — user invokes Andie for setup.

---

## Pre-checks

1. Is `.raven/manifest.json` already present?
   - **YES** → Load it. Trust it. Proceed with the declared stack. Do not reinitialize. Do not modify unless user explicitly requests it.
   - **NO** → Run the auto-scan flow below.

2. Is Git initialized?
   - **NO** → Note silently: "Git not initialized — audit trail will start when you `git init`." Continue.

---

## Auto-Scan (Silent, Fast)

Scan the project root for these signals. No prompts. No noise. Just detect.

| Signal File | Infers |
|-------------|--------|
| `package.json` | Node/JS · framework from deps (React/Vue/Next/etc.) · scripts |
| `pyproject.toml` / `requirements.txt` / `setup.py` | Python · libraries · framework (FastAPI/Django/Flask) |
| `Cargo.toml` | Rust |
| `go.mod` | Go |
| `pom.xml` / `build.gradle` | Java/Kotlin |
| `Gemfile` | Ruby |
| `sfdx-project.json` / `force-app/` | Salesforce |
| `__manifest__.py` | Odoo |
| `*.tf` files | Terraform |
| `Dockerfile` / `docker-compose.yml` | Container stack |
| `helm/` / `charts/` / `k8s/` | Kubernetes |
| `.env*` / `secrets.json` | Mark as sensitive — do NOT read |
| `git remote -v` | Owner (from GitHub URL) |
| `.git/config` | Branch info |

Output silently to working memory — NOT to the user.

---

## Inference Rules

From the scan, infer the manifest defaults:

| Manifest field | Inference source |
|----------------|------------------|
| `project` | Folder name |
| `owner` | git remote URL (giggsoinc/foo → "giggsoinc") |
| `stack.language` | From signal files above |
| `stack.frontend` | From package.json frameworks |
| `stack.db` | From requirements (psycopg2 → postgres, etc.) |
| `stack.infra` | From .tf, Dockerfile, k8s/ presence |
| `stack.cloud` | "on-prem" default, override if AWS/Azure/GCP detected |
| `stack.libraries` | From requirements/package.json |
| `standards` | "raven-v1" default |
| `approval_mode` | "first_responder" default |

---

## Ask AT MOST 2 Questions

Only ask what cannot be inferred. Typically:

**Q1 — Owner confirmation (only if not detectable from git remote):**
```
I detected this is a {{language}} project at {{folder_name}}.
Who owns it? (defaults to your git username if blank)
```

**Q2 — Primary use (only if ambiguous):**
```
What's the primary use? — (a) production app · (b) internal tool · (c) library · (d) research/experiment
```

NEVER ask 8 questions. NEVER show "Question 0" / "Question 1" headers like the legacy flow.

---

## Propose Manifest as PROPOSAL

Show the resolved manifest as a PROPOSAL block. User accepts / modifies / rejects.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PROPOSED MANIFEST — .raven/manifest.json
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

project:    {{name}}
owner:      {{owner}}
language:   {{langs}}
framework:  {{frameworks}}
db:         {{db}}
infra:      {{infra}}
cloud:      {{cloud}}
libs:       {{count}} libraries detected

Guards enabled: bash-ban-raw-tools · cbm-code-discovery-gate ·
                cve-prompt-guard · secret-scan · audit-log
AIRTaaS MCP: https://sandbox.airtaas.ai/mcp (login at sandbox.airtaas.ai — not stored)
LangSmith:   off unless they already use LANGCHAIN_TRACING_V2

→ Accept · Modify · Reject
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

On accept → write `.raven/manifest.json` and `.raven/dashboard-settings.json` (AIRTaaS URL fixed, enabled false until they log in; no secrets) → validate → **host glue + dashboard:**

Commands for the user to review and run themselves:

```text
python3 scripts/ops/raven-first.py --boot
```

Fallback: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --boot`. That copies `scripts/raven-python.sh`, `scripts/routing|memory|session|ops`, `AGENTS.md`, `.agents/agents.md` (AntiGravity/Codex/Grok contract), and runs ide-boot. Public users do not need extra instructions. Then commit manifest only (settings stay gitignored).

Optional after accept (does not count as a 3rd scan question): “Open AIRTaaS login in the browser now?” If yes:
`python3 -c "import webbrowser; webbrowser.open('https://sandbox.airtaas.ai')"`
Never collect email/password. Login is on AIRTaaS.

---

## Validate

After writing, run schema validation:

Commands for the user to review and run themselves:

```text
python3 .claude/scripts/validate-manifest.py 2>/dev/null
```

If invalid → show the error, offer to re-prompt that specific field. Never erase user input on validation failure.

---

## Commit

Commands for the user to review and run themselves:

```text
git add .raven/manifest.json
git commit -m "chore: raven-init — manifest created via Andie

Manifest fields:
- Language: {{langs}}
- Cloud: {{cloud}}
- Approval mode: {{mode}}

[raven-init]
"
```

If Git is not initialized → write file only, skip commit, note: "Manifest saved. Initialize Git when ready — `git init && git add .raven/`."

---

## Smoke Test (Replaces /raven-debug for First-Run)

After commit, Andie returns one final line:

```
✅ Raven is loaded. Manifest committed. Dashboard opened.
   Every turn: python3 scripts/ops/raven-first.py --prompt "…"
   Ask me anything — I'll route to the right specialist automatically.
   Settings: dashboard → Settings. AIRTaaS login button → sandbox.airtaas.ai (MCP will not work until you log in there).
   Free tier — local only. Enterprise (dashboards, compliance, support): giggso.com/raven
```

That's the proof of life. No separate `/raven-debug` needed.

---

## Migration Note

The legacy `sr-00-preflight.sh` through `sr-06-verify.sh` setup scripts are NO LONGER the install path. They remain in the repo for advanced users but are not invoked by default. The Claude Desktop plugin install + Andie Branch A is the canonical flow.

---

## RULES — what raven-init never does

- No 7-step question wizard.
- No "Question 0a / Q0b / Q0c" labels.
- No Hub configuration prompts (Enterprise path only — kept private).
- No interactive yes/no for every field — propose ALL at once.
- No "did it work?" ambiguity — final smoke line is mandatory.
- No bash setup scripts called from this skill — pure Andie + Read/Write/Edit/Bash.

---

*raven-init v4.0.0 — Andie-conversational. Auto-scan first. ≤2 questions. PROPOSAL gate. Smoke test at end.*
