<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# Raven-Codex

> OpenAI Codex implementation of the Raven AI coding discipline engine.
> Part of the [Raven platform](https://github.com/giggsoinc/raven-core). MIT License.
> Built by [Giggso Inc](https://github.com/giggsoinc).

*Guardrails before you ship.*

---

## What It Does

Raven-Codex brings enterprise coding discipline to OpenAI Codex:
- Hard-blocks secrets before they reach your repo
- CVE scans every library before it lands in your codebase
- PR gates — nothing merges without passing Raven
- Encrypted audit logs → your S3/GCS/Azure/OCI bucket
- Manifest-driven stack enforcement

---

## Platform

| | Claude Code | OpenAI Codex |
|---|---|---|
| **Enforcement** | Pre-commit hook | PR gate + pre-task hook |
| **CVE scan** | On import detection | On PR open |
| **Secret scan** | On file save | On PR open |
| **Audit log** | Every tool call | Every PR event |
| **Engine** | [raven-core](https://github.com/giggsoinc/raven-core) | [raven-core](https://github.com/giggsoinc/raven-core) |

---

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven/main/codex/install.sh | bash
cd YourProject && raven-codex-setup
```

---

## Full Test Environment Guide

See [CODEX-TEST-GUIDE.md](CODEX-TEST-GUIDE.md) for step-by-step setup and test scenarios.

---

## Also Install

For production protection (hard-blocks on destructive operations):
```bash
# Coming soon
giggsoinc/raven-guard-codex
```

---

## License

MIT — [Giggso Inc](https://github.com/giggsoinc)
