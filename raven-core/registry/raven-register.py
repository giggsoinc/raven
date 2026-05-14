#!/usr/bin/env python3
"""
raven-register.py — Register a project in the Raven registry.

Usage:
  python3 raven-register.py                    # register current directory
  python3 raven-register.py --path /abs/path   # register specific path
  python3 raven-register.py --list             # list all registered projects
  python3 raven-register.py --remove name      # remove a project from registry

Registry lives at:
  Local:  ~/.raven/registry.json
  GitHub: giggsoinc/raven-registry (private)
"""

import argparse
import json
import os
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

# ── Helpers ───────────────────────────────────────────────────────────────────

def now():
    return datetime.now(timezone.utc).isoformat()

def raven_version():
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text().strip()
    return "unknown"

def load_registry():
    if not REGISTRY_FILE.exists():
        return {
            "schema_version": "1.0",
            "raven_current_version": raven_version(),
            "registry_repo": REGISTRY_REPO,
            "last_updated": now(),
            "projects": []
        }
    return json.loads(REGISTRY_FILE.read_text())

def save_registry(reg):
    REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
    reg["last_updated"] = now()
    reg["raven_current_version"] = raven_version()
    REGISTRY_FILE.write_text(json.dumps(reg, indent=2))

def get_remote(path):
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=path, capture_output=True, text=True
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None

def get_installed_version(path):
    version_file = Path(path) / ".raven" / "raven_version"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"

def detect_components(path):
    p = Path(path)
    skills = []
    skills_dir = p / ".claude" / "skills"
    if skills_dir.exists():
        skills = [d.name for d in skills_dir.iterdir() if d.is_dir()]
    return {
        "scripts": (p / ".claude" / "scripts").exists(),
        "mcp":     (p / ".claude" / "mcp").exists(),
        "skills":  skills
    }

def push_to_github():
    """Push updated registry.json to giggsoinc/raven-registry."""
    clone_dir = REGISTRY_CLONE
    try:
        if not clone_dir.exists():
            print("  Cloning raven-registry...")
            subprocess.run(
                ["git", "clone", REGISTRY_REPO, str(clone_dir)],
                check=True, capture_output=True
            )
        else:
            subprocess.run(
                ["git", "pull", "--quiet"],
                cwd=clone_dir, check=True, capture_output=True
            )

        import shutil
        shutil.copy(REGISTRY_FILE, clone_dir / "registry.json")

        # History snapshot
        history_dir = clone_dir / "history"
        history_dir.mkdir(exist_ok=True)
        date_stamp = datetime.now().strftime("%Y-%m-%d")
        shutil.copy(REGISTRY_FILE, history_dir / f"{date_stamp}.json")

        result = subprocess.run(
            ["git", "diff", "--quiet", "registry.json"],
            cwd=clone_dir
        )
        if result.returncode != 0:
            subprocess.run(["git", "add", "registry.json", "history/"], cwd=clone_dir)
            subprocess.run(
                ["git", "commit", "-m", f"registry: sync {now()[:10]}"],
                cwd=clone_dir, check=True
            )
            subprocess.run(["git", "push"], cwd=clone_dir, check=True)
            print("  ✅ Registry pushed to GitHub")
        else:
            print("  ✅ GitHub registry already up to date")

    except subprocess.CalledProcessError as e:
        print(f"  ⚠️  GitHub push failed — registry saved locally only")
        print(f"     {e}")

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_register(project_path):
    path = str(Path(project_path).resolve())
    name = Path(path).name
    remote = get_remote(path)
    installed = get_installed_version(path)
    components = detect_components(path)

    reg = load_registry()

    existing = next((p for p in reg["projects"] if p["path"] == path), None)
    if existing:
        print(f"  Updating existing registration: {name}")
        existing["remote"] = remote
        existing["installed_version"] = installed
        existing["last_synced"] = existing.get("last_synced", now())
        existing["components"] = components
    else:
        print(f"  Registering new project: {name}")
        reg["projects"].append({
            "name": name,
            "path": path,
            "remote": remote,
            "installed_version": installed,
            "last_synced": now(),
            "registered_at": now(),
            "components": components
        })

    save_registry(reg)
    print(f"  ✅ {name} registered (version: {installed})")
    print(f"     path:   {path}")
    print(f"     remote: {remote or 'none'}")
    print(f"     skills: {len(components['skills'])} installed")

    push_to_github()

def cmd_list():
    reg = load_registry()
    current = raven_version()
    projects = reg.get("projects", [])

    if not projects:
        print("No projects registered.")
        return

    print(f"\nRaven Registry — {len(projects)} project(s)  [current: v{current}]\n")
    print(f"{'Name':<20} {'Installed':<12} {'Status':<10} {'Remote'}")
    print("─" * 80)
    for p in projects:
        installed = p.get("installed_version", "unknown")
        status = "✅ current" if installed == current else f"⚠️  stale ({installed}→{current})"
        remote = p.get("remote") or "local only"
        print(f"{p['name']:<20} {installed:<12} {status:<20} {remote}")
    print()

def cmd_remove(name):
    reg = load_registry()
    before = len(reg["projects"])
    reg["projects"] = [p for p in reg["projects"] if p["name"] != name]
    after = len(reg["projects"])
    if before == after:
        print(f"  ⚠️  Project '{name}' not found in registry")
    else:
        save_registry(reg)
        push_to_github()
        print(f"  ✅ '{name}' removed from registry")

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Raven — Project Registry")
    parser.add_argument("--path", default=os.getcwd(), help="Project path to register")
    parser.add_argument("--list", action="store_true", help="List all registered projects")
    parser.add_argument("--remove", metavar="NAME", help="Remove project from registry")
    args = parser.parse_args()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  Raven Registry")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    if args.list:
        cmd_list()
    elif args.remove:
        cmd_remove(args.remove)
    else:
        cmd_register(args.path)

    print()

if __name__ == "__main__":
    main()
