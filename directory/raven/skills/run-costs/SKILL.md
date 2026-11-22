---
name: run-costs
description: "Real cloud billed cost (when API keys are in env) plus local calculator. Use when the user says run-costs, /run-costs, actual cost, billed cost, or session cost."
---
# /run-costs

Commands for the user to review and run themselves:

```text
python3 scripts/session/run_costs.py
```

Always prints the **local calculator** (`spend_kind` / turn-log + cost-log).

**Cloud billed $** only if these are already in the environment (script never reads `manifest.secrets.json`):

- Claude: `ANTHROPIC_ADMIN_API_KEY` or `ANTHROPIC_API_KEY` → Anthropic Cost Report
- Codex: `OPENAI_ADMIN_KEY` or `OPENAI_API_KEY` → `GET /v1/organization/costs` (admin key)
- Grok: `XAI_API_KEY` → xAI usage if the URL responds; else the console link

Writes `.raven/.run-costs.json`. Fail-soft 2s. No new pip.

**Disclaimer (always):** Calculator is local. Check actual billed cost on the Costs dashboard or `/run-costs`.
