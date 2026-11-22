---
name: raven-core
description: "Use when writing code, adding imports, creating files, committing, or receiving ANY task prompt. First layer of intelligence — reads every prompt, detects intent, routes to the right skill or agent automatically. Always active."
---
# Raven Core

## Live Config
Read `.raven/manifest.json` if it exists (stack, libraries, mode) before continuing.
## Step 0 — Prompt Analysis (fires on EVERY prompt before anything else)

Read the incoming prompt. Detect intent. Route accordingly.

| If prompt mentions... | Route to | Action |
|---|---|---|
| "find skill" / "search skill" / "what skill" | `/raven-search {query}` | Run skill search |
| "expert" / "L99" / "deep dive" / "world class" | `raven-expert` | Activate L99 mode |
| "security" / "threat model" / "vulnerability" / "CVE" | `raven-security` | Security review |
| "plan" / "phases" / "architecture first" / "scaffold" | `raven-plan` + `/raven-scaffold` | Force plan before code |
| "review" / "PR" / "code review" | `raven-review` | Manifest-aware review |
| "refactor" / "clean up" / "too long" | `raven-refactor` | Style enforcement |
| "test" / "write tests" / "coverage" | `raven-test` | Test-first |
| "explain this code" / "what does this do" / "walk me through" | Narrate in chat, then surface Code-XRay | 1) Give an actual narrated walkthrough in chat — what the code does, why, how pieces connect. 2) THEN run `python3 scripts/code-xray.py --repo . --build --html` and print this project's scoped dashboard link from `.raven/dashboard-link.md` (`dashboard.html#{project}`) as a supplementary visual map — not a substitute for the narration |
| "document" / "docstring" / "README" | `raven-document` | Doc enforcement |
| "drama" / "debate" / "stress-test" / "panel" | `andie` Drama Mode | Expert panel |
| JSX / React / npm / node_modules in prompt | WARN + block | "Raven: manifest forbids this framework" |
| new `import X` in code | CVE check | `cve-check.py --library X` |
| "commit" / "push" / "git add" | Pre-commit gate | All 5 checks fire |
| "sync libraries" / "requirements changed" / "new dependency" | `/raven-sync` | Auto-sync requirements → manifest |
| no specific match | passive mode | Style + stack rules apply |

## Step 1 — Project context
Read `.raven/manifest.json` if it exists (stack, libraries, mode) before continuing.
## Step 2 — Project-specific rules
Read `.raven/manifest.json` if it exists before continuing.
## Step 3 — Load rules on demand
- Import/library → rules/stack.md
- Style check → rules/style.md
- Architecture → rules/architecture.md
- Commit gate → rules/commit.md

## Dynamic Skill Discovery
If a task needs a capability not in loaded skills:
1. Say what skill would help
2. Ask: "Want me to search for a {skill_type} skill?"
3. If yes → `python3 .claude/scripts/skill-search.py --query "{query}"`
4. Show results, ask approval, never install silently
