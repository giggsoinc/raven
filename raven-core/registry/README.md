# Raven Registry

Central sync system for Raven. Tracks every project that has Raven installed and keeps them all on the current engine version — like an app store update mechanism.

---

## How It Works

```
raven-core/VERSION          ← single source of truth for current Raven version
~/.raven/registry.json      ← local manifest of all registered projects
giggsoinc/raven-registry    ← private GitHub backup (survives machine wipes)

raven-register.py           ← adds a project to the registry
raven-sync.py               ← syncs all stale projects to current version
```

### The iPhone App Store analogy

| App Store concept | Raven equivalent |
|---|---|
| App Store server | `raven-core` (source of truth) |
| Apps on your phone | `lockey`, `fin-processor`, etc. (installed copies) |
| App version number | `raven-core/VERSION` |
| Installed version | `.raven/raven_version` in each project |
| "Check for updates" | `raven-sync.py --dry-run` |
| "Update all" | `raven-sync.py --all` |
| iCloud backup | `giggsoinc/raven-registry` (GitHub) |

---

## Files

| File | Purpose |
|---|---|
| `raven-register.py` | Register a project. Run once per project at setup time. |
| `raven-sync.py` | Sync all stale projects to current Raven version. |
| `registry-schema.json` | JSON schema for registry.json — reference only. |
| `README.md` | This file. |

---

## Registry Location

```
~/.raven/
├── registry.json       ← local copy (fast, always available)
└── remote/             ← cloned giggsoinc/raven-registry (auto-managed)
```

The registry is NOT stored inside any project repo. It lives at the machine level (`~/.raven/`) so deleting any individual project repo has zero impact on the registry.

GitHub backup at `giggsoinc/raven-registry` (private) means the registry survives a full machine wipe.

---

## Usage

### Register a new project

```bash
# From the project directory
cd ~/AntiGravity_Projects/lockey
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py

# Or specify path explicitly
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py \
  --path ~/AntiGravity_Projects/lockey
```

### List all registered projects

```bash
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py --list
```

Output:
```
Raven Registry — 3 project(s)  [current: v2.8.0]

Name                 Installed    Status               Remote
────────────────────────────────────────────────────────────────────────────────
lockey               2.7.0        ⚠️  stale (2.7.0→2.8.0)  https://github.com/...
fin-processor        2.6.0        ⚠️  stale (2.6.0→2.8.0)  local only
Dev-Claude-Arch      2.8.0        ✅ current               local only
```

### Check what needs updating (no changes)

```bash
python3 ~/AntiGravity_Projects/raven-core/registry/raven-sync.py --dry-run
```

### Update all stale projects

```bash
python3 ~/AntiGravity_Projects/raven-core/registry/raven-sync.py --all
```

### Update one specific project

```bash
python3 ~/AntiGravity_Projects/raven-core/registry/raven-sync.py --project lockey
```

### Interactive update (asks project by project)

```bash
python3 ~/AntiGravity_Projects/raven-core/registry/raven-sync.py
```

### Remove a project from registry

```bash
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py --remove lockey
```

---

## What raven-sync updates in each project

1. **Engine scripts** — `cve-check.py`, `secret-scan.py`, `audit-log.py`, `emit-violation.py` → copied to `.claude/scripts/`
2. **MCP server** — `server.py` → copied to `.claude/mcp/`
3. **Andie skill** — `~/.claude/skills/andie/SKILL.md` → copied to `.claude/skills/andie/`
4. **Tools landscape** — `~/.claude/skills/tools-landscape/` → copied to `.claude/skills/tools-landscape/`
5. **Version stamp** — writes `.raven/raven_version` with current version number
6. **Git commit** — commits all changes with standard message
7. **Git push** — pushes to GitHub if remote exists

After all projects are updated:
8. **Registry update** — updates `installed_version` and `last_synced` for each project
9. **GitHub push** — pushes updated registry to `giggsoinc/raven-registry`

---

## Adding a new project — full flow

```bash
# 1. Install Raven in the project
cd ~/AntiGravity_Projects/new-project
bash ~/AntiGravity_Projects/SHAY-ROLLS/CLAUDE/RAVEN/raven-setup.sh

# 2. Register it (raven-setup.sh does this automatically if wired up)
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py

# 3. Verify it appears in registry
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py --list
```

---

## Restore registry on a new machine

```bash
# Clone the backup
git clone https://github.com/giggsoinc/raven-registry.git ~/.raven/remote

# Copy registry to canonical location
cp ~/.raven/remote/registry.json ~/.raven/registry.json

# Verify
python3 ~/AntiGravity_Projects/raven-core/registry/raven-register.py --list
```

---

## Releasing a new Raven version

```bash
# 1. Update version
echo "2.9.0" > ~/AntiGravity_Projects/raven-core/VERSION

# 2. Bundle engine scripts to platform repos
bash ~/AntiGravity_Projects/raven-core/bundle.sh

# 3. Commit raven-core + RAVEN monorepo
git -C ~/AntiGravity_Projects/raven-core add -A && git -C ~/AntiGravity_Projects/raven-core commit -m "release: v2.9.0"
git -C ~/AntiGravity_Projects/raven-core push

# 4. Sync all registered projects
python3 ~/AntiGravity_Projects/raven-core/registry/raven-sync.py --all
```

One command (step 4) updates every registered project, commits each one, pushes to GitHub, and updates the registry.

---

*Raven Registry v1.0 — Part of [giggsoinc/raven-core](https://github.com/giggsoinc/raven-core)*
