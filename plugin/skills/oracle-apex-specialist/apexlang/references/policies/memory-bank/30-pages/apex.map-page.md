## Map Page Standards

### Purpose
- Ensure map pages use a consistent layout, Universal Theme template, and map region configuration.

### Rules (Non-Negotiable)
1. Set `pageTemplate: @/standard` with `templateOptions: #DEFAULT#`.
2. Main region must be `type: map` (or the appropriate map plug-in) with `appearance.template: @/standard`.
3. Define map attributes (controls, `initialPositionAndZoom`, layer `source { ... }`, tooltip/info-window, and `columnMapping.geometryColumnDataType`) exactly as shown in `page-examples/map-page/map-page.example.md` and the `region-components/map/*` family.
4. Apply navigation/breadcrumb requirements from `apex.page.md`.
5. For `initialPositionAndZoom.type: sqlQuery`, the SQL select-list aliases must exactly match every configured `initial*Column` name. If `initialZoomlevelColumn` is emitted, the SQL must return that alias too.

### Guidance
- Mirror `templates/page-examples/map-page/map-page.example.md` for page-level structure, `body` slot usage, SQL-driven `initialPositionAndZoom`, and the standard table-backed layer pattern.
- Use `templates/region-components/map/*` for the concrete map-region and map-layer attribute vocabulary, including `geometryColumnDataType: longitudeLatitude`.
- In SQL-driven initial positioning, treat `initialLongitudeColumn`, `initialLatitudeColumn`, and optional `initialZoomlevelColumn` as references to the SQL output alias names, not to the source table column names.
- Map-layer source modes are:
  - `source { tableName: ... }` for the preferred baseline
  - `source { type: sqlQuery sqlQuery: ... }` for new SQL-backed layers
  - `source { type: functionBody plsqlFunctionBody: ... }` for advanced fallback cases
- Legacy bare `source { sqlQuery: ... }` remains accepted for existing artifacts during transition, but new SQL-backed examples should use `source.type: sqlQuery`.
- When combining maps with filters or reports, also follow the relevant guardrails (faceted search, classic report) to keep behaviour deterministic.
