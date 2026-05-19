## Smart Filter & Search Page Standards

Rules and conventions for Oracle APEX pages that center on the Smart Filters component paired with a tabular or card-based results region.

Keywords: smart filter, smart filters, smart search, quick search, multi-attribute search

---

## Purpose and Scope
- Deliver a deterministic recipe for implementing Smart Filter & Search experiences that combine a Smart Filters region with a single authoritative results region.
- Ensure consistency with Universal Theme defaults, guardrails defined in `00-guard`, and the component template at `templates/region-components/smart-filter-search/smart-filter-search._common.md`.
- Apply to non-modal pages whose primary interaction is searching/list filtering rather than data entry.

---

## Page Template & Navigation (Non-Negotiable)
1. Use the Standard page template (`pageTemplate: @/standard`) unless a documented exception requires another layout. Keep `templateOptions: #DEFAULT#`.
   Keep each value exact. `#DEFAULT#` remains standalone, and documented composites such as `t-Region--hideHeader js-addHiddenHeadingRoleDesc` remain one atomic entry.
2. Include a Breadcrumb region using the title-bar template. Position it in `slot: REGION_POSITION_01` with `sequence: 10`.
3. Follow `apex.page.md` for page naming, alias, title, breadcrumb entry, and navigation list updates.
4. Disable form autocomplete on search-driven pages unless business requirements state otherwise.

---

## Core Composition (Top → Bottom)
1. **Breadcrumb / Header** – Optional wrapper region for breadcrumbs and page-level actions.
2. **Smart Filters Region** – Region type `smartFilters`, parented to the breadcrumb/header region when using the PLUGIN_SEARCH slot, otherwise place in BODY with `sequence: 10`.
3. **Results Region** – Classic Report (preferred) or approved alternative (Cards, Interactive Report/Grid) representing the canonical search results.
4. **Optional Export / Download** – When exports are enabled, expose them via the results region (e.g., PDF download button) rather than standalone buttons.

Maintain the page grid so that Smart Filters sits visually above or beside the results region while respecting UT responsive behavior.

---

## Smart Filters Configuration (Non-Negotiable)
1. `filteredRegion` must point to the static ID of the results region.
   The filtered target must be the page's actual results region, not a map region, not a map layer, and not another filter region.
2. Preserve `templateOptions: #DEFAULT#` unless a documented template-option exception exists. Do not invent classes.
3. Set `settings.compactNosThreshold` high enough (≥ 10000) to avoid the compact fallback for moderate result counts.
4. Order filters: primary search first, then categorical filters (checkbox/radio), then range or other specialty filters.
5. Use `suggestions.type: dynamic` for facet filters unless a static list is mandated.
6. Provide semantic labels and placeholders; if the Smart Filters region is the primary search control, set `accessibility.landmarkType: search`.

### Filter Types
- **Search Filter** – Consolidate free-text search across key columns via the canonical `source.dbColumns` list. Do not collapse the search filter into a single-column shortcut shape or other undocumented source variant.
- **Categorical Filters** – Prefer checkbox group or radio group facets with `lov.type: distinctValues` for table-backed columns. Provide `listEntries.zeroCountEntries: disable` to hide empty facets.
- **LOV Source** – For demo/sample data, distinct values are acceptable; for production, use curated LOVs or SQL views to control display order.

---

## Results Region Requirements
1. **Classic Report Defaults**
   - `appearance.template: @/standard`
   - `appearance.templateOptions: [ #DEFAULT#, t-Region--noPadding, t-Region--hideHeader js-addHiddenHeadingRoleDesc, t-Region--scrollBody ]` when scrollable body is desired.
   - `componentAppearance.template: @/standard` with stretch/static row color options as needed.
2. Include `messages.whenNoDataFound` with user-friendly copy (e.g., `no data found`).
3. Default pagination for a Classic Report results region is `rowRangesXToYNoPagination`. Switch to another catalog option (see `20-data/apex.sql.md`) only when the user asks for paging controls or when dataset volume requires them.
4. Apply end alignment to numeric columns and hide surrogate keys with `type: hidden`.
5. When exports are required, enable them via the region’s Download attributes instead of custom buttons; respect security guardrails for file generation.

### Alternative Result Types
- Cards: follow card policies from `apex.dashboard.md` and the Cards policy section.
- Interactive Report/Grid: ensure all controlling filters are listed in `pageItemsToSubmit` and the IR/IG configuration follows its respective memory-bank rule.
- Content Row / Metric Card: allowed only when the page still has one authoritative row-based results region with compatible filterable source columns.

### Map + Filter Pages
- Smart Filters must drive a compatible results region such as Classic Report, Interactive Report, Interactive Grid, Cards, Content Row, or Metric Card.
- Treat a map as a companion visualization, not as the Smart Filters `filteredRegion` target.
- If the page needs both map interaction and structured filtering, keep the map synchronized from the authoritative results region or a shared data source instead of targeting the map directly from Smart Filters.

---

## Optional Header Actions
- Primary/secondary buttons should live in the header region slots (`PLUGIN_PRIMARY_ACTIONS`, `PLUGIN_SECONDARY_ACTIONS`).
- Use shared button templates (`@/button`) with `templateOptions: #DEFAULT#`. Keep action layout within template and slot defaults; do not add ad hoc classes.
- Actions must be wired via dynamic actions or navigation that respects checksum policies.

---

## Data, Performance & Sample Data
- Keep Smart Filter results backed by performant SQL (views or packaged APIs per `20-data/apex.sql.md`).
- Avoid per-filter dynamic SQL in session state; leverage `filteredRegion` so APEX handles predicate composition.
- Demo/skeleton pages may use `sampleData` sources (e.g., `employees`); production pages must point to actual schema objects.

---

## Accessibility & UX
- Ensure every filter has a concise label; avoid abbreviations unless registered in `apex.acronyms.md`.
- Provide accessible text for export links and total count indicators; when surfacing total row counts, either rely on defaults or set `settings.showTotalRowCount: true` with a localized label.
- Maintain consistent sequencing so keyboard navigation progresses from filters into results.

---

## Testing & Validation Checklist
- Smart Filters refreshes results region without page reload.
- Filters display only relevant values (no orphan facets with zero results).
- Download/export actions honor current filters.
- Breadcrumb and navigation entries route to the correct page with checksum protection.

---

## References & Assets
- Template: `templates/region-components/smart-filter-search/smart-filter-search._common.md`
- Example page: `applications/apexlang-skeleton-test-application101/pages/p00010-smart-filter-search.apx`
- Oracle APEX Smart Filters documentation
- Pair with related rules: `apex.dashboard.md` (filters section) and `apex.faceted-search.md` for alternate filtering patterns.
