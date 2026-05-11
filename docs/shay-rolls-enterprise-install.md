# Shay-Rolls Claude — Install Guide
## Solo Developer · Small Team · Enterprise

---

## Solo Developer — One command

```bash
bash /path/to/shay-rolls-claude/shay-rolls-setup.sh
```

Answer 7 questions. Done. Takes 2 minutes.

---

## Claude Code Plugin — Any Developer

Install Shay-Rolls as a Claude Code MCP plugin. Available globally across all projects.

```bash
# Install plugin (run once, ever)
claude mcp add shay-rolls -- python3 ~/.shay-rolls-claude/mcp/server.py

# Then init any project
cd YourProject
shay-rolls-setup
```

**What the plugin exposes in Claude Code:**
- `shay_status` — check manifest, version, mode
- `shay_cve_check` — CVE scan any library on demand
- `shay_sync_libs` — sync requirements.txt → manifest
- `shay_debug` — full health check
- `shay_violation` — emit violation to audit log

---

## Small Team (2–10 developers)

**Step 1 — One developer sets up the framework repo:**
```bash
git clone https://github.com/giggsoinc/shay-rolls-claude ~/.shay-rolls-claude
git clone https://github.com/giggsoinc/shay-rolls-claude-guard ~/.shay-rolls-claude-guard
```

**Step 2 — Create a shared org manifest:**
```bash
cp ~/.shay-rolls-claude/manifest/manifest.org.example.json \
   your-org-repo/shay-rolls/manifest.org.json
```

Edit `manifest.org.json` — set shared S3 bucket, approved libraries, forbidden frameworks.

**Step 3 — Each developer installs:**
```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/shay-rolls-claude/main/install.sh | bash
```

**Step 4 — Each developer inits their project:**
```bash
cd MyProject
shay-rolls-setup
```

---

## Enterprise (10+ developers)

### Admin setup (one-time)

**Step 1 — Create org manifest:**

```json
{
  "org": "YourOrg",
  "standards": "shay-rolls-v2.8",
  "audit": {
    "provider":   "aws",
    "s3_bucket":  "your-org-audit-bucket",
    "s3_region":  "us-east-1",
    "kms_key_id": "arn:aws:kms:..."
  },
  "approved_skills": {
    "org_stdlib": [
      "polars", "fastapi", "pydantic", "httpx", "asyncpg",
      "boto3", "sqlalchemy", "pytest", "ruff", "mypy"
    ]
  },
  "project_rules": {
    "commit_convention": "conventional",
    "require_approval_gates": true
  }
}
```

Save as `manifest.org.json` in your internal package registry or S3 bucket.

**Step 2 — Set environment variable on every dev machine (via MDM/Intune):**

```bash
SHAY_ROLLS_ORG_MANIFEST=s3://your-bucket/manifest.org.json
```

Or push via your MDM tool (Jamf, Intune, Puppet, Ansible).

**Step 3 — Push install to all machines:**

Via Ansible:
```yaml
- name: Install Shay-Rolls Claude
  shell: |
    curl -fsSL https://raw.githubusercontent.com/giggsoinc/shay-rolls-claude/main/install.sh | bash
  become: false
```

Via Jamf (macOS):
```bash
# Jamf policy script
curl -fsSL https://raw.githubusercontent.com/giggsoinc/shay-rolls-claude/main/install.sh | bash
```

Via Docker base image:
```dockerfile
FROM ubuntu:24.04
RUN curl -fsSL https://raw.githubusercontent.com/giggsoinc/shay-rolls-claude/main/install.sh | bash
```

### Developer onboarding (each new developer)

```bash
# Clone their project
git clone https://github.com/yourorg/myproject
cd myproject

# Init Shay-Rolls (reads org manifest from env var automatically)
shay-rolls-setup

# Install Guard
shay-rolls-guard-setup

# Open Claude Code
claude .
```

Total time: **under 3 minutes.**

### Zero-click (Claude Code Enterprise)

If your org uses Claude Code Enterprise:

1. Admin uploads `shay-rolls-claude` to the org plugin registry
2. Every developer gets it automatically on next Claude Code update
3. No install, no curl, no setup
4. `shay-rolls-setup` available as a command everywhere

---

## Audit — Multi-Project, One Bucket

Every project writes to the same S3 bucket, isolated by project name:

```
s3://your-org-audit/
  shay-rolls/
    lockey/rv_at_giggso/rvgiggso/2026-05-10.log.gz.enc
    patronai/rv_at_giggso/rvgiggso/2026-05-10.log.gz.enc
    antiGravity/rv_at_giggso/rvgiggso/2026-05-10.log.gz.enc
```

PatronAI reads from this bucket for observability across all projects.

---

## Guard — Enterprise

Install Guard in every project after Core:

```bash
cd MyProject
shay-rolls-guard-setup
```

Guard adds 6 agents that hard-block:
- Force push to any branch
- TRUNCATE / DROP / DELETE without WHERE
- Terraform state modification
- Firewall rules opening 0.0.0.0/0
- SSH (22) / RDP (3389) exposed to public

PagerDuty P1 fires in 15 minutes. Weekly digest to Prism7.

---

## Works alongside

```
Superpowers → dev methodology (TDD, planning, review)
GSD         → context management (long sessions)
Shay-Rolls  → governance + security layer

All three stack. No conflicts.
```

---

## GitHub
- Core: github.com/giggsoinc/shay-rolls-claude (MIT)
- Guard: github.com/giggsoinc/shay-rolls-claude-guard (MIT)

Built by Giggso · giggso.com
