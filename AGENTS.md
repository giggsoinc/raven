# AGENTS.md — Grok / Codex / Cursor boot

**Codex also reads `AGENTS.override.md` first (same directory). Do not skip it.**

## First load (same UX every IDE)

1. `python3 scripts/ops/raven-first.py --boot` (rebuild + open once). Fallback: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --boot`. Print `host=` `rules=` `memory=` `load=` `educate=` `route=` `expected_route=` `first_load=`.
2. If `load=1`, Read **only** the `memory=` card. If `load=0`, no vault, no invented memory.
3. `python3 scripts/ops/raven-first.py --session-start` — print that banner (version, host, rules, educate, expected SIMPLE/MEDIUM/COMPLEX).
4. Later turns: do **not** re-open the dashboard unless they ask (**raven dashboard** / `/raven-dashboard` → `ide-boot.py --open`).

**0. BEFORE any answer or tool — every user turn. No exemptions.**
- Run `python3 scripts/ops/raven-first.py --prompt "<their full message>"` first. Fallback: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/ops/raven-first.py" --prompt "<their full message>"`. That write fills dashboard **Logs**. Skipping it leaves Logs empty for this IDE.
- Do **not** lead with `bash scripts/raven-python.sh` as the only path — Codex in a public app repo often has no wrapper until raven-first copies the engine from the plugin root.
- There is **no** “direct path” that skips this. Not git log, git status, “what shipped”, smoke tests, or “I didn’t need the router.” Claude PreToolUse **denies** other tools without `.raven/.route-stamp`. Codex/Cursor/AntiGravity/Grok have no that hook — **empty dashboard Logs = you skipped**. That is the proof, not a design exemption.
- **Line 1** = printed `🔀 Router · …`
- **Line 2** = printed `💰 total-cost= last_turn= est=`
- **Line 3** = printed `educate= guided|off` and `expected=<recommend model>`
- **Line 4** = `session=<the model writing this>`
- **Line 5** = `Intent: plan|debug|direct — {why}`
- Then tools/answer. Spawn SIMPLE-tier if this IDE can. Do not only print the toast.
- Recap: `python3 scripts/ops/raven-first.py --end` → `💰 turn= total-cost=` (or `?` if Stop has not priced yet).

**0.5 Intent — line 4:** `Intent: plan|debug|direct — {why}`
- **plan** → Andie / raven-plan. No free-style design.
- **debug** → andie-jr. No ad-hoc brownfield diagnose.
- **direct** → answer/execute; still 🔀 + session=. Never skip as “quick X.”
- Unsure → plan or debug, not skip. Plan vs debug unclear → ask.
- If intent/gate state is contradictory: `Routing state is unclear — I will not guess. [ambiguous]. How do you want me to proceed?` Wait. Does not override Lucky / Educate / Rule 8.
- **Andie HITL:** Andie is not force-loaded. If this turn does not load the Andie skill, stop before the work and show the reason plus an override: `1` load Andie and re-route, `2` continue without Andie. Wait. Do not pick for the user. `Lucky` is still the only full opt-out, and only when the user typed it.

1. Code map: `graph_cli` / `mcp=` when they ask about code. Do not dump OKF at boot.
2. If `educate=guided` (default): briefing (WHAT/HOW/files, ≤200 words) then **STOP**. No Write/Edit/`spawn_subagent` that mutates until the user says **go ahead** / **approved** / **proceed**. `educate off` / Lucky persist in `.raven/educate.json`. Grok/Codex/Cursor/Windsurf/VS Code have no PreToolUse — skipping this loop is the same failure as empty dashboard Logs.
3. **Every user turn:** run `python3 scripts/ops/raven-first.py --prompt "<their message>"` and **show the `🔀 Router` line first**. Then **apply** it: on Grok, SIMPLE → you MUST `spawn_subagent` with `model=grok-4.5` and return that answer; MEDIUM/COMPLEX on Grok stay `grok-4.6`. Do not only print the toast. `applied=true` only after that spawn (or if recommend already is this session model). Never claim Claude models on Grok/Codex.
