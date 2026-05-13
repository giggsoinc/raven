# raven_audit

View the encrypted audit log for this project — every Raven action recorded.

## Usage

```
Run raven_audit
Run raven_audit --last 20
Run raven_audit --event cve-block
```

## What is logged

Every Raven action writes a timestamped, encrypted entry:
- CVE scan results (pass/block/warn)
- Secret detections (location only, never value)
- PR gate decisions
- Manifest validation
- Approval flow events

## Output

```
[2026-05-12T14:23:01Z] cve-check     BLOCKED  requests==2.6.0 CVE-9.8   actor:codex
[2026-05-12T14:24:10Z] secret-scan   CLEAN    config.py                 actor:codex
[2026-05-12T14:25:03Z] pr-gate       PASSED   PR#42                     actor:codex
```

Audit log is stored at `.raven/audit/audit.log` and encrypted with `RAVEN_AUDIT_KEY`.
