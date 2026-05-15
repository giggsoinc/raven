---
name: log-management-specialist
description: Use when designing or reviewing logging pipelines, structured logging, log aggregation (ELK, Loki, CloudWatch), retention policies, PII scrubbing, alerting on log patterns, or distributed tracing integration. Expert-level guidance on observability discipline.
allowed-tools: Read, Bash, Grep
---

# Log Management Specialist

Domain: Observability · Structured Logging · Log Aggregation · Distributed Tracing
Expert model: Charity Majors (Honeycomb) — production observability, high-cardinality telemetry, SRE discipline

---

## Pre-flight Check

Before advising, confirm:

1. **Stack declared?** → check `.raven/manifest.json` for `stack`
2. **Current logging approach?** → ask if not obvious from code
3. **Log destination?** → CloudWatch / Elasticsearch / Loki / Splunk / stdout
4. **Retention requirements?** → compliance, cost, debug window
5. **PII risk?** → user data, emails, tokens in log fields

---

## Core Principles

```
1. Structured logs ONLY — JSON lines, not free-text strings
2. One log entry per request/event — no chatty loops
3. Correlation IDs on every log — trace_id, request_id, session_id
4. Never log secrets — API keys, passwords, tokens → [REDACTED]
5. Never log raw PII — emails, phone numbers → hash or mask
6. Log at the right level — DEBUG off in prod, WARN/ERROR always on
7. Fail-open — log pipeline failure must not crash the application
```

---

## Log Levels — When to Use Each

| Level | Use case | Prod enabled? |
|---|---|---|
| `DEBUG` | Internal state, variable dumps, loop tracing | ❌ Never |
| `INFO` | Business events, request start/end, key decisions | ✅ Yes |
| `WARNING` | Degraded state, retries, expected failures | ✅ Yes |
| `ERROR` | Unexpected failure, caught exception with stack | ✅ Yes |
| `CRITICAL` | System can't continue, data loss risk | ✅ Yes — page immediately |

**Rule:** If you're logging in a loop → wrong level or wrong design.

---

## Structured Log Format

Every log line must be a JSON object:

```json
{
  "timestamp": "2026-05-14T12:00:00.000Z",
  "level": "INFO",
  "service": "auth-service",
  "trace_id": "abc123",
  "request_id": "req-456",
  "user_id": "u-789",
  "event": "login.success",
  "duration_ms": 42,
  "message": "User authenticated via OAuth"
}
```

**Never this:**
```python
logger.info(f"User {email} logged in at {time}")  # ❌ free-text, PII in string
```

**Always this:**
```python
logger.info("login.success", extra={
    "user_id": user.id,          # ✅ ID, not email
    "duration_ms": elapsed_ms,
    "provider": "oauth",
})
```

---

## Python — Canonical Setup

```python
import logging
import json
import sys
from pythonjsonlogger import jsonlogger

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

Library: `python-json-logger` (approved in Raven manifest before use)

---

## Correlation IDs — Mandatory Pattern

Every request must carry a trace ID through all log lines:

```python
import uuid
from contextvars import ContextVar

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")

def set_trace_id(tid: str | None = None) -> str:
    tid = tid or str(uuid.uuid4())
    _trace_id.set(tid)
    return tid

def get_trace_id() -> str:
    return _trace_id.get()
```

FastAPI middleware example:
```python
@app.middleware("http")
async def trace_middleware(request: Request, call_next):
    tid = request.headers.get("X-Trace-Id") or str(uuid.uuid4())
    set_trace_id(tid)
    response = await call_next(request)
    response.headers["X-Trace-Id"] = tid
    return response
```

---

## PII Scrubbing — Hard Rules

Fields that must NEVER appear in logs as raw values:

```python
PII_FIELDS = {
    "password", "token", "secret", "api_key", "credit_card",
    "ssn", "dob", "email", "phone", "address"
}

