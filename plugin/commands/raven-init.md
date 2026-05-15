---
name: raven-init
description: Initialize Raven for a new project. Generates manifest.json interactively, validates against schema, commits with audit trail.
allowed-tools: Read, Write, Edit, Bash
---

# /raven init

Initializes Raven for a new project by generating a validated `manifest.json` interactively.

Run this command when starting a new project. It will ask you questions, generate the manifest, validate it against the schema, and commit it to Git with a proper audit trail entry.

---

## Pre-checks

1. Is `.raven/manifest.json` already present?
   - YES → Load it. Trust it. Proceed with the declared stack. Do not ask to reinitialize. Do not modify it unless the user explicitly requests a change.
   - NO → Greenfield. Run interactive creation below.

2. (Greenfield only) Is Git initialized?
   - NO → Warn: "Git not initialized. Run `git init` first. Audit trail requires Git."

---

## Greenfield Creation Rules

```
NEVER auto-detect or pre-populate answers from:
  - existing venv or .venv directories
  - requirements.txt / pyproject.toml / package.json
  - .env files or environment variables
  - any other project files on disk

Every answer comes from the user. No exceptions.
The manifest is what the user declares — not what the project happens to contain.
```

---

## Interactive Questions

Ask these questions one at a time. Wait for answer before proceeding.

**Question 1 — Project name:**
```
What is your project name?
(letters, numbers, hyphens only — e.g. PatronAI, trinity-v2, genlock)
```
Validate: matches pattern `^[a-zA-Z0-9_-]+$`
If invalid → re-ask with example.

---

**Question 2 — Work type:**
```
What kind of work is this project?

( ) code    — writing application code (Python, TypeScript, Go, etc.)
( ) infra   — infrastructure only (Terraform, K8s YAML, CloudFormation, Helm)
( ) review  — reviewing code, docs, or architecture (no new files generated)
( ) mixed   — both code and infrastructure in the same project
```
Single select. This determines which validators apply.
- code  → full language + library validation
- infra → no language block on .yaml/.yml/.tf/.hcl/.json files
- review → stack validation skipped entirely (read-only work)
- mixed → code rules for .py/.ts/.go, infra rules for .yaml/.tf/.hcl

---

**Question 3 — Primary language(s):**

If work_type is `review`:
```
Skipping language selection — review-only projects don't require a declared stack.
```
Set `stack.language: ["review-only"]` automatically.

If work_type is `infra`:
```
Select your infrastructure file types:
[ ] yaml        (Kubernetes, Docker Compose, Ansible, GitHub Actions)
[ ] hcl         (Terraform, Packer)
[ ] json        (CloudFormation, schema files)
[ ] dockerfile  (Container definitions)
[ ] bicep       (Azure ARM templates)
[ ] shell       (Bash scripts, run scripts)
```
Multi-select. At least one required.

If work_type is `code` or `mixed`:
```
Select your primary language(s):
[ ] python3.13
[ ] python3.12
[ ] python3.11
[ ] typescript
[ ] javascript
[ ] go
[ ] rust
[ ] java
[ ] kotlin
[ ] swift
[ ] csharp
[ ] sql + plsql
[ ] shell
[ ] yaml        (if mixed with infra files)
[ ] hcl         (if mixed with Terraform)
```
Multi-select. At least one required for code files.
If org manifest has locked languages → show pre-selected, explain they cannot be changed.

---

**Question 3 — Frontend:**
```
Select frontend framework (or none):
( ) vuejs
( ) reactjs
( ) nextjs
( ) nuxtjs
( ) none
```
Single select.

---

**Question 4 — Cloud:**
```
Which cloud are you deploying to?
( ) aws
( ) gcp
( ) azure
( ) oci
( ) on-prem
( ) multi
```
Single select.

---

**Question 4b — Frontend** (only if work_type is `code` or `mixed`):
```
Select frontend framework (or none):
( ) vuejs
( ) reactjs
( ) nextjs
( ) nuxtjs
( ) none
```
Single select. Skip entirely for work_type `infra` or `review`.

---

**Question 5 — Database(s):**
```
Select your database(s):
[ ] postgresql
[ ] oracle-26ai
[ ] opensearch
[ ] falkordb     ← GraphDB (preferred)
[ ] neo4j        ← GraphDB (customer demand)
[ ] dynamodb
[ ] kafka
[ ] rabbitmq
[ ] none
```
Multi-select.

---

**Question 6 — Infrastructure:**
```
Select your infra tools:
[ ] terraform
[ ] docker-compose
[ ] kubernetes
[ ] kubespray (on-prem)
[ ] helm
[ ] ansible
```
Multi-select. At least one required.

---

**Question 7 — Who is creating this project?**
```
Your email address (becomes first changelog entry author):
```
Validate: basic email format.

---

**Question 8 — Guard enabled?**
```
Enable Raven Guard for production protection?
( ) yes — recommended
( ) no
```
If org manifest has `guard.enabled` locked to `true` → skip this question, show:
"Guard is enabled by your org policy and cannot be disabled."

---

## Generate Manifest

After all questions answered:

1. Merge answers with org defaults (org locked fields win)
2. Generate `manifest.json` matching schema exactly
3. Add initial changelog entry:
```json
{
  "version": "1.0",
  "changed_by": "{email from Q7}",
  "changed_at": "{current ISO timestamp}",
  "changes": "Initial project manifest — {answers summary}",
  "pr": "pending — commit this file to generate PR",
  "approved_by": "{email from Q7}"
}
```

4. Show generated manifest to user:
```
Here's your manifest.json:

{generated JSON}

Looks good?
( ) Yes — save and continue
( ) No — let me change something
```

---

## Save + Secrets

If user confirms:

1. Create `.raven/` directory if not exists
2. Write `.raven/manifest.json`
3. Write `.raven/.gitignore`:
```
manifest.secrets.json
.cache/
```

4. Copy `manifest.secrets.example.json` → `.raven/manifest.secrets.example.json`

5. Output instructions:
```
✅ manifest.json created

Next steps:
1. Get manifest.secrets.json from your architect via secure channel
2. Place it at: .raven/manifest.secrets.json
3. Run: claude --debug to validate everything loaded
4. Commit manifest.json to Git:

   git add .raven/manifest.json
   git add .raven/.gitignore
   git commit -m "chore: init raven manifest v1.0 [RAVEN:INIT]"
   git push

⚠️  NEVER commit manifest.secrets.json
⚠️  NEVER commit .raven/.cache/
```

---

## Validation

After saving, run validation:

1. Validate manifest against `manifest.schema.json`
2. Check all required fields present
3. Check locked fields match org manifest (if present)
4. Check changelog has at least one entry

Output:
```
Validating manifest...

✅ Schema valid
✅ Required fields present
✅ Locked fields respected
✅ Changelog entry present
✅ .gitignore configured

Raven initialized for {project}.
Run: claude --debug
```

If validation fails:
```
❌ Validation failed:
  - {field}: {reason}

Fix and re-run: /raven init
```

---

## Audit Trail

Every init creates:
- A `changelog` entry in `manifest.json` (in Git)
- A commit with message `[RAVEN:INIT]` (in Git history)
- A timestamp + author on the changelog entry

This means every project initialization is fully auditable in Git.

---

*Raven v2.8 — github.com/giggsoinc/raven*
