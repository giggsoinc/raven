#!/usr/bin/env python3
"""
raven-sync.py — Sync Raven engine scripts and skills to all registered projects.

Reads ~/.raven/registry.json, compares installed versions against
raven-core/VERSION, updates stale projects, commits, pushes, and
updates the registry on GitHub.

Usage:
  python3 raven-sync.py                  # interactive — shows report, asks before updating
  python3 raven-sync.py --dry-run        # report only, no changes
  python3 raven-sync.py --all            # update all stale projects without prompting
  python3 raven-sync.py --project lockey # update one specific project
  python3 raven-sync.py --check          # check versions, exit 1 if any stale
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REGISTRY_DIR   = Path.home() / ".raven"
REGISTRY_FILE  = REGISTRY_DIR / "registry.json"
REGISTRY_REPO  = "https://github.com/giggsoinc/raven-registry.git"
REGISTRY_CLONE = REGISTRY_DIR / "remote"
CORE_DIR       = Path(__file__).parent.parent
VERSION_FILE   = CORE_DIR / "VERSION"
SKILLS_DIR     = Path.home() / ".claude" / "skills"

ENGINE_SCRIPTS = [
    "cve-check.py",
    "secret-scan.py",
    "audit-log.py",
    "emit-violation.py",
]

SKILLS_TO_SYNC = [
    "andie",
    "tools-landscape",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def now():
    return datetime.now(timezone.utc).isoformat()

def raven_version():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    print("❌ raven-core/VERSION not found — cannot determine current version")
    sys.exit(1)

def load_registry():
    if not REGISTRY_FILE.exists():
        print("❌ No registry found at ~/.raven/registry.json")
        print("   Run: python3 registry/raven-register.py")
        sys.exit(1)
    return json.loads(REGISTRY_FILE.read_text())

def save_registry(reg):
    reg["last_updated"] = now()
    reg["raven_current_version"] = raven_version()
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2))

def get_installed_version(project_path):
    version_file = Path(project_path) / ".raven" / "raven_version"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"

def write_version_stamp(project_path, version):
    raven_dir = Path(project_path) / ".raven"
    raven_dir.mkdir(exist_ok=True)
    (raven_dir / "raven_version").write_text(version)

def git_run(args, cwd, check=False):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=check)

def push_registry_to_github():
    clone_dir = REGISTRY_CLONE
    try:
        if not clone_dir.exists():
            subprocess.run(["git", "clone", REGISTRY_REPO, str(clone_dir)],
                           check=True, capture_output=True)
        else:
            subprocess.run(["git", "pull", "--quiet"], cwd=clone_dir,
                           capture_output=True)

        shutil.copy(REGISTRY_FILE, clone_dir / "registry.json")

        history_dir = clone_dir / "history"
        history_dir.mkdir(exist_ok=True)
        date_stamp = datetime.now().strftime("%Y-%m-%d")
        shutil.copy(REGISTRY_FILE, history_dir / f"{date_stamp}.json")

        diff = subprocess.run(["git", "diff", "--quiet", "registry.json"], cwd=clone_dir)
        if diff.returncode != 0:
            subprocess.run(["git", "add", "registry.json", "history/"], cwd=clone_dir)
            subprocess.run(
                ["git", "commit", "-m", f"registry: sync after raven-sync {now()[:10]}"],
                cwd=clone_dir, check=True
            )
            subprocess.run(["git", "push"], cwd=clone_dir, check=True)
            print("  ✅ Registry pushed to giggsoinc/raven-registry")
        else:
            print("  ✅ Registry GitHub already up to date")

    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  Registry GitHub push failed — saved locally only")

# ── Core sync ─────────────────────────────────────────────────────────────────

def sync_project(project, current_version, dry_run=False):
    name = project["name"]
    path = project["path"]

    print(f"\n  ▶ Syncing {name}")
    print(f"    path: {path}")

    if not Path(path).exists():
        print(f"    ❌ Path not found — skipping. Update registry if moved.")
        return False

    if dry_run:
        print(f"    [DRY RUN] Would update scripts, skills, version stamp")
        return False

    # 1. Engine scripts
    scripts_dest = Path(path) / ".claude" / "scripts"
    if scripts_dest.exists():
        for script in ENGINE_SCRIPTS:
            src = CORE_DIR / script
            if src.exists():
                shutil.copy(src, scripts_dest / script)
                print(f"    ✅ {script}")
            else:
                print(f"    ⚠️  {script} not found in raven-core — skipped")
    else:
        print(f"    ⚠️  .claude/scripts not found — scripts not updated")

    # 2. MCP server
    mcp_dest = Path(path) / ".claude" / "mcp"
    if mcp_dest.exists():
        mcp_src = CORE_DIR / "server.py"
        if mcp_src.exists():
            shutil.copy(mcp_src, mcp_dest / "server.py")
            print(f"    ✅ server.py (MCP)")

    # 3. Skills
    skills_dest = Path(path) / ".claude" / "skills"
    if skills_dest.exists():
        for skill in SKILLS_TO_SYNC:
            src_skill = SKILLS_DIR / skill
            dst_skill = skills_dest / skill
            if src_skill.exists():
                dst_skill.mkdir(exist_ok=True)
                for f in src_skill.iterdir():
                    if f.is_file():
                        shutil.copy(f, dst_skill / f.name)
                print(f"    ✅ skill: {skill}")
            else:
                print(f"    ⚠️  skill '{skill}' not in ~/.claude/skills — skipped")
    else:
        print(f"    ⚠️  .claude/skills not found — skills not updated")

    # 4. Version stamp
    write_version_stamp(path, current_version)
    print(f"    ✅ .raven/raven_version → {current_version}")

    # 5. Git commit + push
    has_remote = bool(project.get("remote"))
    staged = git_run(["status", "--short"], cwd=path)
    if staged.stdout.strip():
        git_run(["add", ".claude/", ".raven/raven_version"], cwd=path)
        git_run([
            "commit", "-m",
            f"chore(raven): sync to v{current_version} — scripts · skills · Andie v4.0"
        ], cwd=path)
        print(f"    ✅ committed")

        if has_remote:
            push = git_run(["push"], cwd=path)
            if push.returncode == 0:
                print(f"    ✅ pushed to {project['remote']}")
            else:
                print(f"    ⚠️  push failed: {push.stderr.strip()}")
        else:
            print(f"    ℹ️  no remote — committed locally only")
    else:
        print(f"    ℹ️  no changes to commit")

    return True

# ── Report ────────────────────────────────────────────────────────────────────

def build_report(projects, current_version):
    stale   = []
    current = []
    missing = []

    for p in projects:
        path = p["path"]
        if not Path(path).exists():
            missing.append(p)
            continue
        installed = get_installed_version(path)
        p["_installed"] = installed
        if installed == current_version:
            current.append(p)
        else:
            stale.append(p)

    return stale, current, missing

def print_report(stale, current, missing, current_version):
    print(f"\n{'─'*60}")
    print(f"  Raven Sync — current version: v{current_version}")
    print(f"{'─'*60}")

    if current:
        print(f"\n  ✅ Up to date ({len(current)})")
        for p in current:
            print(f"     {p['name']:<25} v{p['_installed']}")

    if stale:
        print(f"\n  ⚠️  Stale — needs update ({len(stale)})")
        for p in stale:
            print(f"     {p['name']:<25} v{p['_installed']} → v{current_version}")

    if missing:
        print(f"\n  ❌ Path not found ({len(missing)})")
        for p in missing:
            print(f"     {p['name']:<25} {p['path']}")

    print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Raven — Project Sync")
    parser.add_argument("--dry-run",  action="store_true", help="Report only, no changes")
    parser.add_argument("--all",      action="store_true", help="Update all stale without prompting")
    parser.add_argument("--project",  metavar="NAME",      help="Update one specific project")
    parser.add_argument("--check",    action="store_true", help="Exit 1 if any project is stale")
    args = parser.parse_args()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Raven Sync")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    reg             = load_registry()
    current_version = raven_version()
    all_projects    = reg.get("projects", [])

    if not all_projects:
        print("\nNo projects registered. Run raven-register.py first.")
        sys.exit(0)

    # Filter to single project if --project specified
    if args.project:
        all_projects = [p for p in all_projects if p["name"] == args.project]
        if not all_projects:
            print(f"\n❌ Project '{args.project}' not in registry.")
            sys.exit(1)

    stale, current, missing = build_report(all_projects, current_version)
    print_report(stale, current, missing, current_version)

    # --check mode: exit 1 if stale
    if args.check:
        sys.exit(1 if stale else 0)

    if not stale:
        print("  All projects up to date. Nothing to do.\n")
        sys.exit(0)

    # Determine which projects to update
    to_update = []

    if args.dry_run:
        print("  DRY RUN — no changes will be made\n")
        for p in stale:
            sync_project(p, current_version, dry_run=True)
        sys.exit(0)

    elif args.all:
        to_update = stale

    elif args.project:
        to_update = stale

    else:
        # Interactive
        print(f"  {len(stale)} project(s) need updating.")
        choice = input("  Update: [A]ll / [S]elect / [N]one: ").strip().upper()

        if choice == "A":
            to_update = stale
        elif choice == "S":
            for p in stale:
                ans = input(f"    Update {p['name']}? [y/N]: ").strip().lower()
                if ans == "y":
                    to_update.append(p)
        else:
            print("  Skipped.")
            sys.exit(0)

    if not to_update:
        print("  Nothing selected.\n")
        sys.exit(0)

    print(f"\n  Updating {len(to_update)} project(s)...\n")

    updated = []
    for p in to_update:
        ok = sync_project(p, current_version)
        if ok:
            # Update registry entry
            for entry in reg["projects"]:
                if entry["path"] == p["path"]:
                    entry["installed_version"] = current_version
                    entry["last_synced"] = now()
            updated.append(p["name"])

    # Save registry + push to GitHub
    if updated:
        save_registry(reg)
        print(f"\n  Updating registry...")
        push_registry_to_github()

    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Done. Updated: {', '.join(updated) if updated else 'none'}")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

if __name__ == "__main__":
    main()
