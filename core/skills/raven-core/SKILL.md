---
name: raven-core
description: Use when writing code, adding imports, creating files, committing,
  or receiving ANY task prompt. First layer of intelligence — reads every prompt,
  detects intent, routes to the right skill or agent automatically. Always active.
allowed-tools: Read Bash Grep
---

# Raven Core

## Live Config
!`cat .shay-rolls/manifest.json 2>/dev/null || echo "MANIFEST MISSING — run raven-setup.sh"`

## Step 0 — Prompt Analysis (fires on EVERY prompt before anything else)

Read the incoming prompt. Detect intent. Route accordingly.

| If prompt mentions... | Route to | Action |
|---|---|---|
| "find skill" / "search skill" / "what skill" | `/raven-search {query}` | Run skill search |
| "expert" / "L99" / "deep dive" / "world class" | `shay-expert` | Activate L99 mode |
| "security" / "threat model" / "vulnerability" / "CVE" | `shay-security` | Security review |
| "plan" / "phases" / "architecture first" / "scaffold" | `shay-plan` + `/raven-scaffold` | Force plan before code |
| "review" / "PR" / "code review" | `shay-review` | Manifest-aware review |
| "refactor" / "clean up" / "too long" | `shay-refactor` | Style enforcement |
| "test" / "write tests" / "coverage" | `shay-test` | Test-first |
| "document" / "docstring" / "README" | `shay-document` | Doc enforcement |
| "drama" / "debate" / "stress-test" / "panel" | `andie` Drama Mode | Expert panel |
| JSX / React / npm / node_modules in prompt | WARN + block | "Raven: manifest forbids this framework" |
| new `import X` in code | CVE check | `cve-check.py --library X` |
| "commit" / "push" / "git add" | Pre-commit gate | All 5 checks fire |
| "sync libraries" / "requirements changed" / "new dependency" | `/raven-sync` | Auto-sync requirements → manifest |
| no specific match | passive mode | Style + stack rules apply |

## Step 1 — Project context
!`cat .shay-rolls/manifest.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); print('Project:', d.get('project'), '| Mode:', d.get('mode','team'), '| Lang:', d.get('stack',{}).get('language'))" 2>/dev/null || true`

## Step 2 — Project-specific rules
!`cat .shay-rolls/manifest.json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
rules=d.get('project_rules',{})
ff=rules.get('forbidden_frameworks',[])
if ff: print('FORBIDDEN frameworks:', ', '.join(ff))
lic=rules.get('license','')
if lic: print('License header required:', lic)
cc=rules.get('commit_convention','')
if cc: print('Commit convention:', cc)
ag=rules.get('require_approval_gates',False)
if ag: print('Approval gates: REQUIRED before any file write')
" 2>/dev/null || true`

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
