---
name: oracle-apexlang-specialist
description: APEXLang deterministic component generation for Oracle APEX. Trigger on: APEXLang, .apx files, APEX component generation, apexctl, APEX scaffold, APEXLang compiler, APEX page materialization.
---

# APEXLang Specialist

## Fetch Protocol

All reference guides live at `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/`.
Use WebFetch to pull specific files when topics match the routing table.
On network failure: answer from built-in APEXLang knowledge and note the limitation.

## Start Order (fetch in this sequence)

1. `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/SKILL.md` — north-star router, contracts, stop conditions
2. `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/domains/README.md` — domain reference index

For live generation with compiler-truth validation, the full package is required (JSON catalogs + `apexctl.mjs`).
See **Full Package** note below.

## Category Routing

| Topic | Fetch URL |
|-------|-----------|
| APEXLang router, contracts, stop conditions | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/SKILL.md` |
| Domain reference index (pages, regions, items, buttons, charts) | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/domains/README.md` |
| APEX generation workflows | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/workflows/apex-generation.md` |
| Prompt contracts, rule IDs, instruction hierarchy | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/workflows/apexlang/prompt-contracts.md` |
| Business logic — computations | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/domains/business-logic/computations/workflow-computations-batch.md` |
| Business logic — dynamic actions | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/domains/business-logic/dynamic-actions/workflow-dynamic-actions-batch.md` |
| Shared components — translations / localization | `https://raw.githubusercontent.com/giggsoinc/skills/main/apex/apexlang/references/domains/README.md` |

## Full Package Required for Live Generation

APEXLang deterministic generation needs the full packaged skill (JSON router catalogs, `apexctl.mjs` tools, Python validators).
Clone locally and run from the package root:
```bash
gh repo clone giggsoinc/skills
cd skills/apex/apexlang
node tools/apexctl.mjs workspace probe
```

The JSON assets (`assets/router-catalog.json`, `assets/load-policies.json`, etc.) are read by the compiler — they cannot be fetched at runtime and must be present locally.

Full source: https://github.com/giggsoinc/skills/tree/main/apex/apexlang
