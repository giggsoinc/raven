# Raven — Codex Discipline Rules

Read this before every task. These rules are non-negotiable.

---

## Non-Negotiable Rules

```
1. NO library added without CVE check — run raven_cve_check first
2. NO secrets in code — API keys, passwords, tokens go in environment variables only
3. NO force push to any branch
4. NO TRUNCATE TABLE or DROP TABLE without approval
5. NO Terraform state file edits without approval
6. NO firewall rule opening 0.0.0.0/0
7. NO commit without manifest.json present in .raven/
```

---

## Before Adding Any Library

Run the CVE check first:
```
Run raven_cve_check on <library-name>
```

Wait for result before proceeding:
- ✅ Clean → add it
- ⚠️ Medium CVE → warn, log to audit, use safer version
- 🔴 Critical CVE → hard block, do not install

---

## Secret Detection

Never write these directly in code:
- API keys of any kind
- Passwords or tokens
- Private keys or certificates
- Database connection strings with credentials

Always use environment variables:
```python
import os
api_key = os.environ.get("OPENAI_API_KEY")
```

---

## Commit Format

```
type(scope): description

feat: add user authentication
fix: resolve CVE in requests library
refactor: simplify manifest validation
```

---

## Stack Declaration

Your stack must be declared in `.raven/manifest.json`.
Run `raven_status` to verify it is loaded.

---

## Audit Trail

Every Raven action is logged to `.raven/audit/audit.log`.
Run `raven_audit` to view the log.

---

*Raven v2.8 — Guardrails before you ship.*
