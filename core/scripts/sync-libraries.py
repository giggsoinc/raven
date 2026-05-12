#!/usr/bin/env python3
# Raven — Library Sync
# Reads requirements.txt / pyproject.toml / poetry.lock / setup.py
# Adds all found libraries to manifest.json stack.libraries
# CVE checks each one. Approved = added. Blocked = flagged.
# Run: python3 .claude/scripts/sync-libraries.py
#      python3 .claude/scripts/sync-libraries.py --dry-run

import json, os, re, sys, subprocess, argparse
from pathlib import Path

DRY_RUN = "--dry-run" in sys.argv

MANIFEST = ".raven/manifest.json"
G = '\033[0;32m'
Y = '\033[1;33m'
R = '\033[0;31m'
B = '\033[0;34m'
N = '\033[0m'

# Stdlib — never add these
STDLIB = {
    "os","sys","json","re","pathlib","typing","datetime","collections",
    "itertools","functools","abc","dataclasses","asyncio","contextlib",
    "io","math","random","hashlib","uuid","copy","enum","time",
    "threading","subprocess","argparse","inspect","traceback","warnings",
    "weakref","signal","builtins","string","struct","types","numbers",
    "operator","socket","ssl","http","urllib","email","html","xml",
    "csv","sqlite3","logging","unittest","shutil","tempfile","glob",
    "fnmatch","stat","platform","ctypes","pickle","shelve","gzip","zipfile"
}

def find_requirements() -> list[str]:
    """Find all library requirements from common files."""
    libs = []

    # requirements.txt
    for fname in ["requirements.txt","requirements-dev.txt","requirements/base.txt",
                  "requirements/prod.txt","requirements/dev.txt"]:
        if Path(fname).exists():
            for line in open(fname):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    # Strip version specifiers
                    name = re.split(r'[>=<!;\[]', line)[0].strip().lower()
                    name = name.replace("_","-")
                    if name and name not in STDLIB:
                        libs.append(name)
            print(f"  {G}✅ Read {fname}{N}")

    # pyproject.toml
    if Path("pyproject.toml").exists():
        content = open("pyproject.toml").read()
        # Match dependencies = [...] or [tool.poetry.dependencies]
        for match in re.findall(r'"([a-zA-Z0-9_\-]+)\s*[>=<!]', content):
            name = match.lower().replace("_","-")
            if name not in STDLIB and name != "python":
                libs.append(name)
        print(f"  {G}✅ Read pyproject.toml{N}")

    # setup.py / setup.cfg
    if Path("setup.py").exists():
        content = open("setup.py").read()
        for match in re.findall(r"'([a-zA-Z0-9_\-]+)\s*[>=<!]?", content):
            name = match.lower().replace("_","-")
            if name not in STDLIB:
                libs.append(name)

    return list(set(libs))

def load_manifest() -> dict:
    try:
        return json.load(open(MANIFEST))
    except Exception as e:
        print(f"{R}❌ Cannot read manifest: {e}{N}")
        sys.exit(1)

def save_manifest(m: dict):
    with open(MANIFEST, "w") as f:
        json.dump(m, f, indent=2)

def already_approved(lib: str, manifest: dict) -> bool:
    """Check if lib is already in any approved list."""
    stack = manifest.get("stack", {})
    existing = stack.get("libraries", [])
    if isinstance(existing, list):
        if lib in existing:
            return True
    # Check org whitelist
    for tier in manifest.get("approved_skills", {}).values():
        if isinstance(tier, list) and lib in tier:
            return True
    return False

def run_cve_check(lib: str) -> tuple[str, str]:
    """Run cve-check.py. Returns (action, message)."""
    script = ".claude/scripts/cve-check.py"
    if not Path(script).exists():
        return "skip", "cve-check.py not found"
    try:
        result = subprocess.run(
            ["python3", script, "--library", lib],
            capture_output=True, text=True, timeout=20
        )
        msg = (result.stdout + result.stderr).strip()
        if result.returncode == 0:   return "approve", msg
        elif result.returncode == 1: return "block",   msg
        elif result.returncode == 2: return "warn",    msg
        else:                        return "approve",  msg
    except Exception as e:
        return "skip", str(e)

def main():
    parser = argparse.ArgumentParser(description="Raven Library Sync")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change, don't write")
    parser.add_argument("--no-cve",  action="store_true", help="Skip CVE check, approve all found libs")
    args = parser.parse_args()

    print(f"\n{B}Raven Library Sync{N}")
    print(f"{'Dry run — no changes will be written' if args.dry_run else 'Live mode — manifest will be updated'}\n")

    manifest = load_manifest()
    found    = find_requirements()

    if not found:
        print(f"{Y}No requirements files found. Nothing to sync.{N}\n")
        return

    print(f"\nFound {len(found)} libraries. Checking against manifest...\n")

    to_approve = []
    blocked    = []
    skipped    = []
    already    = []

    for lib in sorted(found):
        if already_approved(lib, manifest):
            already.append(lib)
            continue

        if args.no_cve:
            to_approve.append(lib)
            print(f"  {G}+ {lib}{N} (CVE skipped)")
            continue

        action, msg = run_cve_check(lib)

        if action == "approve":
            to_approve.append(lib)
            print(f"  {G}✅ {lib}{N} — clean")
        elif action == "block":
            blocked.append(lib)
            print(f"  {R}❌ {lib}{N} — BLOCKED: {msg[:80]}")
        elif action == "warn":
            to_approve.append(lib)
            print(f"  {Y}⚠️  {lib}{N} — moderate risk, added with warning")
        else:
            skipped.append(lib)
            print(f"  {Y}?  {lib}{N} — CVE check inconclusive, skipped")

    # Update manifest
    if not args.dry_run and to_approve:
        existing = manifest.setdefault("stack", {}).setdefault("libraries", [])
        for lib in to_approve:
            if lib not in existing:
                existing.append(lib)
        existing.sort()
        save_manifest(manifest)

    # Summary
    print(f"\n{'━'*50}")
    print(f"  Already approved: {len(already)}")
    print(f"  {G}Newly approved:   {len(to_approve)}{N}")
    print(f"  {R}Blocked (CVE):    {len(blocked)}{N}")
    print(f"  Skipped:          {len(skipped)}")
    if blocked:
        print(f"\n  {R}Blocked libraries — remove from requirements or get manual approval:{N}")
        for b in blocked:
            print(f"    ❌ {b}")
    if not args.dry_run and to_approve:
        print(f"\n  {G}manifest.json updated — {len(to_approve)} libraries added{N}")
    print(f"{'━'*50}\n")

if __name__ == "__main__":
    main()
