---
name: raven-review
description: Use when reviewing code, PRs, or any file changes. Extends
  Claude's built-in review with Raven style and stack compliance checks.
  Checks manifest, imports, style rules, and architecture alignment.
allowed-tools: Read Bash Grep
---

# Raven-Review

## Live Stack
!`cat .raven/manifest.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); s=d.get('stack',{}); libs=s.get('libraries',[]); data=s.get('data',[]); print('Approved libs:', libs, '| Data:', data)"`

## Review checklist (run in order)
1. **Stack** — any imports not in manifest? Flag each one.
2. **Style** — print() statements? Files >150 lines? Functions >50 lines?
3. **Type hints** — all functions annotated?
4. **Docstrings** — all functions documented?
5. **Architecture** — does this match architecture.md? Any drift?
6. **Security** — hardcoded secrets? SQL injection risk? Unvalidated input?
7. **Tests** — are tests present? Do they cover edge cases?

## Output format
| Check | Status | Detail |
|---|---|---|
| Stack | ✅/❌ | ... |
