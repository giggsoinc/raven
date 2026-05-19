# Page Layout Standards

## Purpose
Defines the default region layout contract for page generation so APEXlang pages use the native 12-column flow efficiently instead of over-specifying grid coordinates.

This file applies to generated application page artifacts, templates, and non-modal page layouts unless a page-type rule defines a narrower contract.

## Layout Scopes
Each layout container owns its own 12-column grid. Evaluate `column` and `columnSpan` only within the current scope.

Supported scopes:
- page slot rows, for example top-level BODY regions
- nested region rows grouped by `layout.parentRegion + layout.slot`
- item rows grouped by `layout.region + layout.slot`
- button rows grouped by `layout.region + layout.slot`

Parent and child spans never add together across scopes. A parent region may consume part of the page grid, while items, buttons, or nested regions inside that parent still get their own local 12-column budget.

## Default Rule
- Prefer implicit flow for equal-width sibling components within the current scope.
- Use `layout.sequence` to control order.
- Use `layout.startNewRow: false` on the second and later components in the same row.
- Omit `layout.column` and `layout.columnSpan` for equal-width rows.

## Equal-Width Row Recipes
- `stack`
  - One region per row.
  - Omit `startNewRow`, `column`, and `columnSpan`.
- `two-up-equal`
  - First region in row: omit `startNewRow`.
  - Second region in row: `startNewRow: false`.
  - Omit `column` and `columnSpan` on both.
- `three-up-equal`
  - First region in row: omit `startNewRow`.
  - Second and third regions: `startNewRow: false`.
  - Omit `column` and `columnSpan` on all three.
- `kpi-strip`
  - Use the same equal-width flow rules as `three-up-equal`, extended to the number of KPI siblings in the row.
  - Prefer 2-6 KPIs in one row when labels are short and content is single-value.

## When Explicit Grid Coordinates Are Allowed
Use `layout.column` and `layout.columnSpan` only for intentionally asymmetric layouts within the current scope, such as:
- sidebar + main content
- faceted search
- parent-child split
- wizard or modal shell-specific positioning
- prompt-explicit uneven widths

Allowed asymmetric examples:
- `sidebar-main`: 3/9 or 4/8
- `parent-child-split`: 4/8
- `master-detail-content-row`: parent Content Row at `columnSpan: 3` or `4`, followed by the child region in the same body row with `startNewRow: false`
- `three-zone`: 3/6/3

## Generation Contract
- Generated `applications/**` artifacts are subject to deterministic layout linting; do not treat final app files as exempt from these rules.
- For standard non-login pages, top-level regions should use `layout.slot: body`.
- Reserve `layout.slot: contentBody` for login and modal-dialog page-template contracts that explicitly define that semantic slot.
- Decide the row recipe per layout scope before emitting components.
- For equal-width rows, do not emit fallback coordinates "just to be safe".
- Do not mix implicit-flow and explicit-grid placement within the same scope row unless the pattern is intentionally asymmetric.
- If a row is equal-width, the first component must omit `startNewRow`; later siblings in that row must set `startNewRow: false`.
- The total explicit `columnSpan` in any single row must never exceed 12 within that scope.

## Analytical Page Defaults
- KPI strips: equal-width flow by sequence.
- Two charts on the same row: `two-up-equal`.
- Three charts on the same row: `three-up-equal`.
- Detail/report sections below KPIs/charts: `stack` unless the prompt explicitly requests a split.

## Master-Detail Content Row Defaults
- When a parent Content Row selects context for a child report, use a left/right parent-child split instead of stacked full-width regions.
- Emit the parent Content Row first with `layout.columnSpan: 3` or `4`; omit `layout.column` unless another region in the same scope requires an explicit start column.
- Emit the child report second with `layout.startNewRow: false`; do not add redundant `column` / `columnSpan` unless a runtime or template-specific contract requires explicit coordinates.
- Place parent-context page items as hidden technical items, not as visible body controls, unless the prompt explicitly requests a manual selector.
- Place create/edit/detail buttons for the child context inside the child report toolbar slot instead of laying them out in body-grid columns.

## Anti-Patterns
- Do not emit `column: 1`, `columnSpan: 6`, `column: 7`, `columnSpan: 6` for a simple two-up row.
- Do not assign explicit `column` / `columnSpan` to every sibling on a dashboard when APEX native flow can place them correctly.
- Do not omit `startNewRow: false` from second-or-later equal-width siblings.
- Do not add child spans to parent spans when validating a row budget; each scope resets to 12 columns.
- Do not model master-detail parent selection as a visible select list plus a separate full-width child report when a Content Row parent list is the primary browse affordance.
