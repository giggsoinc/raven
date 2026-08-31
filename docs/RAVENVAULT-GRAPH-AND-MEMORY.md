# RavenVault — Knowledge graph, dashboard & agent memory

> **Current boot (2026-08-22):** agents use `ide-boot.py` + `.raven/memory/CARD.md`. Section 6 packaging text below still mentions copying `vault-load` as a **historical 4.2.0** recipe — do not wire `vault-load` on SessionStart.

**Audience:** Developers using Raven (Claude, Grok, Codex, Enterprise)  
**Vault root:** `~/RavenVault`  
**Build id (HTML):** `kg-v2-grounded+cite`  
**Related:** `docs/obsidian-knowledge-graph-plan.md`, `docs/grok-vault-playbook.md`

---

## 1. What problem this solves

Teams expected:

1. An **Obsidian knowledge graph** (projects, concepts, decisions, short sessions).  
2. Agents that **load memory at session start** (not blank chats).  
3. A **Raven HTML dashboard** that shows that graph **and** costs — with every number **cited**.

Previously: session notes were git dumps; project hubs were missing; dashboard was tokenomics-only; costs often showed `$0.00` while data existed; local clone paths were missing for nested repos.

---

## 2. Architecture (simple)

```
First load                         During work                 Stop
─────────────                      ──────────                  ────
ide-boot.py                        guards + routers            token-meter-write.py
  → host + load=0|1                edits / tools                 → ~/RavenVault/.metrics/
  → if load=1: Read CARD.md                                    obsidian-log.py
session-start.py (Claude only)                                   → vault sessions + hub
  → brownfield/models — NO vault                                 → .raven/memory/CARD.md
                                                               knowledge-extract.py
                                                               (optional) knowledge_graph.py
                                                                 → graph JSON (humans/dashboard)

Human: python3 scripts/dashboard.py --html --open
  → ~/RavenVault/dashboard.html
```

| Path | Role |
|------|------|
| `~/RavenVault` | **Canonical** Obsidian vault + metrics + dashboard (humans) |
| `.raven/memory/CARD.md` | **Agent** start surface (seeded on first boot if missing; refreshed on Stop) |
| `.raven/boot.json` | IDE env → native rules file |
| `AndieVault` | **Deprecated** — do not use |

---

## 3. How agent memory works (new session)

### What the agent loads at start

1. Native rules file for this IDE (see README host table) says: run **`scripts/memory/ide-boot.py`**.  
2. If `load=1`, Read **only** `.raven/memory/CARD.md` (schema 1, open questions/decisions, dashboard path).  
3. If the card is missing, ide-boot writes a schema-1 `status: NONE` card (no invented history), then `load=1` and Read it. Invalid schema still `load=0`.  
4. Claude `SessionStart` still runs **`session-start.py`** (banner/models) — it does **not** shell `vault-load.py`.  
5. `vault-load.py` remains a **manual** dump for humans.

### What is written at session end (Stop)

| Script | Writes | Content rules |
|--------|--------|----------------|
| `token-meter-write.py` | `.raven/.model-session.json`, `~/RavenVault/.metrics/YYYY-MM.json` | **Per-project** tokens/cost (`by_project`, day nest) |
| `obsidian-log.py` | `sessions/YYYY-MM-DD-{project}.md` | Hub-first, ≤ ~80 lines/entry, capped git status |
| `knowledge-extract.py` | `concepts/`, sometimes `decisions/` | Fail-soft path signals |
| Index | `index/README.md` | Rebuilt from `projects/*.md` (no garbage) |

### Why this is “memory”

- **Human memory:** Obsidian graph + dashboard briefings.  
- **Agent memory:** the **card** (projection of hub questions/decisions), not the vault dump.  
- **Not memory:** Full git status dumps, multi‑MB transcripts, unscoped legacy cost rollups.

### How to verify memory is live

```bash
python3 scripts/memory/ide-boot.py
# optional human dump:
python3 scripts/memory/vault-load.py
# Should print open questions / last sessions for current repo

# After a session ends (or dry-run):
echo '{}' | python3 scripts/obsidian-log.py
ls ~/RavenVault/sessions/ | tail
ls ~/RavenVault/projects/
```

---

## 4. Knowledge graph — how to use it

