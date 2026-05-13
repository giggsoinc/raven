# Raven-Codex — Test Environment Guide

Step-by-step guide to running Raven-Codex in a test environment with OpenAI Codex.

---

## Prerequisites

| Requirement | Check |
|---|---|
| OpenAI account (Pro/Enterprise/Business) | [platform.openai.com](https://platform.openai.com) |
| Codex access | [chatgpt.com/codex](https://chatgpt.com/codex) |
| Python 3.10+ | `python3 --version` |
| Git | `git --version` |
| OpenAI API key | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) |

---

## Step 1 — Create a Test Project

Create a clean test repo to run Raven against:

```bash
mkdir raven-codex-test
cd raven-codex-test
git init
echo "# Raven Codex Test Project" > README.md
git add . && git commit -m "init test project"
```

---

## Step 2 — Clone Raven-Codex

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/codex/install.sh | bash
```

---

## Step 3 — Run Setup

```bash
cd raven-codex-test
cd YourProject && raven-codex-setup
```

Setup will ask:
- Project name
- Your email (audit trail)
- Stack (Python / Node / Go / other)
- Cloud provider (AWS / GCP / Azure / OCI)
- OpenAI API key (for CVE deep scan)

This creates `.raven/manifest.json` in your test project.

---

## Step 4 — Connect MCP Server to Codex

`raven-codex-setup` does this automatically — it writes to `~/.codex/config.toml`.

Verify it was registered:
```bash
cat ~/.codex/config.toml
# Should contain:
# [mcp_servers.raven]
# command = "python3"
# args    = ["/Users/YOU/.raven-codex/mcp/server.py"]
```

Then verify Raven is live:
```
In Codex: "Run raven_status"
Expected: ✅ manifest loaded, version, mode
```

If `raven_status` returns an error, check [Troubleshooting](#troubleshooting) below.

---

## Step 5 — Connect Your Test Repo to Codex

1. Go to [chatgpt.com/codex](https://chatgpt.com/codex)
2. Click **New Task**
3. Select your `raven-codex-test` repo
4. Codex will clone it into a sandbox

---

## Step 6 — Run Test Scenarios

### Test A — Secret Detection
Ask Codex:
```
Add an OpenAI API key to config.py as a variable called OPENAI_KEY
```
**Expected:** Raven intercepts — "Secret detected. Move to environment variable."

---

### Test B — CVE Library Block
Ask Codex:
```
Add requests==2.6.0 to requirements.txt and install it
```
**Expected:** Raven CVE check fires — requests 2.6.0 has known CVEs, Raven blocks or warns.

---

### Test C — Unknown Library Approval Flow
Ask Codex:
```
Add a library called pytimeparse to requirements.txt
```
**Expected:** Raven flags it — "Unknown library. Approval flow required before adding to manifest."

---

### Test D — PR Gate
Push a branch with a change:
```bash
git checkout -b test-branch
echo "import os" > test.py
git add . && git commit -m "test commit"
git push origin test-branch
```
Open a PR. Raven PR gate runs — check the PR status checks for:
```
✅ Raven cleared  OR  🔴 Raven blocked  OR  ⚠️ Raven did not run
```

---

### Test E — Manifest Check
Ask Codex:
```
Run raven_status
```
**Expected output:**
```
✅ manifest.json loaded
✅ stack declared
✅ secrets file present
Version: 2.8
Mode: active
```

---

### Test F — Audit Log
After running any test above:
```bash
cat .raven/audit/audit.log
```
**Expected:** Encrypted entries for every Raven action taken.

---

## Step 7 — Verify PR Gate in Codex UI

1. Go to your test repo on GitHub
2. Open the PR from Step 6
3. Check **Status Checks** section
4. You should see: `raven / discipline-check`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `raven_status` returns error | Check MCP server path in Codex settings |
| CVE check not firing | Verify `RAVEN_CVE_MODEL` env var is set |
| PR gate not showing | Check GitHub Actions is enabled on test repo |
| Manifest missing | Re-run `raven-codex-setup.sh` |
| Audit log empty | Check write permissions on `.raven/audit/` |

---

## What's Different from Claude Code

| | Claude Code | Codex |
|---|---|---|
| Enforcement point | Pre-commit (before commit) | PR gate (before merge) |
| Secret scan | On file save | On PR open |
| CVE scan | On import detected | On PR open |
| Setup command | `raven-setup` | `raven-codex-setup` |
| Config dir | `.claude/` | `.raven-codex/` |
| MCP connect | `claude mcp add` | Codex Settings → MCP |

---

*Raven-Codex v2.8 — MIT — [github.com/giggsoinc/raven/tree/main/codex](https://github.com/giggsoinc/raven/tree/main/codex)*
