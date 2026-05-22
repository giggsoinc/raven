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
DOMAIN_SKILL_MAP = [
    {
        "name":          "Salesforce",
        "skill":         "raven:salesforce-specialist",
        "markers":       ["sfdx-project.json", ".forceignore"],
        "dirs":          ["force-app"],
        "globs":         [],
        "keyword_files": [],
        "keyword":       "",
    },
    {
        "name":          "Odoo",
        "skill":         "raven:odoo-specialist",
        "markers":       ["odoo.conf", ".odoo_upgrade.json"],
        "dirs":          [],
        "globs":         ["**/__manifest__.py"],
        "keyword_files": [],
        "keyword":       "",
    },
    {
        "name":          "Terraform",
        "skill":         "raven:terraform-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         ["*.tf"],
        "keyword_files": [],
        "keyword":       "",
    },
    {
        "name":          "Kubernetes",
        "skill":         "raven:k8s-specialist",
        "markers":       [],
        "dirs":          ["k8s", "kubernetes", "helm", "charts"],
        "globs":         [],
        "keyword_files": [],
        "keyword":       "",
    },
    {
        "name":          "Kafka",
        "skill":         "raven:kafka-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         [],
        "keyword_files": ["requirements.txt", "docker-compose.yml", "pyproject.toml"],
        "keyword":       "kafka",
    },
    {
        "name":          "Oracle",
        "skill":         "raven:oracle-db-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         ["*.pkb", "*.pks"],
        "keyword_files": ["requirements.txt"],
        "keyword":       "cx_Oracle",
    },
    {
        "name":          "AWS",
        "skill":         "raven:aws-specialist",
        "markers":       ["cdk.json", "serverless.yml", "serverless.yaml", "sam.yaml"],
        "dirs":          [],
        "globs":         [],
        "keyword_files": [],
        "keyword":       "",
    },
    {
        "name":          "FastAPI",
        "skill":         "raven:fastapi-specialist",
        "markers":       [],
        "dirs":          [],
        "globs":         [],
        "keyword_files": ["requirements.txt", "pyproject.toml"],
        "keyword":       "fastapi",
    },
]


def detect_domain(cwd: Path):
    """Returns (skill, name) or (None, None). Fast — no heavy recursion."""
    for entry in DOMAIN_SKILL_MAP:
        for marker in entry["markers"]:
            if (cwd / marker).exists():
                return entry["skill"], entry["name"]
        for d in entry["dirs"]:
            if (cwd / d).is_dir():
                return entry["skill"], entry["name"]
        # Globs — use non-recursive first, then single-level recursive
        for pattern in entry["globs"]:
            try:
                found = next(iter(cwd.glob(pattern)), None)
                if found:
                    return entry["skill"], entry["name"]
            except Exception:
                pass
        keyword = entry["keyword"]
        if keyword:
            for kf in entry["keyword_files"]:
                kf_path = cwd / kf
                if kf_path.exists():
                    try:
                        if keyword.lower() in kf_path.read_text(errors="ignore").lower():
                            return entry["skill"], entry["name"]
                    except Exception:
                        pass
    return None, None


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

    skill, domain_name = detect_domain(cwd)

    if skill:
        context = (
            f"RAVEN SKILL ENFORCEMENT: This is a {domain_name} project. "
            f"You MUST invoke `{skill}` before any file read, Bash command, or code response. "
            f"Invoking the skill IS the first action — not optional, not skippable."
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
