#!/usr/bin/env python3
"""
Raven Work Mode Detector
Scans a directory and classifies the work type from file signatures.
No questions asked — returns JSON for the setup scripts to consume.

Usage: python3 sr-detect-workmode.py [directory]
Output: JSON to stdout
"""

import os
import sys
import json
import platform
from pathlib import Path
from collections import defaultdict


# ─── SIGNAL DEFINITIONS ──────────────────────────────────────────────────────

# Files that unambiguously identify a platform — these OVERRIDE score-based detection
HARD_SIGNAL_FILES = {
    ".forceignore":         "salesforce",
    "sfdx-project.json":    "salesforce",
    "package.xml":          "salesforce",
    "__manifest__.py":      "odoo",
    "dbt_project.yml":      "data",
    "airflow.cfg":          "data",
    "mkdocs.yml":           "docs",
    "docusaurus.config.js": "docs",
    "docusaurus.config.ts": "docs",
    ".readthedocs.yml":     "docs",
    "Chart.yaml":           "infra",
    "helmfile.yaml":        "infra",
    "kustomization.yaml":   "infra",
}

# Directories that unambiguously identify a platform
HARD_SIGNAL_DIRS = {
    "force-app":        "salesforce",
    "odoo_addons":      "odoo",
    ".dbt":             "data",
    "dags":             "data",
    "airflow":          "data",
}

# File extensions scored per-mode — higher score = stronger signal
EXTENSION_SCORES = {
    # Infra
    ".tf":     {"infra": 4},
    ".hcl":    {"infra": 3},
    ".bicep":  {"infra": 3},

    # Code
    ".py":     {"code": 3},
    ".go":     {"code": 3},
    ".ts":     {"code": 3},
    ".tsx":    {"code": 2},
    ".js":     {"code": 2},
    ".jsx":    {"code": 2},
    ".java":   {"code": 3},
    ".kt":     {"code": 3},
    ".rs":     {"code": 3},
    ".cs":     {"code": 3},
    ".rb":     {"code": 2},
    ".swift":  {"code": 2},
    ".php":    {"code": 2},

    # Data
    ".sql":    {"data": 3},
    ".ipynb":  {"data": 4},
    ".parquet":{"data": 2},
    ".csv":    {"data": 1},

    # Docs
    ".md":     {"docs": 1},
    ".rst":    {"docs": 2},
    ".adoc":   {"docs": 2},

    # Infra + neutral
    ".yaml":   {"infra": 1},
    ".yml":    {"infra": 1},
    ".json":   {"infra": 0},   # too generic to score
    ".sh":     {"infra": 1, "code": 1},
    ".dockerfile": {"infra": 2},
}

# Special filenames (not extensions) that add scores
FILENAME_SCORES = {
    "Dockerfile":          {"infra": 3},
    "docker-compose.yml":  {"infra": 3},
    "docker-compose.yaml": {"infra": 3},
    "Makefile":            {"infra": 1, "code": 1},
    "Jenkinsfile":         {"infra": 2},
    "requirements.txt":    {"code": 2},
    "pyproject.toml":      {"code": 2},
    "Pipfile":             {"code": 2},
    "package.json":        {"code": 2},
    "go.mod":              {"code": 3},
    "go.sum":              {"code": 1},
    "pom.xml":             {"code": 3},
    "build.gradle":        {"code": 3},
    "Cargo.toml":          {"code": 3},
    "pubspec.yaml":        {"code": 2},
    ".eslintrc":           {"code": 1},
    ".prettierrc":         {"code": 1},
}

# Human-readable display labels for signals
SIGNAL_LABELS = {
    ".tf":           "Terraform configs",
    ".hcl":          "HCL files",
    ".bicep":        "Bicep templates",
    ".py":           "Python files",
    ".go":           "Go files",
    ".ts":           "TypeScript files",
    ".tsx":          "TypeScript/React files",
    ".js":           "JavaScript files",
    ".java":         "Java files",
    ".kt":           "Kotlin files",
    ".rs":           "Rust files",
    ".cs":           "C# files",
    ".rb":           "Ruby files",
    ".sql":          "SQL files",
    ".ipynb":        "Jupyter notebooks",
    ".md":           "Markdown / docs",
    ".yaml":         "YAML configs",
    ".yml":          "YAML configs",
    "Dockerfile":    "Docker setup",
    "docker-compose.yml":   "Docker Compose",
    "docker-compose.yaml":  "Docker Compose",
    "Chart.yaml":    "Helm charts",
    "helmfile.yaml": "Helm charts",
    "kustomization.yaml": "Kustomize configs",
    "requirements.txt": "Python dependencies",
    "package.json":  "Node.js project",
    "go.mod":        "Go module",
    "dbt_project.yml": "dbt project",
    "airflow.cfg":   "Apache Airflow",
    ".forceignore":  "Salesforce project",
    "sfdx-project.json": "Salesforce DX",
    "__manifest__.py": "Odoo modules",
    "mkdocs.yml":    "MkDocs site",
}