**Vibe-coder (zero code skills):** [VIBE-CODER-MAP.md](./VIBE-CODER-MAP.md) — icons, picture dictionary, click-only workflow.  
Icons: `assets/kg-icons/*.svg` + `scripts/kg_icons.py` (frontmatter `icon:` or keyword match).

### Build / open

```bash
# From a Raven-enabled repo (or the raven product repo)
python3 scripts/dashboard.py --html --open

# Graph only
python3 scripts/dashboard.py --graph-only --open

# One project filter
python3 scripts/dashboard.py --html --project raven --open

# JSON only
python3 scripts/dashboard.py --graph-json
# → ~/RavenVault/graph/knowledge-graph.json
```

Also open vault in Obsidian: folder `~/RavenVault` → Graph view.

### On the HTML page

| UI | Action |
|----|--------|
| **◎ Center overview** | Portfolio briefing (all graph projects) |
| **Node click** (canvas or list) | Summary (Andie–Guru) · last update · cost/CVE · links |
| **Empty canvas** | Same as Center |
| **Project chips** | Briefing · **GitHub ↗** · **Local 📁** |
| **Per-repo table** | Sessions / tokens / cost + links |
| **Blue [C#]** | Jump to **Citations** bibliography |
| **Open local repo** | `file://` path to clone |
| **Vault note** | Hub markdown under RavenVault |

### Local path discovery

If hub has no `Local:` line, dashboard **searches** (depth ≤ 5) under:

- `~/AntiGravity_Projects` (includes nested e.g. `Proj1/fin-processor`)  
- `~/Projects`, `~/Developer`, `~/src`, `~/code`  

Prefers `.git` roots; rejects weak `docs/…` matches. On success, **writes** `Local:` into `projects/{name}.md` (creates hub if missing).

Hub format:

```markdown
## Repo
- GitHub: https://github.com/giggsoinc/fin-processor
- Local: /Users/you/AntiGravity_Projects/Proj1/fin-processor
```

### Costs — two columns (do not confuse them)

| Column | What it is | Accurate for |
|--------|------------|--------------|
| **Raven-metered** | Token consumption seen by Raven hooks × model rate card (`log-overhead`, `token-meter-write` × `model-pricing.json`) | Local discipline / overhead / partial session capture |
| **Claude / external** | Numbers you or Claude paste into `~/RavenVault/.metrics/external-usage.json` (Console, export, estimate) | Real money when filled from Anthropic billing |

Dashboard sections:

1. **Cost method** — explains both sources  
2. **Cost compare** — side-by-side per repo + Δ  
3. **Headline numbers** — **Raven-metered only**, each value cited **[C#]**

#### Ask Claude to supply external data (paste this)

```
Copy Anthropic Console usage (or your best estimate) into
~/RavenVault/.metrics/external-usage.json using the template at
~/RavenVault/.metrics/external-usage.template.json.
Include by_project entries (e.g. fin-processor) with tokens + cost_usd
for the same ~30 day window as the Raven dashboard.
Then run: python3 scripts/dashboard.py --html --open
and open the side-by-side Cost compare section.
Do not invent per-repo splits if you only have org totals — put those under total.notes.
```

| Card (Raven column) | Source citation |
|------|-----------------|
| All repos | **[C1]** `~/RavenVault/.metrics/*.json` project-tagged rows |
| This repo | **[C2]** same, filtered by project |
| Live session | **[C3]** `.raven/.model-session.json` |
| Graph size | **[C4]** `graph/knowledge-graph.json` |
| Notes / hubs | **[C5]** vault markdown |
| Guards | **[C6]** `.raven/audit/*.log` |

**Not in Raven headlines:** unscoped legacy `by_day` (no project; historically inflated).  
**Small Raven $ amounts** often mean only router overhead was metered — still shown as `$0.000212`, never `$0.00`.

---

## 5. Scripts (source of truth)

| File | Purpose |
|------|---------|
| `scripts/vault_common.py` | Hub ensure, index rebuild, wikilinks, paths |
| `scripts/memory/vault-load.py` | Manual vault dump only (not boot) |
| `scripts/obsidian-log.py` | Stop: trimmed session + hub + index |
| `scripts/knowledge-extract.py` | Concepts/decisions (fail-soft) |
| `scripts/knowledge_graph.py` | Vault → JSON graph |
| `scripts/dashboard.py` | HTML: graph, costs, citations, local discovery |
| `scripts/token-meter-write.py` | Per-project metrics rollup |
| `scripts/session/session-start.py` | Claude SessionStart banner — no vault-load |
| `agents/claude-mem.md` | RavenVault-only mem agent |
| `plugin/settings.json` | SessionStart + Stop hooks |
| `tests/test_knowledge_graph.py` | Parse + graph + HTML markers |

Copy the same set into `raven-core/` and `plugin/scripts/` when releasing.

---

## 6. Packaging as a new Raven version (recommended **4.2.0**)

### Why 4.2.0

Feature release: agent vault load, knowledge graph export, dashboard graph + citations, local path discovery, per-project metrics. Not a patch on 4.1.0 docs-only.

### Release checklist

1. **Bump versions**
   - `.claude-plugin/plugin.json` → `"version": "4.2.0"`
   - `plugin/make-plugin.sh` → `VERSION="4.2.0"`
   - `raven-core/VERSION` → `4.2.0`
   - `.raven/manifest.json` `version` if product repo tracks engine
   - `scripts/dashboard.py` `PLUGIN_VERSION` if still hard-coded
   - Extend `version-check.py` `RAVEN_RELEASES` with `"4.1.0", "4.2.0"`

2. **Sync scripts**
   ```bash
   for f in vault_common.py vault-load.py knowledge-extract.py knowledge_graph.py \
            obsidian-log.py session-start.py token-meter-write.py dashboard.py; do
     cp -f scripts/$f raven-core/$f
     cp -f scripts/$f plugin/scripts/$f
   done
   cp -f agents/claude-mem.md plugin/agents/ core/agents/
   # settings already wired in plugin/settings.json + core/hooks/settings.json
   ```

3. **Tests**
   ```bash
   python3 -m unittest tests.test_knowledge_graph -v
   python3 scripts/dashboard.py --html
   test -f ~/RavenVault/dashboard.html
   grep -q 'kg-v2-grounded' ~/RavenVault/dashboard.html
   ```

4. **Plugin zip**
   ```bash
   bash plugin/make-plugin.sh
   # Ensure make-plugin.sh lists: vault_common, vault-load, knowledge-extract,
   # knowledge_graph, dashboard, obsidian-log, token-meter-write
   ```

5. **Docs in tag**
   - This file  
   - `docs/obsidian-knowledge-graph-plan.md`  
   - `docs/grok-vault-playbook.md`  
   - Changelog entry (see below)

6. **Git**
   ```bash
   git add -A  # exclude .raven/.cache, .model-session, secrets
   git commit -m "feat(vault): knowledge graph, agent digest, cited dashboard (v4.2.0)"
   git tag v4.2.0
   git push origin main --tags
   gh release create v4.2.0 --title "Raven v4.2.0 — RavenVault graph & agent memory" \
     --notes-file docs/CHANGELOG-4.2.0-vault-graph.md
   ```

### Suggested changelog blurb

```markdown
## v4.2.0 — RavenVault knowledge graph & agent memory
- Agent boot is `ide-boot.py` + CARD.md (vault-load is not SessionStart)
- Trimmed obsidian-log + project hub auto-create + index hygiene
- knowledge-extract + knowledge-graph.json export
- dashboard.py: interactive graph, dual cost headlines, on-page citations,
  nested local-path discovery, GitHub + Local links
- token-meter per-project by_project rollups
- claude-mem RavenVault-only; Grok playbook
```

---

## 7. Apply to other Raven variants

Use the **portable apply prompt** in:

`docs/APPLY-PROMPT-vault-graph-memory.md`

Paste that entire prompt into a session on those repos (or run from monorepo copy). Do not invent Hub-only behavior for OSS paths; Enterprise may add Hub later without changing vault file layout.

---

## 8. Day-to-day developer workflow

1. Work in a repo with Raven hooks.  
2. **Start session** → agent gets vault digest automatically.  
3. **Code** → guards fire as usual.  
4. **End session** → metrics + session note + hub update.  
5. **Review**  
   ```bash
   python3 scripts/dashboard.py --html --open
   ```  
6. Click project → Summary / costs / **Local 📁** / GitHub.  
7. Optional: open `~/RavenVault` in Obsidian for full graph editing.

---

*RavenVault graph + memory user guide — pairs with implementation plan and apply prompt.*
