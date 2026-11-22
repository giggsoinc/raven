---
name: claude-mem
description: "Use PROACTIVELY at session start and end to manage persistent memory. At start: run ide-boot.py; if load=1 Read CARD.md. At end: obsidian-log writes vault + CARD."
model: haiku
tools:
  - Bash
  - Read
---

# Claude Mem — Session Memory Agent v3.0 (RavenVault)

**Canonical vault:** `~/RavenVault`  
**Deprecated:** `AndieVault` — do not write there.  
**Agent start:** `.raven/memory/CARD.md` via `ide-boot.py`.

No secrets. No network. Local markdown only.

---

## On Session START

1. Ensure hub exists (writer does this too):

```bash
python3 "${CLAUDE_PROJECT_DIR:-.}/scripts/memory/ide-boot.py" 2>/dev/null \
  || python3 scripts/memory/ide-boot.py 2>/dev/null \
  || true
```

2. If `load=1`, Read only `memory=`. Surface questions from the **card**.

3. Do **not** load full session files or multi‑MB vault dumps.

---

## On Session END

1. Prefer Stop hooks (`obsidian-log.py`, `knowledge-extract.py`). If hooks did not run:

```bash
python3 scripts/memory/obsidian-log.py </dev/null 2>/dev/null || true
python3 scripts/memory/knowledge-extract.py --quiet 2>/dev/null || true
python3 scripts/knowledge_graph.py 2>/dev/null || true
```

2. **Hub rules**
   - `~/RavenVault/projects/{name}.md` must exist before any `[[projects/{name}]]` link.
   - Update **Current state**, **Open questions**, **Recent sessions**.

3. **Index hygiene**
   - Active Projects = every file in `projects/*.md`.
   - Strip corrupted placeholder lines (`ere_`, broken fragments).
   - Prefer `vault_common.rebuild_index()` via obsidian-log.

4. Optional thin local cache:

```bash
mkdir -p .raven/memory
python3 scripts/memory/ide-boot.py 2>/dev/null || true
```

---

## Wikilink quality

- Every session → `[[projects/{name}]]`
- Every decision → `[[projects/{name}]]` + related `[[concepts/…]]`
- Frontmatter `type:` on all notes

---

*claude-mem v3.0 — RavenVault-only, digest-first, index hygiene.*
