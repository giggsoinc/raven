---
name: raven-debug
description: Use to run a full Raven boot diagnostic.
  Checks all files, agents, manifest, and hooks are correctly installed.
---

# /debug (claude --debug)

Run in order:
1. Check CLAUDE.md exists at project root
2. Check .shay-rolls/manifest.json — valid JSON, all required fields
3. Check .shay-rolls/manifest.secrets.json — present (warn if missing)
4. Check .gitignore — exists at project root (hard stop if missing)
5. Check .gitignore entries — .env, *.pem, *.key, manifest.secrets.json all covered
6. Check .env files — present but not gitignored (warn if exposed)
7. Check .claude/agents/ — list all loaded agents
8. Check .claude/skills/ — list all loaded skills
9. Check .claude/settings.json — hooks registered
10. Check .git/hooks/pre-commit — executable
11. Check .shay-rolls/architecture.md — exists (warn if missing)
12. Check manifest.secrets.json permissions — warn if not chmod 600

Output:
✅/❌ per check
Final: CLEARED or X ERROR(S) FOUND
