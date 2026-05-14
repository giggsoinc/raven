---
name: raven-registry-register
description: Use to register a project in the Raven registry so it gets
  included in future raven-registry-sync updates. Run from inside the project
  directory, or pass the path explicitly. Also supports listing all registered
  projects and removing stale entries.
allowed-tools: Bash
---

# /raven-registry-register

Registers a project in the Raven registry (`~/.raven/registry.json`), enabling
`/raven-registry-sync` to keep it updated automatically.

**Registry:** `~/.raven/registry.json` (backed up to `giggsoinc/raven-registry`)

---

## Usage

```
/raven-registry-register                   → register current directory
/raven-registry-register --path /abs/path  → register a specific project
/raven-registry-register --list            → list all registered projects
/raven-registry-register --remove NAME     → remove a project from registry
```

---

## Steps — Register

1. **Locate raven-core**
   ```bash
   RAVEN_CORE=~/AntiGravity_Projects/raven-core
   REGISTER_SCRIPT="$RAVEN_CORE/registry/raven-register.py"
   ```
   If not found → STOP with: "raven-core not found. Check ~/AntiGravity_Projects/raven-core"

2. **Determine target path**
   - If `--path` was provided → use that path
   - Otherwise → use the project's working directory (where Claude is operating)

3. **Run registration**:
   ```bash
   python3 "$REGISTER_SCRIPT" --path "$TARGET_PATH"
   ```

4. **Show result** — expected output:
   ```
   ✅ Registered: fin-processor
      path:      /Users/you/projects/fin-processor
      remote:    https://github.com/yourorg/fin-processor.git
      version:   unknown (no .raven/raven_version found — run /raven-registry-sync)
      scripts:   ✅
      mcp:       ✅
      skills:    raven-core, raven-security, andie
   ```

5. **After registering**, suggest running `/raven-registry-sync --project NAME`
   to immediately stamp the project with the current version.

---

## Steps — List

```bash
python3 "$REGISTER_SCRIPT" --list
```

Output shows all registered projects with installed vs current version and sync status:
```
Raven Registry — 3 project(s)  [current: v2.8.0]

Name                 Installed    Status                    Remote
────────────────────────────────────────────────────────────────────────────
lockey               2.8.0        ✅ current                https://github.com/...
fin-processor        unknown      ⚠️  stale (unknown→2.8.0)  local only
Dev-Claude-Arch      2.7.0        ⚠️  stale (2.7.0→2.8.0)   local only
```

After listing, if stale projects found → suggest: "Run `/raven-registry-sync --all` to update them."

---

## Steps — Remove

```bash
python3 "$REGISTER_SCRIPT" --remove NAME
```

Confirm with user before removing:
```
Remove 'fin-processor' from registry?
Path: /Users/you/projects/fin-processor
This does NOT delete the project or its Raven files — only the registry entry.

Confirm? [y/N]:
```

---

## What Registration Detects Automatically

| Field | How detected |
|---|---|
| `name` | Directory name |
| `path` | Absolute path |
| `remote` | `git remote get-url origin` |
| `installed_version` | `.raven/raven_version` (or "unknown") |
| `components.scripts` | `.claude/scripts/` exists |
| `components.mcp` | `.claude/mcp/` exists |
| `components.skills` | Skill directories under `.claude/skills/` |

---

## After Registration

The project appears in `~/.raven/registry.json` and the `giggsoinc/raven-registry`
GitHub backup. It will be included in all future `/raven-registry-sync` runs.

**To immediately sync the new project to current version:**
```
/raven-registry-sync --project NAME
```

---

*Raven Registry v1.0 — raven-core/registry/raven-register.py*
