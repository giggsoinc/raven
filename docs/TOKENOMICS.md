# Raven Tokenomics — Where Tokens Go, and Where They Don't

Raven's discipline layer is designed around one rule: **enforcement runs in
Python, outside the model — it costs zero tokens.** Tokens are only spent when
text actually enters the model's context. This note itemizes every charge so
nobody burns budget guessing.

## The zero-token tier (most of Raven)

These run as hook scripts on your machine. The model never sees them, so they
cost **0 tokens** regardless of how often they fire:

| Component | Hook | Token cost |
|---|---|---|
| raven-skill-gate.py (edit gating) | PreToolUse, every Edit/Write | **0** |
| raven-mark-skill.py (marker stamp) | run via Bash by a skill | 0 (the call itself ~100 tok, once per session) |
| secret-scan.py, db-guard.py | PostToolUse (async) | **0** |
| pre-commit gate (secrets, CVE, style, notify) | git, not Claude | **0** |
| token-guard.py, obsidian-log.py | Stop | **0** |
| Audit logs, observation logs, dashboards | filesystem | **0** |

## The token-bearing tier (what enters context)

| Item | Frequency | Approx. tokens |
|---|---|---|
| Session-start greeting + transparency banner | once per session | ~400–600 |
| Skill-reminder injection | every message | ~40–60 |
| Router toaster `additionalContext` (triage/architect/model) | every message | ~40–60 |
| Gate banner line (only when a routing policy is active) | once per session | ~30 |
| Marker Bash call + result | once per gated skill invocation | ~100 |
| Soft warning / hard block message | only on a violation | ~40–60 |
| Specialist SKILL.md load (andie, andie-jr, domain specialist) | once per session, when actually used | ~1,000–2,000 |

**Steady-state overhead: ~100 tokens per message** (reminder + toasters),
plus a one-time ~500-token session boot. On a typical 30-message session
(~150k tokens of real work), Raven's governance overhead is **~3.5k tokens —
roughly 2%.**

## Where Raven SAVES tokens

- **Model routing** (`model-router.py`): SIMPLE prompts route to cheap tiers,
  LOCAL_ONLY routes secret-laden context to a free local model. The router
  itself is a hook — 0 tokens to classify.
- **Mode-split skills**: Andie loads only the selected mode file, not all
  four — that's the difference between ~1.5k and ~6k tokens per invocation.
- **One-skill-load guarantee**: the skill gate doesn't add skill loads — it
  makes the one load you already wanted happen *before* edits, instead of
  after a wasted wrong-direction edit cycle (a single bad edit + revert loop
  typically burns 3–10k tokens; the gate's lifetime cost is ~130).
- **Token thresholds** (25/50/75/90%): warnings fire from hooks, costing
  nothing until the warning text itself (~30 tok) is shown.

## The honest line

Governance that lives in context costs tokens every message; governance that
lives in hooks costs none. Raven pushes everything enforceable into hooks and
keeps only the *advisory* layer in context — and keeps that layer terse on
purpose. If a future feature proposes per-message context injection, the bar
is: does it earn back more than ~60 tokens × every message of every session?
