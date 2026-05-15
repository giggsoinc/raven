#!/usr/bin/env python3
"""
Raven — PR Gate v1.0
Orchestrates CVE scan + secret detection + manifest validation for CI.
Called by raven-action on every PR.

Exit codes:
  0 = all checks passed
  1 = hard block (secret or critical CVE)
  2 = manifest missing or invalid (did not run)
"""

import json, os, subprocess, sys
from pathlib import Path

MANIFEST_PATH = os.environ.get("RAVEN_MANIFEST_PATH", ".raven/manifest.json")
SCRIPTS_DIR   = Path(__file__).parent

results = {
    "manifest":    "skipped",
    "secrets":     "skipped",
    "cve":         "skipped",
    "audit":       "skipped",
}

def run(script, extra_args=[]):
    path = SCRIPTS_DIR / script
    if not path.exists():
        return 2, f"{script} not found"
    r = subprocess.run(
        ["python3", str(path)] + extra_args,
        capture_output=True, text=True
    )
    return r.returncode, r.stdout + r.stderr

def banner(icon, label, detail=""):
    print(f"{icon} raven/{label}{(' — ' + detail) if detail else ''}")

# ── 1. Manifest check ─────────────────────────────────────────────────────────
if not Path(MANIFEST_PATH).exists():
    banner("⚠️ ", "discipline-check", "did not run — manifest missing")
    print(f"   Run raven-setup or raven-codex-setup in your project to create {MANIFEST_PATH}")
    sys.exit(2)

try:
    manifest = json.loads(Path(MANIFEST_PATH).read_text())
    missing = [k for k in ("project", "stack", "owner") if k not in manifest]
    if missing:
        banner("⚠️ ", "discipline-check", f"did not run — manifest missing fields: {missing}")
        sys.exit(2)
    results["manifest"] = "passed"
    print(f"✅ manifest.json valid — project: {manifest.get('project')} stack: {manifest.get('stack')}")
except Exception as e:
    banner("⚠️ ", "discipline-check", f"did not run — manifest invalid: {e}")
    sys.exit(2)

# ── 2. Secret scan ────────────────────────────────────────────────────────────
code, out = run("secret-scan.py", ["--pr"])
print(out.strip())
if code == 0:
    results["secrets"] = "passed"
else:
    results["secrets"] = "blocked"
    banner("🔴", "discipline-check", "blocked — secret detected in changed files")
    sys.exit(1)

# ── 3. CVE scan ───────────────────────────────────────────────────────────────
code, out = run("cve-check.py", ["--pr"])
print(out.strip())
if code == 0:
    results["cve"] = "passed"
else:
    results["cve"] = "blocked"
    banner("🔴", "discipline-check", "blocked — CVE found in changed dependencies")
    sys.exit(1)

# ── 4. Audit log ──────────────────────────────────────────────────────────────
pr_num = os.environ.get("GITHUB_PR_NUMBER", "unknown")
actor  = os.environ.get("GITHUB_ACTOR", "unknown")
run("audit-log.py", [
    "--event",  "pr-gate",
    "--pr",     pr_num,
    "--actor",  actor,
    "--result", "passed"
])
results["audit"] = "written"

# ── 5. Pass ───────────────────────────────────────────────────────────────────
banner("✅", "discipline-check", "passed — CVE clean · no secrets · manifest valid")
sys.exit(0)
