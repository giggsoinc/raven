---
templateId: region.interactive-grid.columns.common
componentType: region
version: 1.0
description: Shared column contract for interactive grid regions.
---

# Purpose

Standardize `column` variable contracts, output shape, and guardrails for interactive-grid variants.

---

# Generation Rules (MANDATORY)

1. Load `interactive-grid._common.md` before using this columns contract.
2. Ensure one column maps to the region key column and can be marked as primary key in source metadata.
3. Omit optional nested blocks when their variables are not provided.

---

# Variable Contract

| Name | Required | Type | Notes |
|------|----------|------|-------|
| column.name | yes | string | Column static identifier. |
| column.type | yes | enum | Grid item type (`textField`, `numberField`, `datePicker`, `textarea`, etc.). |
| column.heading | optional | string | Column heading text. |
| column.headingAlignment | optional | enum | `start`, `center`, `end`. |
| column.sequence | yes | number | Display sequence. |
| column.columnAlignment | optional | enum | `start`, `center`, `end`. |
| column.appearance.formatMask | optional | string | Any date format mask; only use when column.type = `datePicker` |
| column.databaseColumn | optional | string | Backing DB column name. |
| column.dataType | optional | string | Source data type. |
| column.primaryKey | optional | boolean | Primary key indicator for the key column. |
| column.maxLength | optional | number | Validation max length. |
| column.sessionStateDataType | optional | string | Session state type for large text columns. `session`, `user`|
| column.columnFormatting.htmlExpression | optional | string | Column markup rendering expression. |
| column.columnFilter.lovType | optional | enum | Filter LOV behavior. |
| column.columnFilter.performanceImpactingOperators | optional | array | Performance-impacting operators list. |
| column.comments | required by default | string | Descriptive metadata string for `comments { comments: ... }` on business-significant, derived, status, and action columns; include the required attributes `Display Label`, `Display in Report`, `Display in Form`, `Format Mask`, `Value Required`, `Read Only`, `Primary Display Column`, and `Authorization Scheme`, with optional leading `Summary`. |
| column.security.authorizationScheme | optional | string | Existing authorization alias. |

---

# Output Template – Full

```apexlang
column {{column.name}} (
  type: {{column.type}}
  heading {
    heading: {{column.heading}}
    alignment: {{column.headingAlignment}}
  }
  layout {
    sequence: {{column.sequence}}
    columnAlignment: {{column.columnAlignment}}
  }
  appearance {
    formatMask: DD-MON-YYYY
  }
  source {
    databaseColumn: {{column.databaseColumn}}
    dataType: {{column.dataType}}
    primaryKey: {{column.primaryKey}}
  }
  validation {
    maxLength: {{column.maxLength}}
  }
  sessionState {
    dataType: {{column.sessionStateDataType}}
  }
  columnFormatting {
    htmlExpression: {{column.columnFormatting.htmlExpression}}
  }
  columnFilter {
    lovType: {{column.columnFilter.lovType}}
    performanceImpactingOperators: {{column.columnFilter.performanceImpactingOperators}}
  }
  comments {
    comments: {{column.comments}}
  }
  security {
    authorizationScheme: @{{column.security.authorizationScheme}}
  }
)
```

---

# Conditional Rendering Rules

- Omit `heading` when no heading values are provided.
- Omit `heading.alignment` and `layout.columnAlignment` when not provided.
- Omit `appearance` if column.type != `datePicker`
- Omit `source` unless at least one source attribute is provided.
- Omit `validation` unless `column.maxLength` is provided.
- Omit `sessionState` unless `column.sessionStateDataType` is provided.
- Omit `columnFormatting` unless `column.columnFormatting.htmlExpression` is provided.
- Omit `columnFilter` unless one or more filter attributes are provided.
- Omit `comments` only for hidden technical columns or when a documented exemption applies.
- Omit `security` when column-level authorization is not required.

---

# Guardrails

- Keep column ordering deterministic and aligned with end-user workflows.
- Use `column.primaryKey: true` on the column that matches the grid key column.
- Keep performance-impacting operators minimal and intentional.
- When `comments` is emitted, keep it as a single string literal inside `comments { comments: ... }`.
- Emit `comments { comments: ... }` by default for business-significant, derived, status, and action columns instead of treating the block as opt-in metadata.
- The required attributes are `Display Label`, `Display in Report`, `Display in Form`, `Format Mask`, `Value Required`, `Read Only`, `Primary Display Column`, and `Authorization Scheme`.
- Include `Summary` only when a short leading business-intent sentence materially helps maintenance.
- When `Summary` is present, keep the stable order `Summary`, `Display Label`, `Display in Report`, `Display in Form`, `Format Mask`, `Value Required`, `Read Only`, `Primary Display Column`, `Authorization Scheme`.
- Mirror executable settings such as `appearance.formatMask` and `security.authorizationScheme` when those blocks are emitted.
- Use only existing authorization scheme aliases when `security.authorizationScheme` is provided.
- When using `columnFormatting.htmlExpression`, do not emit `type: richText`; keep plain text implicit.
- Keep SQL data-only; emit report markup via `columnFormatting.htmlExpression` per `references/policies/memory-bank/30-pages/apex.report-column-rendering.md`.
