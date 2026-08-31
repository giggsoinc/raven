# Changelog

All notable changes to Raven are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

---

## [5.5.5] — 2026-08-31 — obs spend, refresh, repo filter

- Observability actual spend from cost-log; pre-turn est labeled not billed.
- Refresh stays put if dashboard-server is down; repo filter on Costs/Obs.

## [5.5.4] — 2026-08-23 — GitHub version banner on session start

- Session start + first router turn: current vs GitHub latest; upgrade prompt; 5 bullets.

## [5.5.3] — 2026-08-23 — plugin-root first-load

- Current zip: `plugin/raven-plugin-v5.5.3.zip`. Tag `v5.5.3`.
- `scripts/ops/raven-first.py` finds the plugin engine and copies it into any cwd.
- `host-ensure` now copies `scripts/{routing,memory,session,ops}` when missing.
- AGENTS / Cursor / Windsurf / VS Code / Gemini / Replit lead with raven-first (not raven-python.sh alone).

## [5.5.2] — 2026-08-23 — first-load all IDEs

- Current zip: `plugin/raven-plugin-v5.5.2.zip`. Tag `v5.5.2`.
- Unified first-load: ide-boot → memory card → session-start → every-turn router (Cursor/Windsurf/VS Code/Gemini/Replit included).
- `ide-boot` prints `first_load=`; session-start lists host rules + educate + tiers.

## [5.5.1] — 2026-08-23 — host router + educate; install pin

- Current zip: `plugin/raven-plugin-v5.5.1.zip`. Tag `v5.5.1`.
- Session/prompt start prints version, educate, expected SIMPLE/MEDIUM/COMPLEX.
- Global Claude: `model-router.py --hook` + deny-mode push-gate.

## [5.5.0] — 2026-08-22 — one plugin, every host

- One zip: `plugin/raven-plugin-v5.5.0.zip` (`bash plugin/make-plugin.sh`, version from `raven-core/VERSION`).
- Host glue in the zip: `AGENTS.md`, `.agents/agents.md`, `.cursor/rules`, `.windsurf/rules`, `GEMINI.md`, `replit.md`, `CLAUDE.md`, `install-host.sh`.
- Claude loader still `.claude-plugin/`. Not a second plugin.
- Scripts packaged from canonical `scripts/` subtrees (router, cost, dashboard).
- Dashboard Overview above Graph; costs grouped by repo then IDE; graph file open via local `/api/open`.

## [Unreleased] — agent boot card + IDE router

- **Stop** writes `.raven/memory/CARD.md` (in-repo). Vault stays `~/RavenVault` for humans.
- **SessionStart** no longer runs `vault-load.py`. `vault-load.py` is manual only.
- **First load:** `scripts/memory/ide-boot.py` + `.raven/boot.json` (`load=0|1`).
- Hosts: Claude (`CLAUDE.md`), Grok/Codex/Cursor (`AGENTS.md`), AntiGravity (`.agents/agents.md`), Windsurf, Replit (`replit.md`), Gemini (`GEMINI.md`).

---

## [4.3.0] — 2026-08-04

### Tokenomics metering + vibe-coder dashboard

**Token metering (new):**
- `token-meter-write.py` — Stop hook that reads the session transcript JSONL,
  extracts token usage, calculates cost, and writes metrics to three files:
  per-session JSON, monthly rollup, and audit log. Non-blocking, fail-soft.
- Session-end meters in `session-gate.py`: every session close prints
  `📊 Session meters: <tokens> tok · $<cost> · <raven/user> calls`.
- Metering state lives under `.raven/state/` (new, per-project).

**Dashboard (major upgrade — `dashboard.py`):**
- Tokenomics view: Raven-metered usage side-by-side with Claude/external-reported
  usage (`load_external_usage` + editable template so users can paste Claude's
  own numbers for comparison).
- Cost-compare section rendered into the HTML dashboard at `~/RavenVault/dashboard.html`.
- Dashboard is rebuilt on every session start/end; manual rebuild:
  `python3 scripts/dashboard.py --html --open`.

**Knowledge-graph icons (vibe-coder UI):**
- New `kg_icons.py` + `assets/kg-icons/*.svg` — tiny SVG icons inlined as
  data-URIs so `file://` dashboards work fully offline (no CDN).
- Graph nodes now carry picture-dictionary icons: 📦 project, 💡 concept,
  ✅ decision, ⏱️ session, 🔐 login, 🛡️ security, 🗄️ database, 🔌 api,
  🖥️ ui, 💳 money, ☁️ cloud, 🔄 workflow, 💻 code.
- `knowledge_graph.py` / `knowledge-extract.py` updated to classify and tag nodes.

**Docs (new):**
- `docs/VIBE-CODER-MAP.md` — zero-code guide to reading the picture map.
- `docs/DASHBOARD.md` — what the dashboard shows and how to rebuild it.
- `docs/RAVENVAULT-GRAPH-AND-MEMORY.md` refreshed for icons + metering.