def scrub(data: dict) -> dict:
    return {
        k: "[REDACTED]" if k.lower() in PII_FIELDS else v
        for k, v in data.items()
    }
```

If `email` must be traceable: log `sha256(email)` instead of raw value.

---

## Log Aggregation — Stack Options

| Stack | Best for | Raven notes |
|---|---|---|
| **CloudWatch Logs** | AWS-native, low ops burden | Use log groups per service, metric filters for alerts |
| **ELK / OpenSearch** | Full-text search, dashboards | High ops cost — justify before adding |
| **Grafana Loki** | Kubernetes-native, label-based | Pairs with Prometheus/Grafana stack |
| **Splunk** | Enterprise compliance, audit | Expensive — use only if mandated |
| **stdout → platform** | Cloud Run, ECS, K8s | Simplest — let infra handle routing |

**Recommendation for greenfield:** stdout → CloudWatch (AWS) or Loki (K8s). Don't self-host ELK unless you have dedicated ops capacity.

---

## Retention Policy — By Data Class

| Log type | Recommended retention | Reason |
|---|---|---|
| DEBUG (never in prod) | N/A | Not stored |
| INFO / business events | 30 days hot, 1 year cold | Debugging window + audit |
| ERROR / exceptions | 90 days hot, 2 years cold | Incident review |
| Security / auth events | 1 year hot, 7 years cold | Compliance (SOC2, GDPR) |
| PII-adjacent logs | Scrubbed at ingest | GDPR / CCPA — no retention |

---

## Alerting on Log Patterns

Define alerts on log content, not just metrics:

```yaml
# CloudWatch Metric Filter example
filterPattern: '{ $.level = "ERROR" && $.service = "payment-service" }'
metricName: PaymentServiceErrors
threshold: 5 in 1 minute → page oncall
```

**Key patterns to alert on:**
- `level: ERROR` spike in any service
- `event: auth.failure` rate > threshold → credential stuffing
- `event: db.query_slow` duration > 5s → index issue
- Any log containing `exception`, `traceback`, `panic`

---

## Distributed Tracing Integration

Logs + traces = full observability. Correlation strategy:

```python
# OpenTelemetry — attach trace context to logs
from opentelemetry import trace

span = trace.get_current_span()
ctx = span.get_span_context()

logger.info("payment.processed", extra={
    "trace_id": format(ctx.trace_id, "032x"),
    "span_id": format(ctx.span_id, "016x"),
    "amount_cents": amount,
})
```

This lets you jump from a log line → full trace in Jaeger/Honeycomb/Tempo.

---

## Anti-Patterns — Hard Stops

```
❌ logger.info(f"Processing {user.email}")          — PII in log
❌ logger.debug(f"DB response: {response}")          — sensitive data dump
❌ print("Error:", e)                                — not structured
❌ logging.exception(str(e))                         — use exc_info=True instead
❌ for item in items: logger.info(f"item: {item}")   — chatty loop
❌ No correlation ID                                 — untraceable in prod
❌ Log level INFO for 1000 calls/sec tight loop      — performance sink
```

---

## Raven Guard Integration

Log management hooks into Raven's audit trail:

- Every `CRITICAL` log → auto-creates Raven incident entry
- Security events (`auth.failure`, `secret.detected`) → fires `emit-violation.py`
- Log anomaly patterns → flagged in `docs/observations/security_log.md`

---

## Deliverable Format

When reviewing or designing a logging system, produce:

```markdown
## Log Management Review — {service}

### Current State
- Format: [JSON / text / mixed]
- Destination: [CloudWatch / stdout / file]
- Correlation IDs: [yes / no]
- PII risk: [found / clean]

### Issues Found
| Issue | Severity | File:Line |

### Recommended Setup
- Library: [recommendation]
- Format: [JSON schema]
- Correlation: [pattern]
- Retention: [by data class]
- Alerts: [3 key patterns]

### Code Changes Required
[specific diffs or examples]
```
