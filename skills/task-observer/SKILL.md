---
name: task-observer
description: Meta-skill. Loaded at every session start via CLAUDE.md boot sequence.
  Silently watches all actions. Logs vulnerabilities found, corrections made, and
  new patterns learned to docs/observations/security_log.md. Classifies findings
  as internal (Giggso-specific) or general (open-source safe). Never surfaces
  log writes to the user — operates silently in the background.
allowed-tools: Read, Write, Edit
---

# Task-Observer — Session Meta-Skill

**Role:** Silent observer. Runs behind every other skill and agent.
**Visibility:** Zero — never announce log writes. Never say "I'm logging this."
**Scope:** Every session from load to stop.

---

## Boot Sequence (runs at session start)

```
1. Read docs/observations/security_log.md
   → Load all prior observations as session context
   → Note: platforms seen, patterns established, open issues

2. Read docs/knowledge/internal_raven_ops.md
   → Load internal Giggso/Raven-specific patterns

3. Read docs/knowledge/general_security_patterns.md
   → Load generalised patterns

4. Count entries since last /raven-harden
   → If 5+ unreviewed entries → surface once at session start:
     "📋 security_log.md has [N] new entries — consider running /raven-harden"
   → Then stay silent
```

---

## What to Log — Triggers

Log silently whenever any of these occur:

| Event | What to log | Where |
|---|---|---|
| User corrects Claude's output | The wrong approach + the correct one | security_log.md |
| Vulnerability found in code | CVE, injection, leakage, auth gap | security_log.md |
| Platform-specific gotcha discovered | Version-specific behaviour, breaking change | security_log.md |
| New best practice confirmed | Pattern works, user approves | security_log.md |
| Giggso/Raven-specific pattern | Stack-specific, internal only | internal_raven_ops.md |
| General engineering pattern | Applicable broadly, no client refs | general_security_patterns.md |

---

## Log Entry Format — security_log.md

```markdown
### [YYYY-MM-DD] — [Platform] ([type: correction|finding|pattern|vulnerability])

**Issue:** what was wrong or what was found
**Suggested Improvement:** what the correct approach is
**Principle:** the underlying rule this violates or confirms
**Platform:** [Flutter / Salesforce / PostgreSQL / etc.]
**Expert used:** [if dynamic-specialist was invoked]
**Search used:** [yes/no — and what was found]
**Status:** open | hardened | promoted
```

---

## Log Entry Format — internal_raven_ops.md

```markdown
### [YYYY-MM-DD] — [System/Platform]
**Pattern:** specific behaviour observed in this stack
**Context:** where it applies (lockey / fin-processor / specific module)
**Source:** user correction | session finding | search result
```

---

## Log Entry Format — general_security_patterns.md

```markdown
### [YYYY-MM-DD] — [Category: auth | injection | data-leakage | config | etc.]
**Pattern:** generalised description — no client names
**Applies to:** [languages / frameworks]
**Anti-pattern:** what to avoid
**Principle:** the underlying rule
```

---

## Classification Rules

**Goes to internal_raven_ops.md if:**
- References Oracle 23ai/26ai specific behaviour in this stack
- References Giggso's specific Azure Logic App setup
- References lockey/fin-processor specific patterns
- Would reveal architecture if published

**Goes to general_security_patterns.md if:**
- Applies to any project using that platform
- No identifying information
- Would be useful as open-source guidance

**Goes to security_log.md always** — it's the master log. The others are taxonomy refinements.

---

## Pre-flight Security Gate

Before delivering any code, query response, or audit result — run this silent check:

```
□ Does output contain hardcoded secrets or credentials? → remove
□ Does output contain SQL inline in non-SQL files? → extract
□ Does output suggest disabling security controls? → flag
□ Does output expose internal system details unnecessarily? → redact
□ Does output contradict a principle already in security_log.md? → align
```

If any check fails → fix silently before presenting. Never tell the user "I caught myself."

---

## Session End

On session stop (Stop hook fires):

```
1. Count new entries added this session
2. If entries > 0 → silently update Index table in security_log.md
3. If dynamic-specialist was used → check cache count for platform
   → if count >= 3 → add promotion candidate flag to log entry
4. No summary to user unless /raven-harden was run
```

---

## Weekly Hardening Reminder

Task-Observer tracks the date of the last `/raven-harden` run in security_log.md header.
If more than 7 days have passed AND log has 3+ open entries:

```
Surface once per session (not every response):
"📋 It's been [N] days since last /raven-harden.
   [X] open observations ready for review. Run /raven-harden when ready."
```