MODE_DESCRIPTIONS = {
    "salesforce":   "Salesforce / SFDC project",
    "odoo":         "Odoo ERP / CRM project",
    "data":         "Data engineering / analytics workspace",
    "docs":         "Documentation workspace",
    "infra":        "Pure infrastructure workspace",
    "code":         "Software development project",
    "mixed":        "Mixed code + infrastructure project",
    "unknown":      "Unknown — could not classify",
}

MODE_RULES = {
    "salesforce": [
        "Enforce bulk patterns on SOQL queries",
        "Block DML inside loops",
        "Require test classes with 75%+ coverage",
        "Detect hardcoded IDs in metadata",
    ],
    "odoo": [
        "Validate module structure and __manifest__.py",
        "Block raw SQL in ORM context",
        "Detect hardcoded DB IDs",
        "Enforce view XML structure",
    ],
    "data": [
        "Enforce SQL formatting and query structure",
        "Require schema documentation",
        "Block PII in pipeline configs",
        "Validate dbt model references",
    ],
    "docs": [
        "Check for broken internal links",
        "Enforce consistent heading structure",
        "Flag missing section headers",
        "Detect orphaned pages",
    ],
    "infra": [
        "Require change comments on all .tf modifications",
        "Block secrets in config files (.yaml, .tf, docker-compose)",
        "Enforce naming conventions (resources, topics, releases)",
        "Flag open 0.0.0.0/0 firewall rules",
    ],
    "code": [
        "Enforce code style and type hints",
        "CVE scan on every new import",
        "Block secrets in source files",
        "Require tests before commit",
    ],
    "mixed": [
        "Code rules on source files (.py, .go, .ts…)",
        "Infra rules on config files (.yaml, .tf…)",
        "Secret detection across all file types",
        "CVE scan on new dependencies",
    ],
}


# ─── PLATFORM DETECTION ──────────────────────────────────────────────────────

def detect_platform() -> str:
    system = platform.system()
    if system == "Darwin":
        return "macOS"
    elif system == "Linux":
        try:
            with open("/proc/version") as f:
                if "microsoft" in f.read().lower():
                    return "Windows (WSL)"
        except OSError:
            pass
        return "Linux"
    elif system == "Windows":
        return "Windows"
    return "Unknown"


# ─── DIRECTORY SCANNER ───────────────────────────────────────────────────────

