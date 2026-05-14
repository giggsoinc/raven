---
name: raven-registry-sync
description: Use to sync all registered Raven projects to the current engine
  version. Reads ~/.raven/registry.json, diffs installed versions against
  raven-core/VERSION, updates stale projects (scripts, MCP, skills, version
  stamp), commits each, pushes to GitHub, and updates the registry backup.
  Run after any raven-core update or when deploying Raven to registered projects.
allowed-tools: Bash
---

# /raven-registry-sync

Syncs all registered Raven projects to the current engine version.

**Source of truth:** `raven-core/VERSION`  
**Registry:** `~/.raven/registry.json` (backed up to `giggsoinc/raven-registry`)

---

## Usage

```
/raven-registry-sync              → interactive: shows report, asks before updating
/raven-registry-sync --dry-run    → report only, no changes made
/raven-registry-sync --all        → update all stale projects without prompting
/raven-registry-sync --project NAME → update one specific project
/raven-registry-sync --check      → CI mode: exit 1 if any project stale
```

---

## Steps

1. **Locate raven-core**
   ```bash
   RAVEN_CORE=~/AntiGravity_Projects/raven-core
   SYNC_SCRIPT="$RAVEN_CORE/registry/raven-sync.py"
   ```
   If not found → STOP with: "raven-core not found at expected path. Check ~/AntiGravity_Projects/raven-core"

2. **Run the sync script** with the flags passed by the user:
   ```bash
   python3 "$SYNC_SCRIPT" [FLAGS]
   ```

3. **Show output** — the script produces a full report:
   ```
   ────────────────────────────────────────────────────────────
     Raven Sync — current version: v2.8.0
   ────────────────────────────────────────────────────────────
   
     ✅ Up to date (1)
        lockey                    v2.8.0
   
     ⚠️  Stale — needs update (2)
        fin-processor             v2.7.0 → v2.8.0
        Dev-Claude-Arch           unknown → v2.8.0
   
     ❌ Path not found (0)
   ```

4. **After sync completes**, confirm:
   - Which projects were updated
   - Which were committed and pushed
   - Registry GitHub status

---

## What Gets Updated Per Project

| Component | Destination |
|---|---|
| Engine scripts (4 py files) | `.claude/scripts/` |
| MCP server (`server.py`) | `.claude/mcp/` |
| Andie skill | `.claude/skills/andie/` |
| Tools landscape | `.claude/skills/tools-landscape/` |
| Version stamp | `.raven/raven_version` |
| Git commit | Auto-committed |
| Git push | Auto-pushed (if remote exists) |

Projects with no remote → committed locally, no push.

---

## What Gets Updated After All Projects

- `~/.raven/registry.json` → `installed_version` and `last_synced` updated
- `giggsoinc/raven-registry` → pushed to GitHub as backup

---

## Error Handling

- **Path not found** → skipped, reported. Update registry if project moved.
- **Push failed** → committed locally, push error reported. Re-run after fixing remote.
- **Script not found** → stop immediately and show exact missing path.

---

## Typical Workflow (after bumping VERSION)

```bash
# 1. Bump version
echo "2.9.0" > ~/AntiGravity_Projects/raven-core/VERSION

# 2. Bundle to platform repos
bash ~/AntiGravity_Projects/raven-core/bundle.sh

# 3. Commit and push raven-core + SHAY-ROLLS
# (then run:)
/raven-registry-sync --all
```

---

*Raven Registry v1.0 — raven-core/registry/raven-sync.py*
