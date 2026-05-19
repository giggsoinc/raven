---
name: oracle-apex-specialist
description: Oracle APEX application development. Trigger on: APEX page builder, APEX REST, APEX authentication, APEX IR/IG, APEX charts, APEX plug-ins, APEXLang component generation, APEX deployment, APEX upgrade.
---

# Oracle APEX Specialist

## Fetch Protocol

All reference guides live at `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/`.
Use WebFetch to pull the specific file when a topic matches the routing table.
On network failure: answer from built-in Oracle APEX knowledge and note the limitation.

## Category Routing

| Topic | Fetch URL |
|-------|-----------|
| Generate APEX apps and components using APEXLang | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/SKILL.md` |
| APEX generation workflows and patterns | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/workflows/apex-generation.md` |
| APEXLang domain reference (pages, regions, items, buttons) | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/domains/README.md` |

## Key Starting Points

- APEXLang generation: fetch `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/SKILL.md` first — it is the north-star router for all APEXLang work
- APEX workflows: fetch `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/workflows/apex-generation.md`

## Note on Full APEXLang Generation

APEXLang generation requires the full packaged skill (JSON catalogs, `apexctl.mjs` runtime tools).
For deterministic component generation, clone the complete skill locally:
```
gh repo clone giggsoinc/skills
```
Then follow the APEXLang SKILL.md `Start Order` from the cloned package root.

Full source: https://github.com/giggsoinc/skills/tree/main/apex
