---
name: raven-security
description: Use when doing security review of code, PRs, or before any merge.
  Extends security-review with manifest-aware CVE context and Raven
  stack validation. Run before every merge to main.
allowed-tools: Read Bash Grep
---

# Raven-Security

## Live approved stack
!`cat .raven/manifest.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); s=d.get('stack',{}); libs=s.get('libraries',[]); libs=[l if isinstance(l,str) else l.get('name','?') for l in libs]; print('Approved:', libs)"`

## Security checks
1. **Secrets** — API keys, tokens, passwords hardcoded anywhere?
2. **Injections** — SQL injection, command injection, path traversal?
3. **Dependencies** — any import not in approved manifest stack?
4. **Auth** — authentication bypasses, broken access control?
5. **Input validation** — unvalidated user input reaching sensitive ops?
6. **CVE** — run: `python3 .claude/scripts/cve-check.py --library {lib}` for each unapproved lib
7. **Secrets in git** — run: `python3 .claude/scripts/secret-scan.py`

## Severity classification
- P1 Critical → secrets exposed, injection possible, auth bypass
- P2 High → unapproved deps, missing validation
- P3 Medium → style/pattern issues with security implications
