---
templateId: region.region-display-selector.common
componentType: region
version: 1.0
description: Shared contract for region display selector patterns.
---

# Variable Contract

| Name | Required | Type | Notes |
|------|----------|------|-------|
| controlRegionStaticId | yes | string | RDS control region id. |
| toggledRegions | yes | array | Regions that set `advanced.regionDisplaySelector: true`. |
| settings.displayRegionIcons | optional | boolean | Displays target region icons. |
| settings.rememberSelection | optional | enum | `bySession`, `byUser`, or `false`. |

# Guardrails

- Each toggled region must explicitly set `advanced.regionDisplaySelector: true`.
- Keep toggled regions in stable layout order for deterministic tab behavior.
