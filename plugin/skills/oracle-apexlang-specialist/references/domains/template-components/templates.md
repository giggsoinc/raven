# Template & Rule References — Template Components

## Authoritative Policies
- `references/policies/governance/00-governance.md`
- `references/policies/memory-bank/00-guard/ai.guard.md`
- `references/policies/memory-bank/10-global/apex.global.md`
- `references/policies/memory-bank/40-components/apex.templates.md`
- `references/policies/memory-bank/40-components/apex.items.md`
- `references/policies/memory-bank/20-data/apex.sql.md`
- `references/policies/memory-bank/20-data/apex.logic.md`
- `assets/rules-mapping.json`

## Operational References
## Templates
- `templates/template-components/content-row/content-row._common.md`
- `templates/template-components/content-row/content-row._index.md`
- `templates/template-components/content-row/content-row.report-minimal.md`
- `templates/template-components/content-row/content-row._index.md`
- `templates/template-components/button/button._common.md`
- `templates/template-components/button/button._index.md`
- `templates/template-components/metric-card/metric-card._common.md`
- `templates/template-components/metric-card/metric-card._index.md`
- `templates/items/select-list/select-list._index.md`
- `templates/items/text-field/text-field._index.md`
- `templates/buttons/buttons._index.md`

For content-row page or region creation, load `content-row._common.md` first, then `content-row._index.md`, and default to `content-row.report-minimal.md` unless the prompt explicitly requests richer features. When badge iconography or placement is requested, use `plugin-badge.icon` and `plugin-badge.position` from the Content Row contract.

Consult `rules-mapping.json` to load only the listed rules per request.
