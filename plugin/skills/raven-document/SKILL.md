---
name: raven-document
description: Use when adding or updating documentation. Enforces docstrings
  on all functions, updates architecture.md on structural changes, and keeps
  changelog current. Run before any PR merge.
allowed-tools: Read Write Edit Bash
---

# Raven-Document

## Documentation checklist
1. **Docstrings** — every function has: one-line summary, args, returns, raises
2. **architecture.md** — if structure changed: bump version + update affected sections
3. **manifest.json changelog** — if stack changed: add entry with version bump
4. **Inline comments** — complex logic only, not obvious code
5. **README** — if public API changed: update examples

## Docstring format (Google style)
```python
def function(arg: type) -> type:
    """One line summary.

    Args:
        arg: Description.

    Returns:
        Description.

    Raises:
        ValueError: When.
    """
```
