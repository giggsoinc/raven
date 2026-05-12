---
name: raven-scaffold
description: Use when starting a new feature, module, or component.
  Forces architecture-first planning — generates dependency map and
  implementation plan before any code is written.
---

# /scaffold

Before writing any code:

1. Read .shay-rolls/manifest.json — confirm stack
2. Read .shay-rolls/architecture.md — understand current system
3. Ask: "What are you building?" (one sentence)
4. Generate:
   - **Dependency map** — what this touches, what it needs
   - **File structure** — files to create, max 150 lines each
   - **Implementation sequence** — order of operations
   - **Risk flags** — anything that could break existing components
5. Output plan. Wait for confirmation before writing a single line.