def scan_directory(root: str = ".", max_depth: int = 3) -> dict:
    """
    Walk directory up to max_depth.
    Returns:
        ext_counts: {".tf": 14, ".py": 3, ...}
        special_files: {".forceignore": "salesforce", ...}
        special_dirs:  {"force-app": "salesforce", ...}
        found_filenames: {filename: label, ...}
    """
    ext_counts = defaultdict(int)
    found_special_files = {}
    found_special_dirs = {}
    found_filenames = {}

    root_path = Path(root).resolve()

    for dirpath, dirnames, filenames in os.walk(root_path):
        try:
            depth = len(Path(dirpath).relative_to(root_path).parts)
        except ValueError:
            continue

        if depth > max_depth:
            dirnames.clear()
            continue

        # Skip .git and other noise — but keep .github, .dbt, .raven
        dirnames[:] = [
            d for d in dirnames
            if d not in {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache"}
            and (not d.startswith(".") or d in {".github", ".dbt", ".raven", ".dbt-profiles"})
        ]

        # Check directory names
        for d in dirnames:
            if d in HARD_SIGNAL_DIRS and d not in found_special_dirs:
                found_special_dirs[d] = HARD_SIGNAL_DIRS[d]

        # Check files
        for fname in filenames:
            suffix = Path(fname).suffix.lower()
            if suffix:
                ext_counts[suffix] += 1

            # Hard signal filenames
            if fname in HARD_SIGNAL_FILES and fname not in found_special_files:
                found_special_files[fname] = HARD_SIGNAL_FILES[fname]

            # Scored filenames
            if fname in FILENAME_SCORES and fname not in found_filenames:
                found_filenames[fname] = fname

    return {
        "ext_counts": dict(ext_counts),
        "special_files": found_special_files,
        "special_dirs": found_special_dirs,
        "found_filenames": found_filenames,
    }


# ─── MODE CLASSIFIER ─────────────────────────────────────────────────────────

def classify(scan_result: dict) -> dict:
    """
    Classify work mode from scan results.
    Returns: {mode, primary, secondary, signals, scores, confidence}
    """
    ext_counts = scan_result["ext_counts"]
    special_files = scan_result["special_files"]
    special_dirs = scan_result["special_dirs"]
    found_filenames = scan_result["found_filenames"]

    signals = {}   # what to display to user
    scores = defaultdict(float)

    # ── HARD SIGNALS (override everything) ──
    hard_mode = None
    for fname, mode in special_files.items():
        hard_mode = mode
        label = SIGNAL_LABELS.get(fname, fname)
        signals[label] = "✓"
        break   # First hard signal wins

    if not hard_mode:
        for dname, mode in special_dirs.items():
            hard_mode = mode
            signals[dname + "/ directory"] = "✓"
            break

    if hard_mode:
        return {
            "mode": hard_mode,
            "primary": hard_mode,
            "secondary": None,
            "signals": signals,
            "scores": {hard_mode: 100},
            "confidence": "high",
        }

    # ── SCORE-BASED DETECTION ──

    # Score extensions
    for ext, count in ext_counts.items():
        if ext in EXTENSION_SCORES:
            for mode, weight in EXTENSION_SCORES[ext].items():
                capped = min(count * weight, weight * 20)  # cap at 20x weight
                scores[mode] += capped
            if count > 0 and ext in SIGNAL_LABELS:
                signals[SIGNAL_LABELS[ext]] = f"✓  ({count} files)"

    # Score special filenames
    for fname in found_filenames:
        if fname in FILENAME_SCORES:
            for mode, weight in FILENAME_SCORES[fname].items():
                scores[mode] += weight
        if fname in SIGNAL_LABELS:
            signals[SIGNAL_LABELS[fname]] = "✓"

    # ── CHECK FOR NO SIGNALS ──
    if not scores or max(scores.values(), default=0) < 3:
        return {
            "mode": "unknown",
            "primary": "unknown",
            "secondary": None,
            "signals": {},
            "scores": dict(scores),
            "confidence": "none",
        }

    # ── RANK MODES ──
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_mode, best_score = ranked[0]

    # ── AMBIGUITY CHECK ──
    if len(ranked) > 1:
        second_mode, second_score = ranked[1]
        if second_score > 0 and best_score > 5:
            ratio = second_score / best_score
            if ratio > 0.45:  # Within 45% — ambiguous
                return {
                    "mode": "ambiguous",
                    "primary": best_mode,
                    "secondary": second_mode,
                    "signals": signals,
                    "scores": dict(scores),
                    "confidence": "low",
                }

    return {
        "mode": best_mode,
        "primary": best_mode,
        "secondary": None,
        "signals": signals,
        "scores": dict(scores),
        "confidence": "high" if best_score > 15 else "medium",
    }


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    scan_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    # Check manifest exists
    manifest_path = os.path.join(scan_dir, ".raven", "manifest.json")
    manifest_exists = os.path.exists(manifest_path)

    # Platform
    plat = detect_platform()

    # Git
    has_git = os.path.exists(os.path.join(scan_dir, ".git"))

    # Scan
    scan_result = scan_directory(scan_dir)

    # Classify
    classification = classify(scan_result)

    # Has source code?
    code_exts = {".py", ".go", ".ts", ".tsx", ".js", ".jsx", ".java", ".kt", ".rs", ".cs", ".rb", ".swift", ".php"}
    has_source_code = any(scan_result["ext_counts"].get(e, 0) > 0 for e in code_exts)

    output = {
        "platform": plat,
        "has_git": has_git,
        "manifest_exists": manifest_exists,
        "has_source_code": has_source_code,
        "mode": classification["mode"],
        "primary": classification["primary"],
        "secondary": classification["secondary"],
        "signals": classification["signals"],
        "confidence": classification["confidence"],
        "mode_description": MODE_DESCRIPTIONS.get(classification["primary"], ""),
        "mode_rules": MODE_RULES.get(classification.get("mode") if classification["mode"] != "ambiguous" else classification["primary"], []),
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
