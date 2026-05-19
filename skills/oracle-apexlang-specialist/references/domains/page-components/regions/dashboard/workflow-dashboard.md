# Workflow: Dashboard (KPIs/Cards)

Purpose
- Create dashboards with KPI regions/cards and consistent layout.

Required inputs
- KPI definitions, source queries, layout hints.

Clarify — progressive prompts
- Will any dashboard regions, buttons, or items use a server-side condition? (Answer "none" to skip.)
- If yes, state the component scope (region, button, item, dynamic action, or process) and identifier.
- Provide the desired condition type or business rule, referencing memory-bank/20-data/apex.logic.md for valid options.
- Collect the required attributes for that type (item, value/list, request value, plsqlExpression, sqlQuery, etc.). Missing answers block the workflow.

Load
- memory-bank/00-guard/ai.guard.md
- memory-bank/10-global/apex.global.md
- memory-bank/30-pages/apex.layout.md
- memory-bank/30-pages/apex.dashboard.md
- memory-bank/20-data/apex.sql.md

Layout defaults
- Build a row plan before emitting regions.
- Equal-width sibling rows must use sequence ordering plus `startNewRow: false` on second-and-later siblings.
- Do not emit `column` / `columnSpan` for KPI strips or standard two-up / three-up dashboard rows.
- Use explicit coordinates only when the requested dashboard is intentionally asymmetric.

Composition reference
- references/policies/memory-bank/40-components/apex.templates.md

References
- references/policies/governance/00-governance.md
- memory-bank/rules-mapping.json

Completion
- After Revision, prompt for ``db_connection_name`, `app_path`, and `application_id` if missing, run `references/ops/runtime-gates/02-direct-sqlcl-validate-gate.md`, then invoke `references/ops/runtime-gates/01-direct-sqlcl-import.md`.
- Fail the workflow if a requested server-side condition is not mapped to a catalog type or lacks the required attributes.
