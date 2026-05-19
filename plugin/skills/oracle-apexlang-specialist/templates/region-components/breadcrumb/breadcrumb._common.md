---
templateId: region.breadcrumb.common
componentType: region
version: 1.0
description: Shared contract for breadcrumb regions.
---

# Purpose
Define standard wiring for breadcrumb source and template variants.

# Variable Contract

| Name | Required | Type | Notes |
|------|----------|------|-------|
| regionStaticId | yes | string | Breadcrumb region static id. |
| source.breadcrumb | yes | ref | Shared breadcrumb component alias. |
| componentAppearance.breadcrumbTemplate | yes | ref | Breadcrumb template reference. |
| layout.slot | yes | enum | `BODY` or `PLUGIN_NAVIGATION` when nested. |
| layout.parentRegion | conditional | ref | Required for nested header composition. |

# Guardrails

- Always point `source.breadcrumb` to a valid shared breadcrumb component.
- Keep `templateOptions: #DEFAULT#` unless a documented `static_id` from `breadcrumb._template_options.md` is required.
- When adding a parent entry, use the {{name}} attribute from the parent and replace {{parent.name}}
