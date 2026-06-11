#!/usr/bin/env python3
"""
Raven — UserPromptSubmit Hook
Fires before every model response on brownfield/Raven projects.
Injects the mandatory domain skill trigger into model context.

This is the enforcement layer — it fires every single prompt so the
model cannot "forget" which skill to invoke. Silent on non-Raven projects.

Never reads .env or credential files. No external dependencies.
"""

import json, sys
from pathlib import Path

# Domain → skill map (same order / logic as session-start.py)
# Signal strength contract (precision fix):
#   STRONG — proprietary marker file, domain-proprietary extension
#            ("strong_globs": True), or a dependency/content keyword hit.
#   WEAK   — generic directory names. One weak signal → advisory only;
#            two agreeing weak signals → strong.
DOMAIN_SKILL_MAP = [
    {
        "name":          "Salesforce",
        "skill":         "raven:salesforce-specialist",
        "markers":       ["sfdx-project.json", ".forceignore"],
        "dirs":          ["force-app"],
        "globs":         [],
    },
    {
        "name":          "Odoo",
        "skill":         "raven:odoo-specialist",
        "markers":       ["odoo.conf", ".odoo_upgrade.json"],
        "dirs":          [],
        "globs":         ["**/__manifest__.py"],
        "strong_globs":  True,  # Odoo-proprietary filename
    },
    {
        "name":          "Terraform",
        "skill":         "raven:terraform-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         ["*.tf"],
        "strong_globs":  True,  # .tf is Terraform-proprietary
    },
    # "charts" dir removed: it matched JS charting/asset folders.
    {
        "name":          "Kubernetes",
        "skill":         "raven:k8s-specialist",
        "markers":       ["Chart.yaml"],
        "dirs":          ["k8s", "kubernetes", "helm"],
        "globs":         [],
    },
    {
        "name":          "Kafka",
        "skill":         "raven:kafka-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         [],
        "keyword_files": ["requirements.txt", "docker-compose.yml", "pyproject.toml"],
        "keywords":      ["kafka"],
    },
    # No .sql glob: a stray migration/SQLite/test-fixture .sql file is NOT an
    # Oracle signal (false positive observed in the Rex project).
    {
        "name":          "Oracle",
        "skill":         "raven:oracle-db-specialist",
        "markers":       ["tnsnames.ora"],
        "dirs":          [],
        "globs":         ["*.pkb", "*.pks"],
        "strong_globs":  True,
        "keyword_files": ["requirements.txt", "pyproject.toml"],
        "keywords":      ["cx_Oracle", "oracledb"],
    },
    # template.yaml only counts when its content is CloudFormation/SAM.
    {
        "name":          "AWS",
        "skill":         "raven:aws-specialist",
        "markers":       ["cdk.json", "serverless.yml", "serverless.yaml", "sam.yaml"],
        "dirs":          [],
        "globs":         [],
        "keyword_files": ["template.yaml", "template.yml"],
        "keywords":      ["AWS::"],
    },
    {
        "name":          "FastAPI",
        "skill":         "raven:fastapi-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         [],
        "keyword_files": ["requirements.txt", "pyproject.toml"],
        "keywords":      ["fastapi"],
    },
]


def _entry_signals(cwd: Path, entry: dict):
    """Count (strong, weak) signal hits for one map entry."""
    strong = weak = 0
    for marker in entry.get("markers", []):
        if (cwd / marker).exists():
            strong += 1
    for d in entry.get("dirs", []):
        if (cwd / d).is_dir():
            weak += 1
    glob_strong = entry.get("strong_globs", False)
    for pattern in entry.get("globs", []):
        try:
            if next(iter(cwd.glob(pattern)), None):
                strong += 1 if glob_strong else 0
                weak += 0 if glob_strong else 1
        except Exception:
            pass
    keywords = entry.get("keywords") or ([entry["keyword"]] if entry.get("keyword") else [])
    if keywords:
        for kf in entry.get("keyword_files", []):
            kf_path = cwd / kf
            if kf_path.exists():
                try:
                    text = kf_path.read_text(errors="ignore").lower()
                    if any(k.lower() in text for k in keywords):
                        strong += 1
                        break
                except Exception:
                    pass
    return strong, weak


def detect_domain(cwd: Path):
    """Returns (skill, name, strength) or (None, None, None).

    strength: "strong" (marker / proprietary extension / dependency keyword, or
    two agreeing weak signals) or "weak" (single generic-dir hit — advisory).
    Strong matches win over earlier weak ones — a loose entry cannot shadow a
    precise later one.
    """
    weak_hit = None
    for entry in DOMAIN_SKILL_MAP:
        strong, weak = _entry_signals(cwd, entry)
        if strong or weak >= 2:
            return entry["skill"], entry["name"], "strong"
        if weak and weak_hit is None:
            weak_hit = (entry["skill"], entry["name"], "weak")
    return weak_hit if weak_hit else (None, None, None)


def is_raven_project(cwd: Path) -> bool:
    """True if this looks like a brownfield Raven project."""
    # Explicit Raven manifest
    if (cwd / ".raven" / "manifest.json").exists():
        return True
    # session-start.py wrote .model.env — means brownfield was detected
    if (cwd / ".model.env").exists():
        return True
    return False


def main():
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    cwd = Path.cwd()

    if not is_raven_project(cwd):
        # Not a Raven project — silent, no output
        sys.exit(0)

    skill, domain_name, strength = detect_domain(cwd)

    if skill and strength == "strong":
        context = (
            f"RAVEN SKILL ENFORCEMENT: This is a {domain_name} project. "
            f"You MUST invoke `{skill}` before any file read, Bash command, or code response. "
            f"Invoking the skill IS the first action — not optional, not skippable."
        )
    elif skill:
        context = (
            f"Raven: weak {domain_name} signal (directory name only) — "
            f"consider `{skill}` only if the task is {domain_name}-related. Not mandatory."
        )
    else:
        context = (
            "RAVEN ACTIVE: This is a brownfield project with Raven guards enabled. "
            "Before any file read, Bash command, or code response: identify the domain "
            "and invoke the matching Raven specialist skill first."
        )

    output = {
        "hookSpecificOutput": {
            "hookEventName":   "UserPromptSubmit",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
