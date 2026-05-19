---
templateId: region.cards.standard
componentType: region
version: 1.0
imports:
  - cards._common
description: Standard SQL-backed cards region.
---

# Output Template

```
region {{regionStaticId}} (
  name: {{name}}
  type: cards
  source {
    location: localDatabase
    type: sqlQuery
    sqlQuery:
      ```sql
      {{source.sqlQuery}}
      ```
  }
  layout {
    sequence: {{layout.sequence}}
    slot: {{layout.slot}}
  }
  appearance {
    template: @/cards-container
    templateOptions: #DEFAULT#
  }
  card {
    primaryKeyColumn1: {{card.primaryKeyColumn1}}
  }
  title {
    column: {{title.column}}
    htmlExpression: {{title.htmlExpression}}
    advancedFormatting: {{title.advancedFormatting}}
  }
  subtitle {
    column: {{subtitle.column}}
    htmlExpression: {{subtitle.htmlExpression}}
    advancedFormatting: {{subtitle.advancedFormatting}}
  }
  body {
    column: {{body.column}}
    htmlExpression: {{body.htmlExpression}}
    advancedFormatting: {{body.advancedFormatting}}
  }
  secondaryBody {
    column: {{secondaryBody.column}}
    htmlExpression: {{secondaryBody.htmlExpression}}
    advancedFormatting: {{secondaryBody.advancedFormatting}}
  }
  media {
    source: {{media.source}}
    {{media.sourceValueProperty}}: {{media.sourceValue}}
  }
  blobAttributes {
    mimeTypeColumn: {{blobAttributes.mimeTypeColumn}}
    lastUpdatedColumn: {{blobAttributes.lastUpdatedColumn}}
  }
  iconAndBadge {
    iconSource: {{iconAndBadge.iconSource}}
    iconColumn: {{iconAndBadge.iconColumn}}
    iconCssClasses: {{iconAndBadge.iconCssClasses}}
    iconDescription: {{iconAndBadge.iconDescription}}
    badgeColumn: {{iconAndBadge.badgeColumn}}
    badgeLabel: {{iconAndBadge.badgeLabel}}
    badgeCssClasses: {{iconAndBadge.badgeCssClasses}}
  }
  messages {
    whenNoDataFound: {{messages.whenNoDataFound}}
    noDataFoundIcon: {{messages.noDataFoundIcon}}
  }
  componentAppearance {
    gridColumns: {{componentAppearance.gridColumns}}
  }
)
```

In the template above, `{{media.sourceValueProperty}}` / `{{media.sourceValue}}` is schematic. Emit exactly one concrete source-value property according to this mapping:

| media.source | Required value property |
|--------------|-------------------------|
| `blobColumn` | `blobColumn` |
| `urlColumn` | `urlColumn` |
| `imageUrl` | `url` |

# Media Source Shapes

Use exactly one of these source-specific shapes when a Cards region needs media:

```apexlang
media {
    source: blobColumn
    blobColumn: <BLOB_COLUMN_ALIAS>
}
blobAttributes {
    mimeTypeColumn: <MIME_TYPE_COLUMN_ALIAS>
    lastUpdatedColumn: <LAST_UPDATED_COLUMN_ALIAS>
}
```

```apexlang
media {
    source: urlColumn
    urlColumn: <URL_COLUMN_ALIAS>
}
```

```apexlang
media {
    source: imageUrl
    url: <STATIC_IMAGE_URL_OR_COLUMN_SUBSTITUTION>
}
```

## Non-Default Media Presentation

Default media presentation is represented by omission: do not emit any APEXLang-side `position`, `appearance`, or `sizing` property for default Cards media. Emit these properties only when the user or spec explicitly asks for a non-default media presentation. Never emit `position: first`, `appearance: square`, or `sizing: cover` just to mirror APEX defaults.

When a non-default presentation is required, add only the needed supported properties inside the same `media` block:

```apexlang
position: first
appearance: square
sizing: cover
```

# Conditional Rendering Rules

- If `title.column` is emitted, omit `title.htmlExpression` and omit `title.advancedFormatting`.
- If `title.htmlExpression` is emitted, `title.advancedFormatting` must also be emitted with value `true`, and `title.column` must be omitted.
- If `subtitle.column` is emitted, omit `subtitle.htmlExpression` and omit `subtitle.advancedFormatting`.
- If `subtitle.htmlExpression` is emitted, `subtitle.advancedFormatting` must also be emitted with value `true`, and `subtitle.column` must be omitted.
- If `body.column` is emitted, omit `body.htmlExpression` and omit `body.advancedFormatting`.
- If `body.htmlExpression` is emitted, `body.advancedFormatting` must also be emitted with value `true`, and `body.column` must be omitted.
- If `secondaryBody.column` is emitted, omit `secondaryBody.htmlExpression` and omit `secondaryBody.advancedFormatting`.
- If `secondaryBody.htmlExpression` is emitted, `secondaryBody.advancedFormatting` must also be emitted with value `true`, and `secondaryBody.column` must be omitted.
- If the Cards region displays a BLOB image, project the raw BLOB column in SQL for display only, define `card.primaryKeyColumn1`, and emit `media { source: blobColumn blobColumn: <BLOB_COLUMN_ALIAS> }`.
- Do not use the raw BLOB alias as a comparison key; sorting, grouping, distincting, joining, analytic keys, and filter comparisons must follow `SQL_PLSQL_LOB_COMPARISON_KEY_FORBIDDEN_001` in `20-data/apex.sql.md`.
- Keep companion image metadata columns projected in SQL when available. If MIME type or last-updated aliases are available, emit them in `blobAttributes { mimeTypeColumn: <MIME_TYPE_ALIAS> lastUpdatedColumn: <LAST_UPDATED_ALIAS> }`.
- Emit `blobAttributes` if and only if `media.source: blobColumn` is present; do not emit it for other media sources or for Cards regions without BLOB media.
- If the Cards region displays images from a URL column, project that URL alias in SQL and emit `media { source: urlColumn urlColumn: <URL_COLUMN_ALIAS> }`.
- If the Cards region displays a static image URL or column substitution URL, emit `media { source: imageUrl url: <STATIC_IMAGE_URL_OR_COLUMN_SUBSTITUTION> }`; substitution values use APEX syntax such as `&IMAGE_URL_COLUMN.`.
- In any Cards `media` block, emit at most one source-specific value property: `blobColumn` with `source: blobColumn`, `urlColumn` with `source: urlColumn`, or `url` with `source: imageUrl`.
- Default media presentation emits no APEXLang-side `position`, `appearance`, or `sizing` property.
- Emit `position`, `appearance`, and `sizing` only for explicit non-default media presentation requirements. Accepted values are `position: first | background`, `appearance: square | widescreen`, and `sizing: cover`.
- Never emit `position: first`, `appearance: square`, or `sizing: cover` just to mirror APEX defaults.
- Do not emit additional `media` or `blobAttributes` properties unless compiler-backed truth proves them.
- Do not add report-style child `column (...)` blocks for Cards BLOB display.
- Inside cards `title.htmlExpression`, `subtitle.htmlExpression`, `body.htmlExpression`, and `secondaryBody.htmlExpression`, use `&COLUMN.` substitution strings, not `#COLUMN#`.
- Omit the `componentAppearance` block by default.
- Emit `componentAppearance.gridColumns` only when the prompt explicitly specifies a fixed card column count.
- If emitted, `componentAppearance.gridColumns` must be one of `2`, `3`, `4`, or `5`.
