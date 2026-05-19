---
templateId: region.classic-report.common
componentType: region
version: 1.1
description: Shared contract for classic report regions.
---

# Purpose

Standardize the variable contract, guardrails, and template skeleton for classic report scenarios.

---

# Generation Rules (MANDATORY)

1. Load `memory-bank/30-pages/apex.classic-report.md` before drafting classic reports.
2. Validate SQL against the target schema or mark Validation Pending.
3. Synchronize column definitions with the SQL projection; remove unused permutations.
4. Scenario templates in this family must render output templates with variables (`{{...}}`) only; do not embed static sample values in output DSL.
5. Use `classic-report._columns._common.md` as the canonical column contract.
6. Emit explicit `column (...)` definitions for every SQL/table projection before finals.
7. If the report adds navigation, ask which mode is required every time: same application page, another application page, or URL redirect.
8. When the chosen mode is same application page and the column contract supports it, emit a declarative page target instead of a URL string or SQL-generated `apex_page.get_url(...)`.
9. Unless the selected scenario is the dedicated `@/contextual-info` Classic Report variant, emit the canonical Classic Report default template block from `references/policies/memory-bank/40-components/apex.templates.md` exactly as owned there.

---

# Variable Contract

| Name | Required | Type | Notes |
|------|----------|------|-------|
| regionStaticId | yes | string | Identifier used after the `region` keyword. |
| name | yes | string | Builder display name. |
| type | yes | enum | Always `classicReport`. |
| source.location | yes | enum | `localDatabase`, `sampleData`, etc. |
| source.type | yes | enum | `sqlQuery`, `table`, etc. |
| source.sqlQuery | conditional | sql | Required when sourcing via SQL. |
| layout.sequence | yes | number | Region order in the page slot. |
| layout.slot | yes | enum | Slot the region occupies (e.g., `BODY`). |
| appearance.template | yes | string | Region template reference. |
| appearance.templateOptions | optional | array/string | For non-`@/contextual-info` Classic Reports, default to the canonical shared value `#DEFAULT#`. Keep `#DEFAULT#` standalone, emit only exact accepted values, and when more than one value is present serialize it as a bracketed multi-line array with one accepted value per line. |
| componentAppearance.template | yes | string | Report template (e.g., `@Standard`). |
| componentAppearance.templateOptions | optional | array | For non-`@/contextual-info` Classic Reports, default to the exact shared list `#DEFAULT#`, `t-Report--stretch`, `t-Report--altRowsDefault`, `t-Report--rowHighlight`. Keep report modifiers as separate exact values, never concatenate them with `#DEFAULT#`, and serialize multi-value arrays as bracketed multi-line arrays with one accepted value per line. |
| pagination.type | optional | enum | Classic-report pagination strategy. Default `rowRangesXToYNoPagination`; allowed values are limited to the classic-report pagination catalog in this file. |
| messages.whenNoDataFound | optional | string | Custom "no data" message. |
| columns | conditional | list | One or more column blocks following `classic-report._columns._common.md`. |
| serverSideCondition.* | optional | condition | Server-side gating of region visibility. |
| security.authorizationScheme | optional | string | Authorization scheme alias. |

---

# Output Template – Full

```
region {{regionStaticId}} (
  name: {{name}}
  type: classicReport
  source {
    location: {{source.location}}
    type: {{source.type}}
    sqlQuery:
        ```sql
        {{source.sqlQuery}}
        ```
  }
  layout {
    sequence: {{layout.sequence}}
    slot: {{layout.slot}}
  }
  appearance {
    template: {{appearance.template}}
    templateOptions: [
      {{appearance.templateOptions}}
    ]
  }
  componentAppearance {
    template: {{componentAppearance.template}}
    templateOptions: [
      {{componentAppearance.templateOptions}}
    ]
  }
  pagination {
    type: {{pagination.type}}
  }
  messages {
    whenNoDataFound: {{messages.whenNoDataFound}}
  }
  serverSideCondition {
    type: {{serverSideCondition.type}}
    item: {{serverSideCondition.item}}
    {{serverSideCondition.comparisonAttribute}}: {{serverSideCondition.comparisonValue}}
  }
  {{columns}}
)
```

---

# Conditional Rendering Rules

- For non-`@/contextual-info` Classic Reports, do not omit or alter the canonical `appearance` and `componentAppearance` defaults unless the selected scenario template explicitly documents an override.
- Remove optional blocks (`pagination`, `messages`, `serverSideCondition`) when not required.
- Expand `{{columns}}` using `classic-report._columns._common.md`.
- Do not finalize a Classic Report with projected SQL/table columns missing from the `column (...)` list.
- Use server-side conditions for feature flags, request-based visibility, or authorization polices.
- For item colon-list membership conditions, render `comparisonAttribute` as `list`; keep `value` for other comparison types.
- When `appearance.templateOptions` or `componentAppearance.templateOptions` contains more than one accepted value, emit bracketed multi-line array syntax with one accepted value per line; never emit inline comma-separated arrays.

### Classic Report Pagination Catalog

- Default classic-report pagination is `rowRangesXToYNoPagination`.
- Allowed `pagination.type` values for classic reports are:
  - `rowRangesXToYNoPagination`
  - `rowRangesXToYOfZNoPagination`
  - `rowRangesXToYOfZWithPagination`
  - `setPaginationLinks`
  - `setPaginationSelectList`
  - `setPaginationSearchEngine`
  - `externalPaginationButtons`
  - `nextAndPreviousLinks`
- Omit `pagination.type` to represent no explicit value (`null`).
- Do not use interactive-report-only values such as `rowRangesXToY` or `rowRangesXToYOfZ` on classic reports.

---

# Guardrails

- Prefer SQL sourced from views or packaged APIs for complex reports; keep region SQL lightweight.
- For same-application drill links, keep navigation declarative on the report column whenever the DSL supports it; reserve SQL-generated URL columns for explicit URL mode only.
- Apply format masks and alignment to support accessibility and readability.
- Keep `templateOptions` exact: `#DEFAULT#` is standalone, report modifiers are separate tokens, documented composite values stay atomic when the catalog/runtime lists them that way, and multi-value arrays use bracketed multi-line syntax with one accepted value per line.
- For non-`@/contextual-info` Classic Reports, the shared default is exact, not suggestive: `appearance.templateOptions` must remain `#DEFAULT#`, and `componentAppearance.templateOptions` must remain `#DEFAULT#`, `t-Report--stretch`, `t-Report--altRowsDefault`, `t-Report--rowHighlight` unless the selected scenario contract explicitly overrides it.
- Use column comments to document intent when templates require it (see `memory-bank/30-pages/apex.classic-report.md`).
- Validate SQL with SQLcl when possible; otherwise mark "Validation Pending".
- Keep sample/demo literals in prose notes only; output templates must remain contract-driven and variable-oriented.
- When paging controls are required, choose from the classic-report-only pagination catalog in this file; do not reuse interactive-report pagination enums.
- Use `plug_source_type = NATIVE_SQL_REPORT` as the primary metadata anchor.
- Metadata export lookup: search for `NATIVE_SQL_REPORT`, `classicReport`, and `contextual-info`.
- Source of truth: internal generator logic and template-source metadata for classic reports.
- Use `contextual-info` variant only when the report template itself is `@/contextual-info`; keep classic-report metadata lookup centered on `NATIVE_SQL_REPORT`, not `REGION_TMPL_COLUMN` alone.
