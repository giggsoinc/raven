---
templateId: region.region-display-selector.standard
componentType: region
version: 1.0
imports:
  - region-display-selector._common
description: Standard RDS control region with multiple toggled content regions.
---

# Pattern

- Create RDS control region (`type: regionDisplaySelector`) in target slot.
- Mark each controlled region with `advanced { regionDisplaySelector: true }`.
- Optionally enable `displayRegionIcons` and `rememberSelection`.
