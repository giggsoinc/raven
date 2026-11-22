---
name: raven-plan
description: "Use when planning any new feature, module, service, or refactor. Extends Claude's Plan agent with Giggso architecture-first rules. Forces dependency mapping, file structure, and manifest compliance before any code."
---
# Raven-Plan

## Live Config
Read `.raven/manifest.json` if it exists (stack, libraries, mode) before continuing.
## Planning sequence (mandatory — no skipping)
1. Read .raven/architecture.md — understand current system
2. State what is being built in one sentence
3. Dependency map — what this touches, what it needs, what breaks if it fails
4. File structure — list every file, max 150 lines each, no god classes
5. Stack compliance — confirm everything in plan matches manifest
6. Risk flags — what could break existing components
7. Output plan → wait for confirmation → write zero code until confirmed
