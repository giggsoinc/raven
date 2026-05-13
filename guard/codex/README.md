<p align="center">
  <img src="./assets/raven-banner.png" alt="Raven — Guardrails before you ship." width="800"/>
</p>

# Raven-Guard-Codex

> OpenAI Codex implementation of the Raven production protection layer.
> Part of the [Raven platform](https://github.com/giggsoinc/raven-core). MIT License.
> Built by [Giggso Inc](https://github.com/giggsoinc).

*Guardrails before you ship.*

---

## What It Does

Raven-Guard-Codex brings production protection to OpenAI Codex:

### Hard Blocks — No Exceptions
```
1. Force push to any branch
2. TRUNCATE TABLE
3. DROP TABLE / DROP SCHEMA
4. Terraform state file modified
5. 0.0.0.0/0 firewall rule
6. RDP (3389) / SSH (22) opened publicly
7. Kubernetes namespace deleted
8. Secrets file committed
9. Repo config wiped
```

### Approval Flows
```
- Mass deletion >100 rows
- S3 bucket deletion
- VM termination
- Network rule change
- Index deletion
```

### Incident SLAs
| Level | SLA |
|---|---|
| P1 Critical | 15 min escalation |
| P2 High | 1 hour |
| P3 Medium | 24 hours |

---

## Requires

Install first:
```bash
giggsoinc/raven-codex
```

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/giggsoinc/raven-guard-codex/main/install.sh | bash
cd YourProject && raven-guard-codex-setup
```

---

## License

MIT — [Giggso Inc](https://github.com/giggsoinc)
