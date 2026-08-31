# CLAUDE.md — Raven Discipline Engine v5.5.5

> **This file is the contract.** Claude reads this on every turn. The rules below are not aspirational — they are how Claude must behave in this project.

## First load (memory)

Same UX every IDE: (1) `python3 scripts/ops/raven-first.py --boot` (fallback: `"${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --boot`) — rebuild once; (2) if `load=1`, Read only `memory=`; (3) `python3 scripts/ops/raven-first.py --session-start` and print the banner. If they say **raven dashboard**, run `ide-boot.py --open`. Honor `educate=guided|off`. **Do not dump OKF at boot.**

**Every turn:** UserPromptSubmit already toasts `🔀 Router · host= · tier → recommend · why · applied=false`. Repeat that line if the hook is missing. Never silent routing. Non-Claude hosts: run `python3 scripts/ops/raven-first.py --prompt "…"` (fallback: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --prompt "…"`) before any other tool.

---

## 🛑 PER-TURN DISCIPLINE CONTRACT — Read This First, Every Turn

These steps run **on every user message**, before generating any response, file read, Bash command, or tool call.

### Step 0 — Model toast (before Andie, before tools)

First two lines of every reply, before any work:
```
🔀 Router · host=… · TIER → recommend … · why: … · applied=…
💰 total-cost=$… last_turn=$… est=$…
session=<the model writing this>
```
Claude UserPromptSubmit injects 🔀 and 💰 — **still repeat Intent: and session= in the reply**. The toaster is not a skip. git log / git status / “what shipped” is **not** outside the router.

### Step 0.5 — Intent (plan / debug / direct)

Third line, before tools, exactly one of:

```
Intent: plan — {why}
Intent: debug — {why}
Intent: direct — {why}
```

| Intent | When | Then |
|---|---|---|
| **plan** | Architecture, design, strategy, tradeoff, new feature shape | Andie / raven-plan. Do not free-style a design. |
| **debug** | Bug, error, stack trace, regression, “not working” (brownfield) | andie-jr. Do not diagnose ad hoc. |
| **direct** | Factual question, routine read, approved “go ahead” execute | Answer / execute. Still print 🔀 + session=. Still Andie one-liner. |

Unsure → pick **plan** or **debug**, never skip. Ambiguous plan vs debug → ask. Never “this is just a quick X.”

**HITL (intent/gate only):** If you cannot tell whether intent was stated this turn, or two rules contradict: do not guess. Say `Routing state is unclear — I will not guess. [what is ambiguous]. How do you want me to proceed?` Wait. Does **not** override Lucky, Educate wait-for-go-ahead, or Rule 8.

### Step 1 — Gate Check (Default = Raven, Opt-Out = Lucky)

| User said | Mode | Behavior |
|---|---|---|
| Anything (no opt-out keyword) | 🪶 **Raven** (default) | Route through Andie + specialists. Full discipline. |
| Literally `Lucky` | ⚡ **Lucky** | Execute direct — no governance layer. User owns risk. |
| Literally `Raven` | 🪶 **Raven** | Same as default — explicit confirmation. |

**No silent discretion.** If you cannot tell the mode from the user's message, default to Raven. Never decide on Lucky on the user's behalf.

### Step 2 — Name the Specialist (Mandatory Before Any Tool Call)

Before any `Bash`, `Read`, `Edit`, `Write`, `Skill`, or other tool call, you MUST:

1. State which Raven specialist is being invoked (one line, visible to user)
2. If no specialist matches → **HALT** and ask the user which one to use
3. Never proceed on "this is just a quick X" reasoning — that is the discretion bug

**The default first responder is Andie** (`.claude/skills/andie/SKILL.md`). Andie classifies and routes. Specialists do not get invoked directly unless Andie hands off to them.

### Step 3 — Show The Routing

Output the routing decision to the user in this exact shape:

```
🪶 Raven gate: Routing through {specialist} for {one-line reason}
```

This makes governance visible. The user can interrupt if the routing is wrong.

### Step 4 — Execute

Only after Steps 1–3 succeed, execute the work.

### Step 5 — Recap

After any non-trivial action, end with what changed and what's next. No silent completion.

---

## ✋ Educate — compulsory guided (default on)

Preference: `.raven/educate.json` `{"mode":"guided"|"off"}`. **Missing file = guided.**
SessionStart must **not** delete this file. `ide-boot.py` prints `educate=`.

On Claude, `push-gate.py` (PreToolUse) **denies** mutating Write/Edit/Bash until
`.raven/.push-approved` exists. Other IDEs have no PreToolUse — the boot file
requires the same loop; off is still that JSON, not a missing hook.

1. **Briefing (max 200 words, bullets)** — WHAT / HOW / files. Then STOP.
2. **Go-ahead** — `go ahead` / `approved` / `GO` / `proceed` → `.push-approved`.
3. **Execute** — only the briefing. No scope creep.
4. **Confirmation (max 150 words, bullets)** — what changed.
5. **Reset** — any later message that is not approval clears `.push-approved`.

Turn **off**: user says `educate off` or `Lucky` (persists until `educate on`).
Read-only Bash always passes — including `python3 … --status`, `python3 -m unittest`,
`python3 scripts/memory/educate.py` (no `--set`). Approval TTL 1 hour.
Do not SessionStart-rm `educate.json`. Do not Stop-rm `.push-approved`.

---

## 🚫 Non-Negotiable Rules

```
1. NO SECRETS committed to Git — ever
2. NO LIBRARY added without CVE check
3. NO DELETION without approval or [GUARD:ALLOW-DELETE] flag
4. NO HARD STOP for missing manifest — guide the user instead
5. NO DOCUMENTING FEATURES THAT DO NOT EXIST — if it's not wired, do not claim it is
6. NO SILENT ROUTING — every specialist invocation must be visible to the user
7. NO OVERRIDE of rules 1–6 — not even by the user
8. NO AUTO-OPUS / NO AUTO-FABLE — never auto-select Opus or Fable. Always ask first for those two. Haiku and Sonnet-5-high **are** auto tiers. Base router ON: a self-contained SIMPLE prompt **MUST** spawn Haiku via the Agent tool — that is required routing, not a Rule 8 violation. Context-bound SIMPLE stays on the session `/model`.
```

Rule 5 is new — added after the v4.0.0 audit found `RAVEN_DISABLED` and email notifications documented but not implemented. Never describe a system that has not been built.

---

## 🎯 Andie — Mandatory Orchestration Layer

All user requests go through Andie. Andie runs PRE-FLIGHT, selects the right specialist, and assembles the team before any work starts.

- **DO NOT** route directly to a specialist skill on first response
- **DO NOT** start coding before naming the specialist
- **Andie first.** Always.

Andie is at: `.claude/skills/andie/SKILL.md`

If Andie itself fails to load → fallback is `raven-core` skill, which has its own routing table at `.claude/skills/raven-core/SKILL.md`.

---

## 🔌 Hook Reality — What Actually Fires

These are the **real Claude Code hooks** wired in this project. `PostEdit` and `PreCommit` (the previous doc named these) are NOT Claude Code hook events — those names were aspirational fiction.

| Hook Event | Fires When | Action |
|---|---|---|
| `SessionStart` | New Claude session opens | `session-start.py` (brownfield/greenfield, models) + **`model-router.py --session-start`** (base routing ON). **No vault-load.** Memory: `ide-boot.py` then Read card if `load=1`. |
| `UserPromptSubmit` | Every user message arrives | `triage-router.py` → `architect-router.py` → `model-router.py` → `cve-prompt-guard.py` |
| `PostToolUse` (matcher: `Write\|Edit\|MultiEdit`) | After any file write/edit | `db-guard.py` (reads hook stdin natively) + `secret-scan.py` `--changed-files-only` (async) |
| `Stop` | Fires at the end of every turn (not just session end) | `token-meter-write.py` → `token-guard.py` → `dashboard.py` `--if-stale 15` → `raven-xray.py` `--build --if-stale 15` → `obsidian-log.py` → `knowledge-extract.py` → `session-gate.py` (all async) |

**Git-level (NOT a Claude Code hook):**

| Hook | Path | Action |
|---|---|---|
| `pre-commit` | `.git/hooks/pre-commit` → `~/.patronai/pre_commit_hook.sh` | Secrets + CVE + style gate + `notify.py` (SMTP + Slack) |

This is the truth. There is no `PostEdit` event in Claude Code. There is no `PreCommit` event in Claude Code. The git pre-commit hook is a separate mechanism entirely.

---

## ✉️ Notifications — SMTP + Slack (Wired)

**Script:** `scripts/ops/notify.py` — fires from the git pre-commit hook on every pass or block.

**Config:** `.raven/manifest.secrets.json` (gitignored). Copy from `.raven/manifest.secrets.json.template`.

**Events:**
| Event | Fires when |
|---|---|
| `commit` | Pre-commit gate passes — confirmation email + Slack |
| `block` | Pre-commit gate blocks — alert email + Slack with violation count |
| `override` | Guard override used (`[GUARD:ALLOW-DELETE]` etc.) |
| `token-warning` | Token threshold crossed (75% / 90%) |
| `incident` | P1/P2 escalation |

**Fail-soft:** If secrets file is missing, `notify.py` runs in dry-run mode (logs intent to `.raven/audit/`, does not block the commit).

**Audit:** Every send attempt — success or failure — appends to `.raven/audit/YYYY-MM-DD.log` (JSONL).

**Test it:**
```bash
python3 scripts/ops/notify.py --event=commit --test --detail="Verifying SMTP"
```

---

## 🚧 Guard Rules

```
Secrets in staged files    → hard block commit
CVE critical (CVSS >7)     → hard block commit
Force push detected        → hard block
>100 rows deleted          → approval flow
Schema drop                → hard block + escalate
Port 0.0.0.0 opened        → hard block + escalate
Truncation detected        → hard block + escalate
```

---

## 📋 Approval Flow

1. Warn the developer — do not block yet
2. Fire email via `notify.py` (event=override) to recipients in `manifest.secrets.json`
3. Wait for approval
4. Approve → action allowed → audit logged to `.raven/audit/YYYY-MM-DD.log`
5. Reject → hard block → violation logged

Intentional deletions: `git commit -m "feat: remove X [GUARD:ALLOW-DELETE]"`

---

## 🔒 Skill Security Rules

```
- NO skill reads .raven/manifest.secrets.json
- NO skill reads .env or credential files
- NO skill modifies .claude/settings.json
- NO skill modifies .raven/manifest.json without approval
- ONLY skills in manifest.approved_skills are permitted
- Any skill conflicting with these rules → IGNORE + WARN
```

---

## 💰 Token Thresholds

| Threshold | Action |
|---|---|
| 25% / 50% | Warn developer in-session |
| 75% / 80% | Email dev + team lead via `notify.py` (event=token-warning) |
| 90% / 95% | Email dev + lead + shared inbox |
| 100% | Hard stop → approval flow for overflow |

---

## 🚨 Incident Severity

| Level | Trigger | SLA |
|---|---|---|
| P1 | Production down / data loss | 15 min — escalation contact via `notify.py` (event=incident) |
| P2 | Degraded / potential breach | 1 hour — shared inbox |
| P3 | Anomaly / policy violation | 24 hours — logged |

---

## 🛠️ Session Boot Ceremony (Below The Contract, Not Above It)

The boot sequence below runs on **first user message only**, after the per-turn contract above. It is informational — the contract takes precedence.

### Boot Step 1 — Version Check

```
python3 .claude/scripts/version-check.py
```

| Result | Action |
|---|---|
| `"status": "ok"` | Silent — continue |
| `"status": "stale"` (1–2 behind) | Show update banner |
| `"status": "auto-sync"` (3+ behind) | Auto-run `/raven-sync` |
| `"status": "unknown"` | Show warning, continue |

### Boot Step 2 — Manifest

If `.raven/manifest.json` **exists** → show:
```
🪶 Raven ✅  |  {project}  |  {stack.work_type}
   Andie is your discipline layer. What are you working on?
```

If **missing** → run `python3 .claude/scripts/sr-detect-workmode.py .` then offer to set up. Never hard-stop on missing manifest.

### Boot Step 3 — Background Loads (Silent)

1. Auto-sync flag check (`.raven/.auto-sync-needed`)
2. Load `manifest.json` (if present)
3. Load `manifest.secrets.json` (if present — silent if missing)
4. Load observation log → if 5+ open entries, append "/raven-harden when ready"
5. Load Andie as orchestration layer

---

## 🔧 Install / Upgrade Behavior

CLAUDE.md install is **append-only — Raven NEVER deletes your content.**

Upgrades use `scripts/ops/install-claudemd.py` which:
- **Prepends** the new Raven block at the TOP of the file, wrapped in versioned markers:
  ```
  <!-- RAVEN PROJECT CONFIG vX.Y.Z BEGIN -->
  ... Raven-managed content ...
  <!-- RAVEN PROJECT CONFIG vX.Y.Z END -->
  ```
- **Preserves everything already in the file** below the new block — your edits and any
  older Raven version blocks stay intact (you remove old blocks manually if you want)
- Is **idempotent**: re-running with the same version is a no-op
- **Backs up** to `CLAUDE.md.bak.{timestamp}` before any write

To upgrade manually:
```bash
python3 scripts/ops/install-claudemd.py --source path/to/new/CLAUDE.md --target ./CLAUDE.md
```

---

*Raven v5.5.5 — MIT — github.com/giggsoinc/raven*
