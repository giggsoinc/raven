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
    violations.append(
        "No .gitignore yet — without one, it's easy to commit secrets or junk by accident.\n"
        "     What to do: create a starter with —\n"
        "     curl -fsSL https://www.gitignore.io/api/python,node,macos > .gitignore"
    )
else:
    gitignore_content = open(".gitignore").read()

    # ── Check 2: .gitignore covers critical entries ────────────────────────────
    for entry in REQUIRED_GITIGNORE:
        # Check if entry or equivalent is covered
        base = entry.replace("*","").replace(".","").strip("/")
        if entry not in gitignore_content and base not in gitignore_content:
            warnings.append(f".gitignore doesn't cover '{entry}' yet — consider adding it")

# ── Check 3: .env file exists but not gitignored ──────────────────────────────
for env_file in [".env", ".env.local", ".env.production", ".env.staging"]:
    if os.path.exists(env_file):
        gitignore_ok = os.path.exists(".gitignore") and (
            env_file in open(".gitignore").read() or
            ".env" in open(".gitignore").read()
        )
        if not gitignore_ok:
            violations.append(
                f"{env_file} exists but isn't in .gitignore — it could get committed by accident.\n"
                f"     Why this matters: .env files usually hold keys and passwords.\n"
                f"     What to do:  echo '{env_file}' >> .gitignore"
            )

# ── Check 4: manifest.secrets.json not staged ─────────────────────────────────
files = staged_files()
if ".raven/manifest.secrets.json" in files or "manifest.secrets.json" in files:
    violations.append(
        "manifest.secrets.json is staged — this file holds your SMTP/Slack credentials "
        "and must never be committed.\n"
        "     What to do:  git reset HEAD .raven/manifest.secrets.json"
    )

# ── Check 5: Secret patterns in staged files ──────────────────────────────────
for path in files:
    content = file_content(path)
    if not content:
        continue
    for pattern, label in PATTERNS:
        for i, line in enumerate(content.splitlines(), 1):
            if re.search(pattern, line) and not line.strip().startswith("#"):
                violations.append(
                    f"Looks like a {label} on line {i} of {path}.\n"
                    f"     Why this matters: committed secrets get scraped from git history within minutes — "
                    f"rotating a leaked key is far more painful than fixing this now.\n"
                    f"     What to do: move it to an environment variable or .env file (which is gitignored), "
                    f"then unstage this file with:  git reset HEAD {path}"
                )

# ── Check 6: .pem / .key files staged ─────────────────────────────────────────
for path in files:
    if any(path.endswith(ext) for ext in [".pem",".key",".p12",".pfx",".cer"]):
        violations.append(
            f"{path} looks like a certificate or private key — these should never be committed.\n"
            f"     What to do: store it outside the repo (or in a secrets manager), then:  "
            f"git reset HEAD {path}"
        )

# ── Output ─────────────────────────────────────────────────────────────────────
if warnings:
    print("\n💡 Raven noticed a few things worth tidying up (not blocking):")
    for w in warnings:
        print(f"  • {w}")

if violations:
    print("\n🛡️  Raven stopped this commit to protect you — here's what to fix:\n")
    for v in violations:
        print(f"  • {v}\n")
    print("  Once you've fixed the above, just commit again. Nothing else is needed.")
    print("  (If a match is a false positive, say so and we'll tune the pattern.)\n")
    sys.exit(1)

if not warnings:
    print("✅ Secret scan passed — no secrets in your staged files. Safe to commit.")

sys.exit(0)
