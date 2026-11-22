#!/usr/bin/env python3
"""
build-skill-manifest.py — skills/MANIFEST.json generator + raven-skill-manifest-check.

Every skill must be registered: name, path(s), owner, status, purpose, and —
where skills overlap — an explicit resolution: either a `layering` note
(intentional hierarchy) or deprecated/superseded_by. Unregistered skills,
ghost entries, unresolved active overlaps, and core/skills distribution
drift all fail the check.

Usage:
  python3 scripts/build-skill-manifest.py            # regenerate MANIFEST.json
  python3 scripts/build-skill-manifest.py --check    # CI lint, exit 1 on violation
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"
CLAUDE_SKILLS = REPO / ".claude" / "skills"
CORE_SKILLS = REPO / "core" / "skills"
MANIFEST = SKILLS / "MANIFEST.json"
OWNER = "raven-core-team"

# Explicit overlap resolutions (chain Prompt 4). Every entry here is a
# decision, not an observation. `domain` groups potential overlaps; two
# ACTIVE skills sharing a domain need a `layering` note or the lint fails.
OVERRIDES = {
    # -- OCI cluster: genuine duplication, resolved by deprecation --
    "oci-specialist": {
        "domain": "oci",
        "status": "deprecated",
        "superseded_by": "oracle-oci-specialist",
        "note": "Generic OCI persona superseded by the Oracle-family suite (oracle-oci-specialist).",
    },
    "oracle-oci-specialist": {"domain": "oci", "layering": "Canonical OCI skill within the oracle-* suite."},
    # -- Andie cluster: intentional layering, not duplication --
    "andie": {"domain": "andie", "layering": "Front-door orchestrator; routes to andie-jr (debug), andie-guru (explain), andie-frames (browser tests)."},
    "andie-jr": {"domain": "andie", "layering": "Brownfield debug arm of andie — receives handoffs, never orchestrates."},
    "andie-guru": {"domain": "andie", "layering": "On-demand Feynman explainer for andie output; never auto-loaded."},
    "andie-frames": {"domain": "andie", "layering": "Browser-testing arm with andie packed inside; no external skill calls."},
    # -- DB cluster: intentional layering (router -> orchestrator -> specialists) --
    "db-router": {"domain": "db", "layering": "Pure routing table; detects DB, hands to db-specialist or a per-DB specialist. Zero content."},
    "db-specialist": {"domain": "db", "layering": "Universal DB orchestrator; loads per-DB sub-skills (postgres, oracle-db, graph-db, vector-db, redis)."},
    "postgres-specialist": {"domain": "db", "layering": "Leaf specialist under db-specialist routing."},
    "oracle-db-specialist": {"domain": "db", "layering": "Leaf specialist under db-specialist routing."},
    "graph-db-specialist": {"domain": "db", "layering": "Leaf specialist under db-specialist routing."},
    "vector-db-specialist": {"domain": "db", "layering": "Leaf specialist under db-specialist routing."},
    "redis-specialist": {"domain": "db", "layering": "Leaf specialist under db-specialist routing."},
}


def _purpose(skill_md: Path) -> str:
    """First description-ish line from SKILL.md frontmatter or body."""
    try:
        text = skill_md.read_text(errors="replace")
    except OSError:
        return ""
    m = re.search(r"^description:\s*(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip().strip('"')[:200]
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith(("#", "---", "name:")):
            return line[:200]
    return ""


def discover() -> dict:
    entries = {}
    for base, origin in ((SKILLS, "skills"), (CLAUDE_SKILLS, "claude-skills")):
        if not base.is_dir():
            continue
        for d in sorted(base.iterdir()):
            skill_md = d / "SKILL.md"
            if not d.is_dir() or not skill_md.is_file():
                continue
            name = d.name
            entry = entries.setdefault(name, {
                "name": name,
                "paths": [],
                "owner": OWNER,
                "status": "active",
                "purpose": _purpose(skill_md),
            })
            entry["paths"].append(str(d.relative_to(REPO)))
            entry.update(OVERRIDES.get(name, {}))
    return entries


def check(entries: dict) -> list:
    failures = []
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"skills": {}}
    registered = manifest.get("skills", {})

    for name in entries:
        if name not in registered:
            failures.append(f"UNREGISTERED skill (add to MANIFEST.json via generator): {name}")
    for name in registered:
        if name not in entries:
            failures.append(f"GHOST manifest entry (skill dir missing): {name}")

    by_domain = {}
    for name, e in registered.items():
        if e.get("status") != "active" or not e.get("domain"):
            continue
        by_domain.setdefault(e["domain"], []).append((name, bool(e.get("layering"))))
    for domain, members in by_domain.items():
        if len(members) > 1:
            unjustified = [n for n, has_layering in members if not has_layering]
            if unjustified:
                failures.append(
                    f"AMBIGUOUS OVERLAP in domain '{domain}': active skills {unjustified} "
                    f"lack a 'layering' justification (deprecate one or declare the hierarchy)"
                )

    # core/skills is a distribution subset of skills/ — content must match.
    if CORE_SKILLS.is_dir():
        for d in sorted(CORE_SKILLS.iterdir()):
            canon = SKILLS / d.name / "SKILL.md"
            mirror = d / "SKILL.md"
            if not mirror.is_file():
                continue
            if not canon.is_file():
                failures.append(f"core/skills/{d.name} has no canonical skills/{d.name} source")
            elif canon.read_bytes() != mirror.read_bytes():
                failures.append(f"DISTRIBUTION DRIFT: core/skills/{d.name}/SKILL.md != skills/{d.name}/SKILL.md")
    return failures


def main() -> int:
    entries = discover()
    if "--check" in sys.argv:
        failures = check(entries)
        if failures:
            print("raven-skill-manifest-check: FAIL")
            for f in failures:
                print(f"  {f}")
            return 1
        print(f"raven-skill-manifest-check: PASS — {len(entries)} skills registered, overlaps resolved, no distribution drift")
        return 0

    manifest = {
        "_generated": "by scripts/build-skill-manifest.py — regenerate after adding/removing skills; "
                      "overlap resolutions live in the OVERRIDES table in that script",
        "skills": entries,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"wrote {MANIFEST.relative_to(REPO)} ({len(entries)} skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
