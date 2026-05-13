# CLAUDE.md — Raven Guard

This project operates under **Raven Guard v2.8** protection.
Read this before any action.

---

## Guard Agent Priority

```
guard-incident-manager   ← Coordinates all alerts
guard-git-watch          ← Git layer protection
guard-db-watch           ← Database protection
guard-infra-watch        ← Infrastructure protection
guard-firewall-watch     ← Network protection
guard-observability-watch ← Anomaly detection
```

## Hard Block Rules (no exceptions, no override)

```
1. Force push to any branch → HARD BLOCK
2. TRUNCATE TABLE → HARD BLOCK
3. DROP TABLE / DROP SCHEMA → HARD BLOCK
4. Terraform state file touched → HARD BLOCK
5. 0.0.0.0/0 firewall rule → HARD BLOCK
6. RDP port (3389) opened → HARD BLOCK
7. SSH (22) to public range → HARD BLOCK
8. Kubernetes namespace deleted → HARD BLOCK
9. manifest.secrets.json committed → HARD BLOCK
10. Repo config wiped → HARD BLOCK
```

## Approval Flow Rules

```
File deletion + [GUARD:ALLOW-DELETE] flag → approval flow
Mass deletion >100 rows → approval flow
S3 bucket deletion → approval flow
VM termination → approval flow
Network rule change → approval flow
Index deletion → approval flow
```

## Incident SLA

```
P1 Critical → 15 minutes → escalation contact SMS
P2 High     → 1 hour    → Prism7 + team lead email
P3 Medium   → 24 hours  → Prism7 daily digest
```

## Escalation Ladder

```
Strike 1 → warn
Strike 2 → Prism7 flagged
Strike 3 → escalation contact direct
SLA breach → next level up
```

---

*Raven Guard v2.8 — github.com/giggsoinc/raven-guard*
