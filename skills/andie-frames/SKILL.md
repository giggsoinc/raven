---
name: andie-frames
description: 3-phase browser testing skill. Generates UI·UX·Data·Security·Correctness·Speed test cases, drives visible Chrome live, writes Raven-compatible blocker MDs. Human watches and guides throughout. Andie packed inside — no external skill calls.
---

# Andie-Frames

AI browser testing you watch live. Like UiPath — but Claude drives it.

---

## QUICK START

```
/andie-frames https://your-app.com
```

**One-time setup — pick one:**
- **Chrome (recommended):** Install Claude-in-Chrome extension → open a regular Chrome window → connect it
- **Playwright fallback:** `npm i -g playwright && npx playwright install chromium`

**During the run — just talk:**

| Say | Result |
|---|---|
| `GO` | Start testing |
| `focus on security` | Filter cases, then start |
| `skip login tests` | Remove auth cases |
| `scroll down first` | Executes immediately, resumes |
| `stop` | Pauses — awaits instruction |
| `abort` | Stops, writes partial report |

---

## WHAT IT TESTS (20+ cases auto-generated)

| Category | Checks |
|---|---|
| UI | Broken images · layout · labels · error states · responsive |
| UX | Time-to-interactive · click latency · form feedback |
| Data | Network payloads · validation copy · API field completeness |
| Security | HTTPS · CSP · data exposure · auth lockout · logout |
| Correctness | Login flow · error states · redirects · HTTP status |
| Speed | Page load · TTFB · API response · blocking resources |

---

## WHAT GETS CREATED

```
tests/andie-frames/
  cases.csv                  ← generated test index
  yaml/TC001-*.yaml          ← one file per case

docs/andie-frames/{run_id}/
  FRAMES-REPORT.md           ← final verdict
  raven-queue.json           ← Raven auto-fix queue
  blockers/*.md              ← one per failure (Raven reads these)
  screenshots/               ← before + after every step
```

---

## CREDENTIALS — NEVER HARDCODED

Reference by key name only. Resolution order (first match wins):
1. `.env` in project → `~/.env` → Lockey MCP → AWS SSM → GCP Secret Manager → Vault → human prompt (masked)

---

## BUSINESS CONTEXT & SCOPE DOCUMENTS

Andie-Frames accepts scope input in any format. The richer the context,
the smarter the generated test cases.

### Scope resolution order (first match wins, all merged)

**1. Raven (checked automatically — no flag needed)**
At startup, query Raven for everything it knows about this project:
```
/raven-search "scope requirements test plan acceptance criteria known issues"
/raven-search "architecture decisions bugs blockers {url domain}"
```
Raven holds: PRDs · architecture docs · prior test runs · known bugs ·
ADRs · blocker history · acceptance criteria · security requirements.
If Raven has it — use it. No need to ask the human.

Announce what was found:
```
[andie-frames] Raven scope loaded:
  ✓ requirements.md     — acceptance criteria extracted
  ✓ architecture.md     — critical flows identified
  ✓ prior run blockers  — 3 known issues pre-loaded as P1 cases
  ✓ security-spec.md    — SOX controls mapped to security cases
```

**2. Scope documents — pass one or many:**
```
/andie-frames https://app.com --scope scope.md
/andie-frames https://app.com --scope requirements.pdf testplan.xlsx
/andie-frames https://app.com --scope *.md docs/scope.docx
```
Supported: `.md` · `.txt` · `.pdf` · `.docx` · `.pptx` · `.ppt` · `.xlsx` · `.xls` · `.csv`

**3. Inline at invocation:**
```
/andie-frames https://app.com "fintech, B2B, SOX compliance, payment flows critical"
```

**4. Interactive — only if nothing found above:**
```
[andie-frames] No scope found in Raven or files. Answer or skip:
  - What does this app do?
  - Who are the users?
  - What's critical to test?
  - Any known issues or recent changes?
```

### How scope shapes test cases

