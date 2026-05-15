---
name: raven-refactor
description: Use when refactoring code to meet Raven standards. Combines
  simplify + style enforcement + type hints in one pass. Use on files flagged
  by style-enforcer or before any PR to main.
allowed-tools: Read Write Edit Bash
---

# Raven-Refactor

## Rules (non-negotiable)
- Max 150 lines per file — split if over
- Max 50 lines per function — extract if over
- All functions: type hints + docstrings
- Replace all print() with logging
- Replace Pandas with Polars if found
- Extract shared logic into base classes

## Process
1. Read the file
2. List all violations
3. Refactor — smallest change that fixes each violation
4. Do not change business logic — only structure and style
5. Confirm file still does the same thing after refactor
