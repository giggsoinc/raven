---
templateId: region.faceted-search.standard
componentType: region
version: 1.0
imports:
  - faceted-search._common
description: Standard left-column faceted-search region paired with report results.
---

# Output Template

```
region {{searchRegionStaticId}} (
  name: {{name}}
  type: facetedSearch
  source {
    filteredRegion: @{{resultsRegionStaticId}}
  }
  layout {
    sequence: {{layout.sequence}}
    slot: leftColumn
  }
  appearance {
    template: {{appearance.template}}
    templateOptions: #DEFAULT#
  }
  {{facets}}
)
```

# Standard Notes

- Emit child facets as `facet (...)` blocks after the region shell.
- For the common “Product / Order Date / Order Status / Store” shape:
  - Product: `type: search` with `source.dbColumns`
  - Order Date: `type: range`
  - Order Status: `type: selectList`, `checkboxGroup`, or `radioGroup` with `lov { type: distinctValues }`
  - Store: `type: selectList`, `checkboxGroup`, or `radioGroup` with `lov { type: distinctValues }`
- Do not emit `settings.currentFacetsSelector`; the live importer rejects that property in this runtime.
