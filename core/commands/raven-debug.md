---
name: raven-debug
description: Use to run a full Raven boot diagnostic.
  Checks all files, agents, manifest, and hooks are correctly installed.
  If no manifest exists, runs first-run discovery instead of erroring.
---

# /raven-debug

## First: Check If Raven Is Initialized

Before running any diagnostics:

```
Is .raven/manifest.json present?
```

### NO MANIFEST — First-Run Discovery

If `.raven/manifest.json` does NOT exist:

Do NOT error. Do NOT say "manifest missing — hard stop."

Instead, say this:

```
─────────────────────────────────────────────────
  RAVEN — not set up yet for this project
─────────────────────────────────────────────────

  No manifest found at .raven/manifest.json

  Raven can help with this project. Here's what
  I can see in the current directory:

  [Run: python3 .claude/scripts/sr-detect-workmode.py .]
  [Display the signals and detected mode from the output]

  This looks like a [detected mode] project.

  Want me to set Raven up now?

    1) Yes — set it up (takes 2 minutes)
    2) No — just tell me what Raven would do here
    3) Show me the manifest that would be created

  →
```

If user says **1**: Run the setup flow inline (ask the 2-3 questions, create the manifest, confirm).
If user says **2**: Describe what Raven would enforce for the detected mode, no manifest created.
If user says **3**: Generate and display the manifest JSON without saving it. Ask "Save this? [y/n]".

This is the correct behaviour when a developer runs `raven-debug` as their first command — they're exploring. Reward that, don't punish it.

---

### MANIFEST EXISTS — Full Diagnostic

Run these checks in order. Output ✅ or ❌ per check.

1. **CLAUDE.md** — exists at project root?
2. **manifest.json** — valid JSON, all required fields present?
3. **manifest.json → stack.work_type** — present and valid? (code/infra/data/docs/review/mixed/salesforce/odoo)
4. **manifest.secrets.json** — present? (warn if missing, not hard stop)
5. **.gitignore** — exists at project root?
6. **.gitignore entries** — covers `.env`, `*.pem`, `*.key`, `manifest.secrets.json`?
7. **.env files** — present but gitignored? (warn if exposed)
8. **.claude/agents/** — list all loaded agents (count + names)
9. **.claude/skills/** — list all loaded skills (count + names)
10. **.claude/settings.json** — hooks registered (PreToolUse, PostToolUse, PreCompact, Notification)?
11. **.git/hooks/pre-commit** — executable?
12. **.raven/architecture.md** — exists? (warn if missing — not a hard stop)
13. **manifest.secrets.json permissions** — warn if not chmod 600

---

### Output Format

```
─────────────────────────────────────────────────
  RAVEN — diagnostic
─────────────────────────────────────────────────

  Project:    {project name from manifest}
  Work type:  {work_type}
  Mode:       {solo/team/enterprise}
  Platform:   {auto-detected}

  ✅  CLAUDE.md present
  ✅  manifest.json valid
  ✅  work_type: infra
  ⚠️   manifest.secrets.json missing — get from your architect
  ✅  .gitignore configured
  ✅  5 agents loaded: manifest-checker stack-validator style-enforcer architecture-guard db-guard
  ✅  Skills: raven-core + 23 specialists
  ✅  pre-commit hook executable
  ✅  Hooks: PreToolUse PostToolUse PreCompact Notification
  ⚠️   .raven/architecture.md missing — create before first commit

  CLEARED — 2 warnings

─────────────────────────────────────────────────
```

Final line:
- `CLEARED` — all checks passed (warnings OK)
- `CLEARED — N warning(s)` — passed with warnings
- `X ERROR(S) FOUND — run /raven-debug for details` (only if hard errors)
