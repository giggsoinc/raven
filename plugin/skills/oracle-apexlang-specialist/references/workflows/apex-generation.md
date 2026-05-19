---
name: apex-developer
description: Orchestrate the APEXlang internal generate, review, and fix loop for application and page generation.
---

# Constitutional Master Playbook — APEX Developer Reference Package

## Purpose
- Single authoritative orchestration for APEXlang generation using the internal generate -> review -> fix loop.
- Enforce minimal rule loading, no fabrication, template-first drafting, and direct SQLcl runtime gates when a live roundtrip is required.

## Authoritative Policies
- `references/policies/memory-bank/00-guard/ai.guard.md`
- `references/policies/governance/00-governance.md`
- `assets/rules-mapping.json`
- `references/policies/memory-bank/systemPatterns.md`

## Operational References
- `references/workflows/apexlang/prompt-contracts.md`
- `references/workflows/apex-generation/templates.md`
- `references/workflows/apex-generation/registry.md`
- `references/workflows/apex-generation/workflow-manifests/apex-generation-master-workflow.md`
- `references/workflows/apex-generation/workflow-manifests/apex-generation-agent-suite.md`
- `assets/apex-generation/components.registry.json`
- `references/ops/reusable-prompts/prompt-normalization.md`

## Execution Agents
- `references/ops/sqlcl-agents/00-connection-gate.md`
- `references/workflows/apex-generation/agents/20-agent-draft.md`
- `references/workflows/apex-generation/agents/30-agent-critique.md`
- `references/workflows/apex-generation/agents/40-agent-revision.md`
- `references/ops/runtime-gates/02-direct-sqlcl-validate-gate.md`
- `references/ops/runtime-gates/01-direct-sqlcl-import.md`

## Loading Guidance
- Load this package from `SKILL.md` when the request needs broad orchestration, mixed-domain generation, or the full internal generate -> review -> fix loop.
- In the root-only APEXlang model, this package is not invoked as a direct skill.

## Core workflow
1. Normalize free-form input with `references/ops/reusable-prompts/prompt-normalization.md` and ask only one simple-English clarification round for critical blockers.
2. For packaged-build refresh work, classify the change as broad DSL drift or narrow component metadata delta before changing templates, examples, or packaged docs.
3. Resolve prerequisite metadata and saved-connection discovery first for APEX artifact work: inspect offline schema dictionaries, scan saved SQLcl connections, use discovered aliases as candidates, and require the user to specify the live `db_connection_name` plus corresponding APEX workspace name before live work.
4. If `db_mode = online`, continue with the resolved `db_connection_name`, APEX workspace name, and metadata/runtime gates as needed.
5. Select page and component patterns only from `templates/**`, using `page-examples/**` first for page-scoped work.
6. Use the resolved target app only for integration facts, never as a pattern or DSL source.
7. Generate APEXlang artifacts from canonical templates and rules inside the transient temp workspace.
8. Run the compiler-truth audit against the generated temp app and record `compiler-truth-report.json`; missing or failing compiler-truth evidence blocks completion.
9. Review for rule compliance, missing inputs, and required fixes.
10. Apply deterministic fixes and rerun the compiler-truth audit before publish/runtime handoff.
11. When a live roundtrip is required and `db_mode = online`, hand off to `references/ops/runtime-gates/`.

## Runtime hand-off
- Live roundtrips use direct SQLcl commands only.
- `apex validate -input` is mandatory for every live runtime hand-off.
- Runtime hand-off defaults to check-only; in user-facing responses, call that `Check APEXLang code`. After the live APEXLang check passes, offer GUI/clickable choices for `Check APEXLang code` or `Check and import APEXLang code`.
- `apex import -input` runs only after an explicit post-check GUI import choice, and then it must use the same authenticated SQLcl user session as the live check.
- Completion remains blocked until runtime status proves eligibility.
