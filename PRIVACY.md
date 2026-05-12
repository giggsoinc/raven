# Privacy Policy — Raven

**Last updated: May 12, 2026**
**Published by: Giggso Inc**

---

## What Raven Collects

Raven is a local developer tool. It does not collect, transmit, or store personal data on any Giggso-operated server.

Data that stays on your machine or your own infrastructure:

| Data | Where it goes |
|---|---|
| Audit logs (tool calls, violations, approvals) | Your S3 / GCS / Azure / OCI bucket — configured by you |
| Manifest (project config, stack, libraries) | Your Git repo |
| Secrets file (API keys, email addresses) | Local only — never committed |
| Session state (claude-mem backups) | Local only |

---

## Third-Party Services

Raven optionally calls two external services:

**OpenAI API** — used for CVE deep-scan (`cve-check.py`). Only library names and version numbers are sent. No source code, no personal data. Requires you to provide your own OpenAI API key. Governed by [OpenAI's Privacy Policy](https://openai.com/privacy).

**PyPI Safety DB** — used for CVE tier-1 checks. Sends library names and versions only. No authentication required.

---

## What Raven Does Not Do

- Does not sell or share any data
- Does not phone home to Giggso servers
- Does not collect telemetry or usage metrics
- Does not transmit source code to any external service
- Does not store credentials beyond your local machine

---

## Your Audit Logs

If you configure Raven to write audit logs to a cloud bucket (S3, GCS, Azure Blob, OCI), those logs are stored in **your** account under **your** control. Giggso has no access to them.

---

## Contact

Questions about this policy:
**giggso.ravi@gmail.com**
**https://github.com/giggsoinc/raven**
