# /raven init

Initializes Raven for a new project by generating a validated `manifest.json` interactively.

Run this command when starting a new project. It will ask you questions, generate the manifest, validate it against the schema, and commit it to Git with a proper audit trail entry.

---

## Pre-checks

Before asking anything, check:

1. Is `.raven/manifest.json` already present?
   - YES → Ask: "Manifest already exists (v{version}). Reinitialize? This will create a new version." 
   - If yes → continue. If no → STOP.

2. Is `manifest.org.example.json` or an org manifest present?
   - YES → Load org defaults. Locked fields will be pre-filled and cannot be changed.
   - NO → Use schema defaults only.

3. Is Git initialized in this directory?
   - NO → Warn: "Git not initialized. Run `git init` first. Audit trail requires Git."

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

**Question 2 — Primary language(s):**
```
Select your primary language(s):
[ ] python3.12
[ ] python3.11
[ ] typescript
[ ] javascript
[ ] go
[ ] sql + plsql
[ ] shell
```
Multi-select. At least one required.
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
