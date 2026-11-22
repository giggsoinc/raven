#!/usr/bin/env python3
"""
check-engine-drift.py — raven-engine-drift-check (CI + local).

The engine lives canonically in scripts/. raven-core/ and .claude/scripts/
carry same-named entries (relative symlinks in-repo). This check fails if any
same-named entry's CONTENT (symlinks followed) differs from its canonical
scripts/ source, or if any symlink is broken/absolute.

Exit 0 = no drift. Exit 1 = drift (each divergence listed).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CANONICAL = REPO / "scripts"
MIRRORS = [REPO / "raven-core", REPO / ".claude" / "scripts"]


def main() -> int:
    failures = []
    for mirror in MIRRORS:
        if not mirror.is_dir():
            continue
        for entry in sorted(mirror.glob("*.py")):
            canon = CANONICAL / entry.name
            if not canon.is_file():
                continue  # mirror-unique file — allowed, not drift
            if entry.is_symlink():
                target = entry.readlink()
                if target.is_absolute():
                    failures.append(f"ABSOLUTE SYMLINK (breaks other clones): {entry} -> {target}")
                    continue
                if not entry.resolve().exists():
                    failures.append(f"BROKEN SYMLINK: {entry} -> {target}")
                    continue
            try:
                if entry.read_bytes() != canon.read_bytes():
                    failures.append(f"CONTENT DRIFT: {entry} != {canon}")
            except OSError as e:
                failures.append(f"UNREADABLE: {entry} ({e})")

    if failures:
        print("raven-engine-drift-check: FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print("raven-engine-drift-check: PASS — all mirror entries match scripts/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