**Plumbing:**
- `.claude/scripts/` now ships the full hook script set (dashboard,
  knowledge-extract, knowledge_graph, obsidian-log, session-gate,
  session-start, token-meter-write, vault-load, vault_common).
- `plugin/make-plugin.sh` + `plugin/settings.json` package the new scripts.

---

## [4.2.0] — 2026-07-xx

RavenVault knowledge graph & agent memory. Full details:
[docs/CHANGELOG-4.2.0-vault-graph.md](docs/CHANGELOG-4.2.0-vault-graph.md).

---

## [4.1.x unreleased work] — 2026-06-10

### Andie v6.4 + routing visibility + LOCAL_ONLY hard floor

**Andie v6.4 (ported into the compact structure — token efficiency kept):**
- One hard gate: mode card + pre-flight assembly arrive in ONE message with ONE GO.
- Implicit GO: a file upload, pasted document, or an answer at any gate counts as
  consent. Ask-once: no gate is ever re-asked; ambiguity → state default and move on.
- GATES ledger: every OODA block carries a `GATES: passed | open` line.
- Critic voice on every team (Devil's Advocate / Critic / Red Team / Saboteur) +
  the user holds a named seat with the casting vote.
- Invocation toaster: Andie's (and Andie Jr v1.1's) first line always announces
  what is running, what triggered it, and what happens next. Never "background".

**Routing (triage-router v4.2 — no double-fire):**
- Precedence made mutually exclusive: decision/architecture prompts → andie
  (architect-router); triage-router stays silent instead of also firing andie-jr.
  triage loads architect's classifier dynamically — one source of truth, fail-soft.
- Symptom language now overrides the data-question check ("why is auth failing"
  → andie-jr, matching the documented trigger table).
- Both routers + model-router (`--hook`, now wired in plugin settings.json) emit
  a user-visible one-line `systemMessage` toaster on every route. Raven never
  routes silently. `router_common.py` added and packaged with the plugin.

**LOCAL_ONLY visibility (privacy):**
- model-router `--hook` mode: secrets-detected prompts show a
  `🔒 … LOCAL_ONLY · cloud subagents blocked` toaster and inject explicit
  do-not-spawn-cloud guidance for subagents.

**Skill-routing gate (deterministic enforcement — new):**
- `raven-skill-gate.py` (PreToolUse on Edit/Write/MultiEdit/NotebookEdit):
  edits are blocked (mode: hard) until a gated specialist skill has actually
  run this session — same two-tier model as commits (advise while coding,
  block at the boundary). Gates the ACTION via marker files; never tries to
  classify prompts in the hook.
- `raven-mark-skill.py`: enforced skills (andie, andie-jr) run it as their
  first step; the script — not the model — stamps `{ts, skill, session_id}`
  into `.raven/state/skill-invocations.jsonl`.
- Modes shadow/soft/hard/off via `.raven/state/routing-policy.json`
  (template shipped); soft is the default grace mode. Override touch-file
  allows N calls, always audited — never silent. No policy file → gate off.
- Banners rewritten to the honest contract: when the gate is active they say
  "enforced at edit time by raven-skill-gate (mode: X)" instead of
  unenforceable "MANDATORY: invoke X before any file read".
- Zero-token design: gate + marker run outside the model (~130 tokens total
  per session for the visible messages, none per tool call). Latency budget
  <100ms covered by tests (`tests/test_skill_gate.py`, 9 cases).
- Docs: `docs/SKILL-GATE.md` — including the stated residual gap (the gate
  proves the skill ran, not that its output was used well).

**Domain detection precision (false-positive Oracle fix):**
- `DOMAIN_SKILL_MAP` (session-start.py + raven-skill-reminder.py): removed the
  `**/*.sql` Oracle glob — it branded any repo containing a single .sql file
  (migrations, SQLite schemas, fixtures) as Oracle and shadowed later entries
  like FastAPI (observed in the Rex project). Oracle now requires `.pkb`/`.pks`,
  `tnsnames.ora`, or `cx_Oracle`/`oracledb` in dependencies.
- Same audit applied map-wide: `charts/` dir removed from Kubernetes (matched
  JS charting folders; `Chart.yaml` marker added); AWS `template.yaml` demoted
  to a content check (`AWS::`).
- `detect_domain` now returns signal strength: strong (marker / proprietary
  extension / dependency keyword, or two agreeing weak signals) → mandatory
  banner; weak (single generic dir) → advisory "consider invoking" hint only.
  Strong matches win over earlier weak ones — no more shadowing.
- Regression suite: `tests/test_domain_detection.py` (10 fixtures, both hook
  copies tested). All script copies (scripts/, plugin/scripts/, raven-core/)
  synced checksum-identical.

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
  cross-session memory, dropped the "57% savings" perf table and the misleading framing (it's prompt templates + routing, described as such).
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
- 61 skills, 11 agents — unchanged from prior version.
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
