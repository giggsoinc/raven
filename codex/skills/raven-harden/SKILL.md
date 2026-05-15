---
name: raven-harden
description: Reviews security_log.md and promotes accumulated observations into
  permanent rules. Hardens confirmed patterns into CLAUDE.md. Promotes dynamic
  specialist profiles with 3+ uses into curated skills. Classifies findings into
  internal_raven_ops.md or general_security_patterns.md. The weekly learning loop.
allowed-tools: Read, Write, Edit, Bash, Agent
---

# /raven-harden

Turns session observations into permanent Raven intelligence.
Run when prompted by Task-Observer or whenever you want to solidify what's been learned.

---

## Steps

### 1. Read the Log

```
Read: docs/observations/security_log.md
Find: all entries with Status: open
Find: all entries with Status: promotion-candidate
Count: total open, total candidates
```

Report summary before doing anything:
```
Raven Harden — Review
══════════════════════════════════════
Open observations:      [N]
Promotion candidates:   [N platform(s)]
Last hardened:          [date or never]

Open observations:
  [date] [platform] — [one-line summary]
  ...

Promotion candidates:
  [platform] — used [N] times, [N] log entries
  ...
══════════════════════════════════════
What would you like to do?
  [A] Harden all open observations
  [S] Select which to harden
  [P] Promote candidates to curated skills
  [N] Nothing — just reviewing
```

Wait for user input before proceeding.

---

### 2. Harden Observations → CLAUDE.md

For each approved observation:

**Assess where it belongs:**
- Rule that should never be broken → add to CLAUDE.md Non-Negotiable Rules
- Platform-specific Giggso pattern → add to docs/knowledge/internal_raven_ops.md
- General engineering pattern → add to docs/knowledge/general_security_patterns.md

**CLAUDE.md hardening — append to relevant section:**
```markdown
## Hardened Rules (from observations)

| Date | Rule | Source |
|---|---|---|
| [date] | [rule in one line] | [platform / observation type] |
```

**Mark entry in log:**
```
Status: hardened → [date]
```

---

### 3. Promote Candidates → Curated Skills

For each platform with Status: promotion-candidate:

```
1. Read all log entries for that platform
2. Read cache: .raven/.cache/dynamic-skills/[platform-slug].md
3. Assemble SKILL.md using accumulated profile

Template for promoted skill:
---
name: [platform]-specialist
description: [generated from log observations]
allowed-tools: Agent, WebSearch, Read, Write
---

# [Platform] Specialist — [Expert Name]

**Expert persona:** [from cache]
**Promoted from:** dynamic-specialist after [N] sessions
**Last updated:** [date]

## Core Focus
[from cache + log]

## Key Rules (from observations)
[all confirmed patterns from log entries]

## Known Gotchas (confirmed in practice)
[gotchas from log entries]

## Agent Chain
Step 1 → check guard agents relevant to this platform
Step 2 → [platform] expertise below
Step 3 → search agent ON DEMAND only

[rest of specialist content from cache profile]

---

4. Write to: core/skills/[platform]-specialist/SKILL.md
5. Mark log entries: Status: promoted → [date]
6. Commit to giggsoinc/raven and push
7. raven-sync automatically distributes to all registered projects
```

---

### 4. Final Report

```
Raven Harden — Complete
══════════════════════════════════════
Hardened into CLAUDE.md:   [N] rules
Classified to internal:    [N] patterns
Classified to general:     [N] patterns
Promoted to curated:       [platform list]
Registry synced:           [yes / no — run /raven-registry-sync --all]

Next review: run /raven-harden when Task-Observer surfaces 5+ new entries
══════════════════════════════════════
```

---

## When to Run

- Task-Observer surfaces 5+ open entries at session start
- After any significant debugging session where patterns were found
- After any security audit
- Proactively once a week during active development
