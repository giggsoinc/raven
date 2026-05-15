#!/usr/bin/env python3
# Raven — Secret Scanner v2.1
# Modes:
#   pre-commit (default) — scans staged files via git diff --cached
#   --pr                 — scans PR diff between base and head (CI mode)
#   --file <path>        — scans a single file directly
# Exit 1 = hard block.

import sys, os, re, subprocess, argparse

parser = argparse.ArgumentParser(description="Raven Secret Scanner")
parser.add_argument("--pr",                action="store_true", help="PR mode — scan diff vs base branch")
parser.add_argument("--changed-files-only",action="store_true", help="Only scan files changed in PR")
parser.add_argument("--file",              default=None,        help="Scan a single file")
parser.add_argument("--base-ref",          default=None,        help="Base branch ref for PR diff")
args = parser.parse_args()

PR_MODE = args.pr or args.changed_files_only

# ── Secret patterns ────────────────────────────────────────────────────────────
PATTERNS = [
    (r'AKIA[0-9A-Z]{16}',                                                    "AWS Access Key"),
    (r'(?i)aws.{0,20}secret.{0,20}["\'][A-Za-z0-9+/]{40}["\']',             "AWS Secret Key"),
    (r'sk-[A-Za-z0-9]{20,}',                                                 "OpenAI API Key"),
    (r'(?i)(api[_-]?key|api[_-]?secret)\s*=\s*["\'][A-Za-z0-9+/._-]{16,}',  "API Key"),
    (r'(?i)password\s*=\s*["\'][^"\']{8,}["\']',                             "Hardcoded Password"),
    (r'-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----',                     "Private Key"),
    (r'(?i)bearer\s+[A-Za-z0-9\-._~+/]{20,}',                               "Bearer Token"),
    (r'(?i)(secret_key|private_key)\s*=\s*["\'][^"\']{8,}["\']',            "Secret Key"),
    (r'AIza[0-9A-Za-z\-_]{35}',                                              "Google API Key"),
    (r'ghp_[A-Za-z0-9]{36}',                                                 "GitHub Personal Token"),
    (r'xoxb-[0-9]{11}-[0-9]{11}-[A-Za-z0-9]{24}',                          "Slack Bot Token"),
]

# ── Critical .gitignore entries ────────────────────────────────────────────────
REQUIRED_GITIGNORE = [
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "manifest.secrets.json",
    ".raven/manifest.secrets.json",
]

violations = []
warnings   = []

def staged_files():
    if PR_MODE:
        base = args.base_ref or os.environ.get("GITHUB_BASE_REF", "main")
        try:
            out = subprocess.check_output(
                ["git", "diff", "--name-only", "--diff-filter=ACM", f"origin/{base}...HEAD"]
            ).decode().split()
            return out
        except:
            return []
    if args.file:
        return [args.file]
    out = subprocess.check_output(
        ["git","diff","--cached","--name-only","--diff-filter=ACM"]
    ).decode().split()
    return out

def file_content(path):
    if args.file:
        try:
            return open(path).read()
        except:
            return ""
    if PR_MODE:
        try:
            return open(path).read()
        except:
            return ""
    try:
        return subprocess.check_output(["git","show",f":{path}"]).decode(errors="ignore")
    except:
        return ""

# ── Check 1: .gitignore exists ─────────────────────────────────────────────────
if not os.path.exists(".gitignore"):
    violations.append("❌ .gitignore missing at project root — create one immediately")
    violations.append("   Run: curl -fsSL https://www.gitignore.io/api/python,node,macos > .gitignore")
else:
    gitignore_content = open(".gitignore").read()

    # ── Check 2: .gitignore covers critical entries ────────────────────────────
    for entry in REQUIRED_GITIGNORE:
        # Check if entry or equivalent is covered
        base = entry.replace("*","").replace(".","").strip("/")
        if entry not in gitignore_content and base not in gitignore_content:
            warnings.append(f"⚠️  .gitignore missing: {entry}")

# ── Check 3: .env file exists but not gitignored ──────────────────────────────
for env_file in [".env", ".env.local", ".env.production", ".env.staging"]:
    if os.path.exists(env_file):
        gitignore_ok = os.path.exists(".gitignore") and (
            env_file in open(".gitignore").read() or
            ".env" in open(".gitignore").read()
        )
        if not gitignore_ok:
            violations.append(f"❌ {env_file} exists but is NOT in .gitignore — exposure risk")

# ── Check 4: manifest.secrets.json not staged ─────────────────────────────────
files = staged_files()
if ".raven/manifest.secrets.json" in files or "manifest.secrets.json" in files:
    violations.append("❌ manifest.secrets.json staged — NEVER commit this file")
    violations.append("   Run: git reset HEAD .raven/manifest.secrets.json")

# ── Check 5: Secret patterns in staged files ──────────────────────────────────
for path in files:
    content = file_content(path)
    if not content:
        continue
    for pattern, label in PATTERNS:
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line) and not line.strip().startswith("#"):
                violations.append(f"❌ {label} detected: {path}:{i}")

# ── Check 6: .pem / .key files staged ─────────────────────────────────────────
for path in files:
    if any(path.endswith(ext) for ext in [".pem",".key",".p12",".pfx",".cer"]):
        violations.append(f"❌ Certificate/key file staged: {path} — never commit keys")

# ── Output ─────────────────────────────────────────────────────────────────────
if warnings:
    print("\n⚠️  Raven Secret Scan — Warnings:")
    for w in warnings:
        print(f"  {w}")

if violations:
    print("\n❌ Raven Secret Scan — VIOLATIONS (commit blocked):")
    for v in violations:
        print(f"  {v}")
    print()
    sys.exit(1)

if not warnings:
    print("✅ Secret scan passed")

sys.exit(0)
