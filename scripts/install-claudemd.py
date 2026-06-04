#!/usr/bin/env python3
"""
Raven — CLAUDE.md Safe Installer (APPEND-ONLY)

CORE PRINCIPLE: Never delete anything in the user's CLAUDE.md.
                Always prepend new Raven content at the TOP.
                Existing content (Raven or user) stays untouched below.

Behavior:
  - If a Raven block with the EXACT SAME version is already at the top
    → no-op (already current — idempotent re-runs are safe).
  - If a Raven block exists but with a different version
    → prepend the new block at TOP. The old block is preserved below
      (the user can manually remove old versions if they want to).
  - If no Raven block exists
    → prepend the new block at TOP. All existing user content stays below.
  - If file is missing
    → create it with the Raven block.

Backup: every write creates CLAUDE.md.bak.{timestamp}. User content
is never destroyed — even on re-runs, the previous file is always preserved.

Markers (versioned — version is read from the source file's first line):
  <!-- RAVEN PROJECT CONFIG vX.Y.Z BEGIN -->
  <!-- RAVEN PROJECT CONFIG vX.Y.Z END -->

Usage:
  python3 install-claudemd.py --source path/to/CLAUDE.md --target /proj/CLAUDE.md
  python3 install-claudemd.py --source path/to/CLAUDE.md --target /proj/CLAUDE.md --dry-run
"""
import argparse
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

MARKER_BEGIN_RE = re.compile(
    r"<!--\s*RAVEN PROJECT CONFIG\s+v([\d.]+)\s+BEGIN\s*-->", re.IGNORECASE
)
MARKER_END_FMT_RE = re.compile(
    r"<!--\s*RAVEN PROJECT CONFIG\s+v([\d.]+)\s+END\s*-->", re.IGNORECASE
)
VERSION_HEADER_RE = re.compile(
    r"#\s+CLAUDE\.md\s+—\s+Raven Discipline Engine\s+v([\d.]+)", re.IGNORECASE
)


def extract_version(source_text: str) -> str:
    """Read Raven version from the source CLAUDE.md header. Falls back to 'unknown'."""
    m = VERSION_HEADER_RE.search(source_text)
    return m.group(1) if m else "unknown"


def already_at_top(target_text: str, version: str) -> bool:
    """True iff a Raven block with this exact version is already at the top of target."""
    head = target_text.lstrip()
    expected_begin = f"<!-- RAVEN PROJECT CONFIG v{version} BEGIN -->"
    return head.startswith(expected_begin)


def wrap(source_text: str, version: str) -> str:
    """Wrap source content in versioned BEGIN/END markers."""
    begin = f"<!-- RAVEN PROJECT CONFIG v{version} BEGIN -->"
    end   = f"<!-- RAVEN PROJECT CONFIG v{version} END -->"
    # Strip any markers that might already be in the source — we add our own
    body = source_text
    for pat in (MARKER_BEGIN_RE, MARKER_END_FMT_RE):
        body = pat.sub("", body)
    body = body.strip()
    return f"{begin}\n{body}\n{end}\n"


def prepend(source_text: str, target_text: str, version: str) -> str:
    """Build new target: Raven block at TOP, all existing content below."""
    block = wrap(source_text, version)
    if not target_text.strip():
        return block
    separator = (
        "\n"
        "<!-- ─────────────────────────────────────────────────────────── -->\n"
        "<!-- Content below this line is preserved from previous version. -->\n"
        "<!-- Raven never deletes — you can manually remove old sections. -->\n"
        "<!-- ─────────────────────────────────────────────────────────── -->\n\n"
    )
    return f"{block}{separator}{target_text.lstrip()}"


def main() -> int:
    p = argparse.ArgumentParser(description="Raven CLAUDE.md safe installer (append-only)")
    p.add_argument("--source", required=True, help="Path to source CLAUDE.md (framework canonical)")
    p.add_argument("--target", required=True, help="Path to project CLAUDE.md to update")
    p.add_argument("--dry-run", action="store_true", help="Print result, do not write")
    p.add_argument("--quiet",   action="store_true", help="Suppress non-error output")
    args = p.parse_args()

    source_path = Path(args.source)
    target_path = Path(args.target)

    if not source_path.exists():
        sys.stderr.write(f"❌ Source not found: {source_path}\n")
        return 2

    source_text = source_path.read_text()
    target_text = target_path.read_text() if target_path.exists() else ""
    version     = extract_version(source_text)

    # Idempotent check — already current at top?
    if already_at_top(target_text, version):
        if not args.quiet:
            print(f"✓ CLAUDE.md already at v{version} (top of file) — no changes")
        return 0

    new_text = prepend(source_text, target_text, version)

    if args.dry_run:
        sys.stdout.write(new_text)
        return 0

    # Backup whenever a file exists with any content — never destroy silently
    if target_text.strip():
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = target_path.with_suffix(target_path.suffix + f".bak.{ts}")
        shutil.copy2(target_path, backup)
        if not args.quiet:
            print(f"📦 Backup: {backup.name}")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(new_text)

    if not args.quiet:
        if not target_text.strip():
            print(f"✅ CLAUDE.md created at v{version}: {target_path}")
        else:
            # Detect if older Raven block was preserved
            existing_versions = [m.group(1) for m in MARKER_BEGIN_RE.finditer(target_text)]
            older = [v for v in existing_versions if v != version]
            if older:
                print(f"✅ CLAUDE.md v{version} prepended — older v{','.join(sorted(set(older)))} preserved below")
            else:
                print(f"✅ CLAUDE.md v{version} prepended — existing content preserved below")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        sys.stderr.write(f"❌ install-claudemd error: {type(e).__name__}: {e}\n")
        sys.exit(1)