| Scope signal | Effect on test generation |
|---|---|
| "SOX compliance" | Adds audit trail, access control, data integrity cases |
| "payment flow" | Stricter data + security + correctness cases on checkout |
| "public landing page" | Skips auth cases entirely |
| "mobile users" | Adds responsive layout cases at 375px |
| "API-heavy" | Expands network payload and data category cases |
| "known issue: slow checkout" | Adds targeted speed cases on that flow |
| CSV/XLS with test cases | Imports existing cases + supplements with generated ones |
| PRD/spec doc | Extracts acceptance criteria → maps to correctness cases |

### Document parsing

- **PDF / DOCX / PPTX** — extracted via `anthropic-skills:pdf`, `anthropic-skills:docx`, `anthropic-skills:pptx`
- **XLSX / CSV** — parsed directly; existing test case rows imported as-is
- **MD / TXT** — read directly
- Multiple docs are merged — conflicts resolved by taking the union

Scope is stored in run state and printed in FRAMES-REPORT.md under **Scope Used**.

---

## INVOCATION OPTIONS

```
/andie-frames <url>                      ← full run, all categories
/andie-frames <url> --categories X,Y    ← specific categories only
/andie-frames <url> --runtime playwright ← bypass Chrome extension
/andie-frames frames <run-dir>           ← Andie review on existing run
```

---

## FLOW

```
PHASE 0 — INIT
  1. Detect runtime (Chrome MCP → Playwright → hard stop)
  2. Print clickable URL → human opens it → human says GO
  3. Ask for business context (see below)
  4. Resolve paths · parse input · resolve credentials
  5. URL reachability check (hard stop if blocked — shows fix options)

PHASE 1 — ANDIE GENERATES CASES (embedded — no external skill)
  Triad: Functional (QA) · Technical (DevTools) · Data (Coverage)
  Generates 20+ cases → writes cases.csv + yaml/ → HITL: confirm list

PHASE 2 — BROWSER EXECUTION (human watches live)
  Per step: screenshot before → action → screenshot after → dev tools capture
  Retry 3x on minor failures. CHECKPOINT on real blockers.
  Blocker → writes MD immediately with console + network + perf dump.
  Human can speak at any point. Reacts immediately.

PHASE 3 — ANDIE-FRAMES REVIEW (embedded)
  Reads all blocker MDs → cross-category pattern analysis
  Writes FRAMES-REPORT.md + raven-queue.json → HITL: confirm before writing
```

---

## RUNTIME RULES

- **Browser is always visible.** Never headless. Human watches every step.
- **Playwright fallback = `--headed` always.** Never silent.
- **CHECKPOINT is non-blocking.** Human can use Claude for other things while deciding.
- **Human input overrides everything.** Any message mid-run is acted on immediately.

---

## BLOCKER MD (Raven-readable frontmatter)

```markdown
---
run_id: · test_id: · status: BLOCKER · timestamp: · url: · step: ·
category: · raven_fixable: true|false · raven_tags: []
---
## Console at failure  ## Network at failure  ## Performance  ## Screenshots
```

**raven_fixable: true** → element_not_found · css · broken_link · js_error · csp · mixed_content
**raven_fixable: false** → auth_failure · 5xx · external_dependency · mfa

---

## HITL GATES

1. **After input parse** — confirm task block before browser opens
2. **After case generation** — confirm case list before execution
3. **After full run** — confirm FRAMES-REPORT before writing

---

## ANDIE SPECIALIST INTERFACE

Returns JSON when called from another skill:
```json
{
  "run_id": "…", "status": "complete|failed|awaiting_hitl",
  "pass_rate": 0.8, "failures": […],
  "report_path": "docs/andie-frames/{run_id}/FRAMES-REPORT.md",
  "raven_queue": "docs/andie-frames/{run_id}/raven-queue.json",
  "hitl_pending": { "question": "…", "options": ["…"] }
}
```

---

## URL BLOCKED?

If `navigate(url)` fails with permission error — full diagnosis printed:
- **SSH tunnel:** `ssh -N -L <port>:localhost:<port> user@host` → use `localhost:<port>`
- **HTTPS proxy:** nginx/caddy with real cert → use the domain
- **`/etc/hosts`:** `127.0.0.1 myapp.local` → use `myapp.local:<port>`
- **Playwright:** `--runtime playwright` — no URL restrictions

Hard stop until URL passes `navigate()`.
