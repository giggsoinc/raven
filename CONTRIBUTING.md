# Contributing to Raven

Thanks for working on Raven. A few rules keep this project trustworthy.

## The Truth Rule (non-negotiable)

**No claim ships unless it is true of the code as it exists right now.**

Raven is a discipline tool. If our own docs overstate what we do, we have no
standing to enforce discipline on anyone else. A v3.4 audit found several
documented features that did not exist (live token meter, email notifications,
"always-on" guards) and a skill count that was wrong in four different
directions. That is the exact failure mode this rule exists to prevent.

Before you write a number, a capability, or a "Raven does X" claim:

1. **Verify it against the running code**, not memory and not an older doc.
   - Skill count? `bash plugin/make-plugin.sh` and read "N skills at ZIP root".
   - Guard/hook behavior? Read the script. Confirm it actually fires.
   - A feature? Run it. If it only half-works, say so.
2. **If it is not built, do not document it as built.** "On the roadmap" is fine
   — but mark it clearly, and remove the roadmap note the moment it ships.
3. **No "always-on" language** for things that fire conditionally. Say when they fire.

This is enforced in two places:
- **In-session**: `CLAUDE.md` Rule 5 ("NO DOCUMENTING FEATURES THAT DO NOT EXIST").
- **At commit**: the pre-commit truth-guard check (when `truth-guard.py` is present).

## Counts: always verify, never hardcode from memory

| Thing | How to get the real number |
|---|---|
| Skills shipped | `bash plugin/make-plugin.sh` → "N skills at ZIP root" |
| Guard agents | `ls agents/*.md \| wc -l` |
| Scripts bundled | the build report's "N OSS scripts bundled" line |

## Single source of truth

Some directories are intentionally the canonical source; their mirrors are built
from them, never edited directly:

- **Skills**: root `skills/` is canonical. The plugin build bundles it.
- **Scripts**: root `scripts/` is canonical for the plugin bundle. `raven-core/`
  holds the copies the live `.claude/scripts/` symlinks use — **keep them in sync**
  (they are byte-identical except where a sync is mid-flight).
- **Commands**: `core/commands/` is canonical. The build bundles it.
- **Pre-commit hook**: `core/hooks/pre-commit` is the shipped source.

If you edit a guard/hook script, update **both** `scripts/` and `raven-core/`,
then rebuild the plugin (`bash plugin/make-plugin.sh`) and commit the new ZIP.

## Deletions

Intentional deletions need the flag in the commit message:

```
git commit -m "chore: remove X [GUARD:ALLOW-DELETE]"
```

Note: with `git commit -m`, a pre-commit hook cannot read the message (git writes
it after pre-commit runs). Until that is fixed, pre-populate the message:

```
printf 'chore: remove X [GUARD:ALLOW-DELETE]\n' > .git/COMMIT_EDITMSG
git commit -F .git/COMMIT_EDITMSG
```

## Secrets

Never commit `.raven/manifest.secrets.json`, `.env`, or key files. The secret-scan
guard will block you — but don't rely on it; keep secrets out by habit.

---

MIT — [Giggso](https://giggso.com)
