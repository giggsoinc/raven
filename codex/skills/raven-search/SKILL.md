---
name: raven-search
description: Use when developer wants to find, evaluate, or install a new
  Claude skill. Searches anthropics/skills and GitHub, runs security audit,
  shows preview, requires architect approval before installing.
allowed-tools: Bash Read
---

# /raven-search

Search for skills, audit them, and install with approval.

## Usage
```
/raven-search {query}           ← search
/raven-search --install {name}  ← install with audit + approval
/raven-search --list            ← show approved skills
```

## Steps

### Search
Run: `python3 .claude/scripts/skill-search.py --query "{query}"`
Show results table. Prompt: "Which would you like to install? (number or full_name)"

### Install + Audit
Run: `python3 .claude/scripts/skill-search.py --install "{full_name}"`

Script will:
1. Fetch SKILL.md from source
2. Run automated security audit
3. Show first 15 lines for manual review
4. Block if critical issues found
5. Ask for approval (yes/no)
6. Install to .claude/skills/ if approved
7. Add to manifest.approved_skills
8. Remind to restart Claude Code

### After install
Remind developer:
- Review full SKILL.md before using
- Pin to commit hash for production use
- Re-audit on every update
