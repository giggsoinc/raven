---
templateId: region.smart-filters.common
componentType: region
version: 1.1
description: Shared contract for smart-filters regions and target result region binding.
---

# Purpose

Document the native smart-filters region shell and its filter child metadata boundary.

# Generation Rules (MANDATORY)

1. Use the dedicated `region-smart-filters` template.
2. Treat the filtered-region reference as mandatory.
3. Keep suggestion-chip settings on the region shell and individual filters as child metadata.
4. Use the canonical search-filter source contract with `source.dbColumns` for free-text search; do not invent single-column shortcut shapes.

# Variable Contract

| Name | Required | Type | Notes |
|------|----------|------|-------|
| regionStaticId | yes | string | Region identifier. |
| name | yes | string | Display name. |
| smartFiltersRegionStaticId | yes | string | Smart filters region static id. |
| source.filteredRegion | yes | ref | Results region static id. |
| filters | optional | array | Filter definitions (radio/search/etc). |
| settings.maxSuggestionChips | optional | number | Suggestion-chip limit. |
| settings.showTotalRowCount | optional | boolean | Show row count indicator. |
| settings.moreFiltersSuggestionChip | optional | boolean | Enable additional filter hints. |

# Output Template – Full

```apexlang
region {{regionStaticId}} (
  name: {{name}}
  type: smartFilters
  source {
    filteredRegion: @{{source.filteredRegion}}
  }
  settings {
    maxSuggestionChips: {{settings.maxSuggestionChips}}
  }
  {{filters}}
)
```

# Conditional Rendering Rules

- Keep filter children separate from the shell.
- Use the advanced HTML DOM ID only when the owning scenario requires it.
- Omit `settings` block when no settings values are required.

# Guardrails

- `filteredRegion` must reference an existing results region with compatible source columns.
- `filteredRegion` must not reference a map region, map layer, Smart Filters region, Faceted Search region, or any other non-results alias.
- For map + filter pages, keep Smart Filters bound to the authoritative results region and treat the map as a companion visualization.
- Filter LOV/value definitions must match result columns.
- Metadata export lookup: search for `Smart Filters`, the filtered-region reference, and child filter metadata.
