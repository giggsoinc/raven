# Changelog

All notable changes to Raven are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [4.1.0] — 2026-06-06

### Patch: Privacy hardening + routing fix

**Privacy hardening:**
- Removed changelog array from `.raven/manifest.json` entirely — cleared historical email exposure.
- Replaced all personal emails (giggso.ravi@gmail.com) with org email (rv@giggso.com) in all JSON registries.

**Critical routing fix (triage-router.py rewrite):**
- **REMOVED** regex-based classification (DEVIATION, EXISTING_SYSTEM, NEW_WORK patterns) — was brittle.
- **IMPLEMENTED** deterministic repo-state routing:
  - Brownfield (>1 commit) → andie-jr for fast triage
  - Greenfield (≤1 commit) → Andie for architecture
  - Data questions (read/explain/show/list) → direct, no skill
  - Force paths (/andie, /andie-jr) always win
- This fixes misclassification of debug prompts as new-work and architectural decisions as bugs.

---

## [4.0.0] — 2026-06-04

### Major: Honesty pass + onboarding + force-paths

**Truth alignment (docs now match code):**
- Rewrote README to remove false/misleading claims — "always-on" guards → event-driven,
  "current session" token counter → previous-session, Obsidian "token reduction" →
  cross-session memory, dropped the "57% savings" perf table and "expert system" framing.
- Corrected skill count to the **verified 61** (was wrongly 60/46/55 across docs).
- Added an Honest ROI section ("when to use, and when NOT to") and per-persona messaging.
- Added `CONTRIBUTING.md` truth-rule: no claim ships unless true of the code now.
- CLAUDE.md rewritten — per-turn discipline contract at top, Raven/Lucky gate,
  Rule 5 (no documenting features that don't exist), real hook names (no PostEdit/PreCommit).

**New capabilities:**
- First-install onboarding fork in Andie: Tour / Setup / Guru; brownfield self-discover
  (≤2 Qs) vs greenfield (5–7 Qs).
- `/andie` + `/andie-jr` force-path commands — and the plugin now **bundles commands**
  (previously zero shipped). 12 commands in the ZIP.
- `notify.py` — real SMTP + Slack notifications wired into the pre-commit gate.
- `install-claudemd.py` — append-only CLAUDE.md installer (never deletes user content).
- Plain-English, help-toned guard messages (secret-scan, db-guard).
- Session-start transparency banner + progressive disclosure.

**Hygiene:**
- Removed stale `plugin/skills/` mirror; single source of truth = root `skills/` (61).
- Synced divergent copies (`scripts/` ↔ `raven-core/`, live ↔ repo pre-commit hook).
- Plugin zip: `raven-plugin-v4.0.0.zip`.

---

## [4.0.0] — 2026-06-01

### Storage Architecture Refresh

- Plugin manifest bumped to v4.0.0.
- Description updated to reflect current architecture.
- 60 skills, 11 agents — unchanged from prior version.
- Plugin zip rebuilt: `raven-plugin-v4.0.0.zip`.
- Backwards-compatible with v4.0.0 — structural updates only.

---

## [4.0.0] — 2026-05-27

- Andie v6.3 routing refresh.
- Auto-trigger fixes for andie/andie-jr/andie-guru.
- Guard audit + notification fix.

---

## [3.0.0] and earlier

See git history.
