# Report Column Rendering Standards

## Purpose
- Define one canonical contract for presentation markup in report columns across Classic Report, Interactive Report, and Interactive Grid.
- Keep SQL/PLSQL data-focused and move UI markup to report-column formatting attributes supported by the active compiler contract.

## Scope
- Applies to:
  - Classic Report columns
  - Interactive Report columns
  - Interactive Grid columns
- Applies when report source is SQL/PLSQL and when column output needs visual emphasis (status badges, highlighted amounts, icons, chips, etc.).

## Rules (Non-Negotiable)
1. SQL/PLSQL source must remain data-only.
   - Do not emit HTML literals/tags in SQL/PLSQL used for report rendering.
2. For compiler contract `mmdVersion 26.1.053`, emit column markup only inside `columnFormatting.htmlExpression`.
   - Do not emit top-level `column ... htmlExpression: ...`.
3. When using `columnFormatting.htmlExpression`, keep the column as plain text rendering.
   - Do not emit `type: richText` for this pattern.
   - Do not emit `type: plainText` unless explicitly required; plain text is the implicit default.
4. Keep rendering logic declarative and column-scoped; do not push UI rendering into SQL projections.

## Canonical Rendering Shape
```apexlang
column SOME_COL (
  ...
  columnFormatting {
    htmlExpression: <span class="t-Badge">#SOME_COL#</span>
  }
)
```

## Fallback Behavior
- If the requested report type or runtime contract does not support column-level markup rendering:
  - keep SQL data-only,
  - render plain text/non-HTML output,
  - log a critique finding describing unsupported rendering capability,
  - do not emit unsupported attributes.

## Prohibited Patterns
- Top-level `htmlExpression` directly under report `column (...)`.
- `type: richText` on columns that use `columnFormatting.htmlExpression`.
- HTML literals in report SQL/PLSQL source.
- Region-specific ad-hoc rendering attributes not present in the active component contract.

## References
- `references/policies/memory-bank/00-guard/ai.guard.md`
- `references/policies/memory-bank/20-data/apex.sql.md`
- `assets/component-attributes.json`
