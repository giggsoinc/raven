# raven-skill-gate — Deterministic Skill-Routing Enforcement

Raven's specialist routing used to be advisory-only: SessionStart /
UserPromptSubmit banners *asked* the model to invoke a specialist, and the
model decided whether to comply. This gate applies the same two-tier model
Raven already uses for commits — advise while coding, hard-block at the
boundary — to skill routing: **Claude cannot modify code until the required
specialist skill has actually run.**

## Design — gate the action, not the intent

A hook cannot semantically detect "this prompt was a bug report," so the gate
never classifies prompts. It enforces a workflow invariant via marker files:

1. **Marker emission** — each enforced skill's SKILL.md instructs the model,
   as its first step, to run:

   ```
   python3 .claude/scripts/raven-mark-skill.py andie-jr
   ```

   The script appends `{ts, skill, session_id}` to
   `.raven/state/skill-invocations.jsonl`. The *script* stamps the timestamp —
   the model cannot forge freshness.

2. **PreToolUse gate** — `raven-skill-gate.py` runs before every
   `Edit | Write | MultiEdit | NotebookEdit`. It reads
   `.raven/state/routing-policy.json` and blocks (exit 2) when policy requires
   a specialist and no fresh marker exists.

## Configuration

Copy `routing-policy.example.json` to `.raven/state/routing-policy.json`:

| Field | Meaning |
|---|---|
| `mode` | `shadow` (log only) · `soft` (warn — default) · `hard` (block) · `off` |
| `required_skills` | any one fresh marker from this list satisfies the gate |
| `scope` | globs of gated paths; `[]` = everything not excluded |
| `exclude` | never-gated globs (default: docs, markdown, `.raven/`) |
| `freshness_hours` | fallback window when no session stamp exists (default 4) |
| `override_uses` | tool calls one override touch allows (default 3) |

**No policy file → gate is disabled** (exits in <5 ms). New installs should
run `soft` for a week, then switch to `hard` — the same grace-period pattern
as architecture-guard.

**Freshness**: a marker counts if its `session_id` matches the current
session, or it is newer than `.raven/state/.session-start` (touched by
session-start.py), or — when no stamp exists — it falls inside
`freshness_hours`.

## Escape hatch (never silent)

```
touch .raven/state/gate-override
```

allows the next N tool calls. Every override use is appended to
`.raven/audit/YYYY-MM-DD.log`. Discipline with accountability, not a lockout.

## Enforcement modes at a glance

| Mode | Blocks? | Logs? | Warns? |
|---|---|---|---|
| shadow | no | audit + `docs/observations/security_log.md` | no |
| soft | no | same | yes (stdout) |
| hard | **yes** (exit 2) | audit | block message |

## Token cost

The gate and marker scripts run **outside the model — zero tokens per tool
call**. Token costs only appear when something is shown to the model: a hard
block message (~60 tokens, once), a soft warning (~40 tokens), the one-line
marker Bash call a skill runs (~100 tokens once per session), and the
one-line banner notice (~30 tokens at session start). Steady-state overhead
on a clean session is ~130 tokens total, not per message.

## Deployment

- Source of truth: `scripts/` in this repo (same as session-start.py); the
  plugin build packages both scripts and the example policy into the zip, and
  `plugin/settings.json` registers the PreToolUse hook.
- Existing installs pick the hook up via `raven-registry-sync` or re-install.
  Deployed copies live in `~/.claude/scripts/` — sync, don't hand-edit.

## Honest contract

This gate guarantees the specialist skill **ran** this session. It does not —
and cannot — guarantee the skill's output was understood or used well. That
residual gap is inherent to LLM systems and is stated here rather than
papered over.
