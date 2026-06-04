---
name: andie-jr
description: Force-invoke Andie-jr, Raven's brownfield debug assistant, for any
  bug, error, regression, stack trace, or "not working" case. Use this when the
  automatic triage router did not fire but you want a structured 2-round triage.
  For planning or design, use /andie instead.
---

# /andie-jr

This is the **force-path** for Andie-jr. The `triage-router.py` hook loads
Andie-jr automatically when a prompt looks like a brownfield symptom, but it is
regex-based and misses edge cases. This command loads Andie-jr unconditionally.

## What to do

1. **Load the `andie-jr` skill** immediately — do not wait for the router.
2. Take everything after `/andie-jr` as the problem report. Example:
   `/andie-jr the login endpoint 500s after the last deploy` → that's the symptom.
3. If no symptom was given, ask once: *"What's broken, and what did you expect instead?"*
4. Run Andie-jr's normal flow from her SKILL.md:
   - Max 2 rounds, max 3 roles
   - Returns: **problem · root cause · fix · why · audit note · commit suggestion**
   - No mode dance, no ceremony — fast triage.
5. If the task turns out to be greenfield design (not a bug), stop and redirect
   to `/andie`.

## Routing reminder

| Use | When |
|---|---|
| `/andie-jr` | bug, error, regression, stack trace, "not working", "why is X failing" |
| `/andie` | planning, design, architecture, tradeoffs, strategy, "should I…" |
