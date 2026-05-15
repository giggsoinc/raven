# Raven Observation Log

Maintained by the Task-Observer meta-skill. Written silently during sessions.
Every vulnerability found, correction made, or new pattern learned is logged here.
Reviewed during `/raven-harden` to promote permanent rules into CLAUDE.md and curated skills.

**Format:** Issue → Suggested Improvement → Principle
**Review cadence:** Run `/raven-harden` when log has 5+ new entries or after significant sessions.

---

## Index

| # | Date | Platform | Type | Status |
|---|---|---|---|---|
| 1 | 2026-05-14 | Raven plugin | YAML bug | closed |
| 2 | 2026-05-14 | Raven plugin | Duplicate agent name | closed |
| 3 | 2026-05-14 | Raven plugin | Missing frontmatter | closed |
| 4 | 2026-05-14 | bundle.sh | Wrong source-of-truth | closed |
| 5 | 2026-05-14 | raven-codex | Stale plugin file | closed |
| 6 | 2026-05-14 | All READMEs | Wrong specialist count | closed |
| 7 | 2026-05-14 | raven-codex | Misleading moved tombstone | closed |
| 8 | 2026-05-14 | raven-setup.sh | Broken raven-register path | closed |
| 9 | 2026-05-14 | sr-02 install | Missing hook scripts | closed |
| 10 | 2026-05-15 | Task-Observer | Never fires in sessions | open |

---

## Observations

<!-- New entries appended below by Task-Observer. Most recent first. -->

---

### [2026-05-15] — Task-Observer / Meta

**Issue:** Task-Observer skill is defined but never actually fires during sessions — log stayed empty through a full week of significant changes.
**Suggested improvement:** Add explicit invocation in CLAUDE.md boot sequence and/or wire to PostEdit hook so it auto-appends after each session.
**Principle:** A log no one writes to is a false sense of observability. Observer must be active, not aspirational.
**Status:** open

---

### [2026-05-14] — raven-codex / Plugin install

**Issue:** `.codex-plugin/plugin.json` was at v2.8.0 with a hardcoded `skills` array of only 4 entries. Installing `giggsoinc/raven-codex` gave users 15 skills instead of 49 because Claude read the stale explicit list, not the directory.
**Fix:** Updated `.codex-plugin/plugin.json` to v2.9.1 with all 49 skills explicitly listed.
**Principle:** Plugin files with explicit skills arrays shadow directory scanning. Any explicit list must be kept in sync with the actual skills/ directory or removed in favour of directory scanning.
**Status:** closed

---

### [2026-05-14] — All READMEs / Counts

**Issue:** `claude_plugin_readme.md` quoted 33 specialists in three places. `raven-codex/README.md` quoted 49. Actual count is 23 named specialists.
**Fix:** Updated all occurrences to 23.
**Principle:** Counts in documentation must be derived from the actual directory, not estimated or carried forward from planning docs. Automate the count or keep it deliberately vague ("20+ specialists") until it's stable.
**Status:** closed

---

### [2026-05-14] — raven-codex / README

**Issue:** `raven-codex/README.md` said "This repo has been consolidated into the giggsoinc/raven monorepo" — a tombstone from a decision that was reversed. We then pushed 65 files of active content into the same repo. Any AI reading the README was being redirected away from the live plugin.
**Fix:** Replaced the tombstone with an active plugin README.
**Principle:** Archived/moved messaging must be removed the moment a repo is made active again. Stale tombstones misdirect both humans and AI agents.
**Status:** closed

---

### [2026-05-14] — bundle.sh / Source of truth

**Issue:** `core/agents/claude-mem.md` had unquoted YAML description (colons in `At start:` / `At end:` broke the parser). `core/agents/guard-git-watch.md` had `name: skill-guard` (copy-paste from skill-guard.md — caused duplicate agent name on plugin validation). `core/commands/raven-init.md` had no frontmatter. bundle.sh copies `core/` → root, so running it overwrote previous fixes applied only to root files.
**Fix:** Fixed all three source files in `core/`. Root files now stay correct through bundle runs.
**Principle:** bundle.sh treats `core/` as the source of truth. All fixes must be applied to `core/` first, not to the generated root output. Fixing the output without fixing the source creates a regression on the next bundle run.
**Status:** closed

---

### [2026-05-14] — Raven plugin / YAML validation

**Issue:** `agents/claude-mem.md` failed plugin validation with "mapping values are not allowed here" — YAML parser choked on colons inside an unquoted multi-line description field.
**Fix:** Wrapped the description value in double quotes.
**Principle:** Any YAML string containing `: ` (colon-space) must be quoted. This applies to all agent and skill frontmatter descriptions. Validate with `python3 -c "import yaml; yaml.safe_load(open(f).read())"` before packaging.
**Status:** closed

---

### [2026-05-14] — Raven plugin / Duplicate agent name

**Issue:** `agents/guard-git-watch.md` had `name: skill-guard` — a copy-paste error from `skill-guard.md`. Plugin validator rejected the package with "duplicate agent name".
**Fix:** Changed to `name: guard-git-watch`.
**Principle:** The `name:` field in agent frontmatter must match the filename (without `.md`). A validation script should check `name == basename(file)` across all agents before any plugin packaging step.
**Status:** closed

---

### [2026-05-14] — Raven plugin / Missing skill frontmatter

**Issue:** `skills/raven-init/SKILL.md` had no YAML frontmatter — migrated from `commands/raven-init.md` which also had none. Plugin validator silently skipped it; Claude Code would not load the skill.
**Fix:** Added frontmatter block with `name`, `description`, `allowed-tools`.
**Principle:** Every SKILL.md must open with a valid YAML frontmatter block. The migration script from `commands/` → `skills/*/SKILL.md` must carry frontmatter or generate it.
**Status:** closed

---

### [2026-05-14] — raven-setup.sh / Broken path

**Issue:** `RAVEN_REGISTER` path used `dirname "$SR_REPO_DIR"` which walked up one directory too many — pointed to `SHAY-ROLLS/CLAUDE/` instead of staying in the RAVEN repo.
**Fix:** Changed to `"$SR_REPO_DIR/raven-core/registry/raven-register.py"`.
**Principle:** Path construction from dynamic variables must be tested by echoing the resolved path before use. `dirname` on a directory path removes the last component — use with care when the variable is already a directory.
**Status:** closed

---

### [2026-05-14] — sr-02 install / Missing hook scripts

**Issue:** `settings.json` hooks reference `tool-guard.py`, `token-guard.py`, `skill-search.py`. `sr-02-install-files.sh` only copied from `raven-core/*.py` — missing the `core/scripts/` files entirely. Hooks would fail silently on every project setup.
**Fix:** Added `cp core/scripts/*.py` and `cp core/scripts/*.sh` step to sr-02.
**Principle:** The install script must be tested end-to-end against a clean project directory. Every file referenced in `settings.json` hooks must be verified present after install runs.
**Status:** closed
