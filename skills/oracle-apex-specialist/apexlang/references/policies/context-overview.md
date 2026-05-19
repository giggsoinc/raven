# references/policies

## Purpose

`references/policies/` is the repository's shared knowledge and policy area. It contains the rules, templates, reference material, and machine-readable manifests that workflow skills use to decide what to load and how to behave.

If you are navigating the repo manually, this is the best starting point for understanding the repository's guardrails and canonical template inventory.

## What is in this directory

- `governance/`
  - Repo-level governance and precedence documents.
  - Start here when you need the canonical policy layer behind a workflow.
- `memory-bank/`
  - The rule partitions used by routing and generation: guardrails, global rules, data rules, page rules, component rules, and styling rules.
  - Also contains machine-readable contracts such as `rules-mapping.json`, `component-policies.json`, and `component-attributes.json`.
- `db/`
  - Offline schema-dictionary markdown files used to avoid unnecessary DB connections during DB-backed planning and generation.
  - `db/index.json` is the machine-readable registry the router must inspect before asking for a DB connection.
- `apexlang/`
  - APEXlang reference material and canonical templates.
  - The main subareas are `apexlang/templates/` and `apexlang/dsl-reference.md`.
- `routing-index.json`
  - Machine-readable discovery manifest for the main routing and policy assets that live in this directory.
- `router-catalog.json`
  - Compact top-level catalog that the router should read before opening full workflow docs.
- `load-policies.json`
  - Compact policy contract for how many follow-on docs the router should open per intent.

## How to use this directory

- Read `governance/00-governance.md` when you need the canonical governance anchor.
- Read `memory-bank/` when you need rule files that shape generation behavior.
- Read `apexlang/templates/` when you need the canonical template families that workflows should reference.
- Read `../the temp-runtime logs directory under `APEXLANG_OUTPUT_ROOT/logs/`` when you need compact runtime, validator, import, or audit-log outputs.
- Read `../the temp-runtime reports directory under `APEXLANG_OUTPUT_ROOT/reports/`` when you need critiques, change logs, summaries, SQL captures, or other non-log durable artifacts.
- Read `apexlang/compiler-prop-map/` when you need the compiler-derived APEXlang property query helper for exact syntax validity checks.
- Use `router-catalog.json` and `load-policies.json` first for compact routing decisions.
- Use `routing-index.json` as a discovery manifest that points at the authoritative catalogs and machine-readable contracts.

## Important machine-readable assets

- `memory-bank/rules-mapping.json`
  - Keyword-driven selector for minimal rule loading.
- `memory-bank/component-policies.json`
  - Deterministic policy contract used by validation and critique checks.
- `memory-bank/component-attributes.json`
  - Canonical component attribute allowlist/schema.
- `db/index.json`
  - Compact registry describing eligible offline schema dictionaries under `db/*.md`.
- `routing-index.json`
  - Discovery manifest for routing-aware tooling.
- `router-catalog.json`
  - Compact top-level routing catalog.
- `load-policies.json`
  - Compact load-order and document-cap contract.

## Related ownership notes

- Policy anchor: `references/policies/governance/00-governance.md`
- Router contracts: domain `skills/*/SKILL.md` files
- Router conventions: `references/ops/one-message-router-contract.md`
- Workflow index and orchestration manifest:
  - `references/workflows/apexlang/apexlang-execution-model.md`
  - `assets/orchestration.manifest.json`

## Maintenance

- Keep this README aligned with the actual directory layout.
- Keep this file human-facing; do not turn it into a second copy of governance or router contracts.
- If a new top-level folder or machine-readable contract is added under `references/policies/`, document it here.
