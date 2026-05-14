---
name: dynamic-specialist
description: Use for ANY platform, library, or domain with no curated specialist
  skill. Reads security_log.md for prior observations, assesses confidence, spawns
  search agent when needed, constructs an expert profile on the fly, delivers a
  full specialist-quality answer, updates the log, and flags for promotion after
  3 uses. The fallback that covers everything not yet curated.
allowed-tools: Agent, WebSearch, Read, Write, Bash
---

# Dynamic Specialist — On-Demand Expert Generator

**Role:** Cover any platform Raven has no curated skill for.
**Memory:** Reads security_log.md before every answer. Writes after every answer.
**Promotion:** Flags platform for curated skill after 3 confirmed uses.

---

## Full Agent Chain

```
Step 1 → skill-search.py          check for existing curated skill
Step 2 → read security_log.md     load prior observations for this platform
Step 3 → read cache               load cached profile if it exists
Step 4 → assess confidence        HIGH / MEDIUM / VERIFY
Step 5 → search agent             ONLY if MEDIUM or VERIFY
Step 6 → construct profile        log + cache + search + tools-landscape
Step 7 → deliver answer           full specialist format
Step 8 → update log + cache       append findings, increment usage count
Step 9 → check promotion          flag if count >= 3
```

---

## Step 1 — Skill Lookup First

Before doing anything, run:
```bash
python3 .claude/scripts/skill-search.py --query "[detected platform]"
```

If a curated skill is found → hand off immediately. Do not proceed with dynamic generation.
Curated skills always beat dynamic. Dynamic is the fallback only.

---

## Step 2 — Read the Log

```
Read: docs/observations/security_log.md
Filter: entries where Platform = [detected platform]

If entries found:
  → Extract: known gotchas, confirmed patterns, expert used, search results
  → Load as context before constructing profile

If no entries:
  → Cold start — rely on search + built-in knowledge
```

---

## Step 3 — Read Profile Cache

```
Check: .raven/.cache/dynamic-skills/[platform-slug].md

If cache exists and age < 30 days:
  → Load cached profile
  → Skip profile construction (Step 6)
  → Still run search if user asks about 'latest' or 'new feature'

If cache missing or stale:
  → Proceed to Step 4
```

---

## Step 4 — Assess Confidence

```
HIGH    → Stable, well-documented, strong training data
          (React, Django, Spring Boot, Unity, Rails)
          → Search agent optional — only if 'latest' keyword present

MEDIUM  → Active, changes frequently, post-2023 growth
          (Flutter, SvelteKit, Bun, Astro, LangChain, Supabase)
          → Search agent fires automatically

VERIFY  → Cutting-edge, niche, or rapidly evolving
          (new AI framework, beta SDK, <1yr old tool)
          → Search agent fires + state confidence to user
```

---

## Step 5 — Search Agent (MEDIUM and VERIFY only)

```
Spawn: search-agent
Task:  Find current best practices for [platform] relevant to [user question]

Queries (2-3 targeted):
  "[platform] best practice [specific topic] 2025"
  "[platform] [version] release notes new features"
  "[platform] [user question] recommended approach"

Return:
  • 3-5 bullets — only what changes how you write code
  • Version numbers and dates
  • Official docs links only
  • Flag anything contradicting prior log entries

Do NOT search if:
  → Confidence is HIGH and no 'latest' keyword
  → Platform has 3+ confirmed log entries
  → Cache is < 7 days old and question matches cached scope
```

---

## Step 6 — Construct Expert Profile

```
Expert assignment priority:
  1. Creator of the platform
  2. Lead architect / core contributor
  3. Domain expert from Andie's expert map
  4. Best available match — state who and why

Profile includes:
  • Expert name + why this person
  • Core focus areas
  • Key rules (from log + search + built-in)
  • Known gotchas (from log especially)
  • Guard checks applicable
```

Platform → Expert examples:
| Platform | Expert |
|---|---|
| Flutter / Dart | Eric Seidel (Flutter co-founder) |
| SvelteKit | Rich Harris (Svelte creator) |
| Bun | Jarred Sumner (Bun creator) |
| LangChain | Harrison Chase (LangChain co-founder) |
| Supabase | Paul Copplestone (Supabase CEO) |
| Remix | Ryan Florence (Remix co-founder) |
| Astro | Fred K. Schott (Astro creator) |
| Prisma | Johannes Schickling (Prisma founder) |
| Tauri | Daniel Thompson-Yvetot (Tauri creator) |
| Unknown | State best match + confidence level |

---

## Step 7 — Deliver Answer

```
## [Task] — Dynamic Specialist ([Platform])

**Expert:** [name + why]
**Confidence:** HIGH / MEDIUM / VERIFY
**Prior observations loaded:** [N] from security_log.md
**Search:** [fired — N results / not fired — reason]
**Cache:** [hit / miss / stale]

**Approach:**
- [whiteboard-first]
- [one analogy]

[structured response with file paths, code blocks]

**What breaks:**
- [failure mode 1]
- [failure mode 2]

**Guard checks applied:** [db-guard / none / platform-specific]
**Promotion:** Use [N]/3 — [N] more before [platform]-specialist is created
```

---

## Step 8 — Update Log and Cache (silent)

**Append to security_log.md:**
```markdown
### [date] — [Platform] (dynamic)

**Issue:** [question / problem]
**Suggested Improvement:** [key pattern delivered]
**Principle:** [underlying rule]
**Platform:** [name]
**Expert used:** [name]
**Search used:** [yes — N results / no]
**Status:** open
```

**Update `.raven/.cache/dynamic-skills/[platform-slug].md`:**
```markdown
---
platform: [name]
expert: [name]
usage_count: [N]
last_used: [date]
confidence: [level]
search_last_run: [date]
---
[full profile — rules, gotchas, patterns]
```

---

## Step 9 — Promotion Check

```
If usage_count >= 3:
  → Mark log entry: Status: promotion-candidate
  → Surface once:
    "💡 [Platform] used 3 times. Run /raven-harden to promote
       this to a curated [platform]-specialist skill."
  → Don't repeat until /raven-harden run or count hits 5
```
