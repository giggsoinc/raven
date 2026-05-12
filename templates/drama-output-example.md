# Drama Mode Output — Enterprise Gemini Enforcement
**Date:** 2026-05-09 | **Session:** Scene 1 of 3 | **Panel:** Bruce (CISO) · Kelsey (Infra) · Meera (DBA) · Arun (Dev) · Zaid (Dev)

---

## Strategy Document

### Problem Statement
Developers are using personal Gemini API keys because enterprise access requires a two-week approval process. Company data exits under personal accounts with no audit trail, no revocation capability, and no usage visibility.

### Strategic Direction
Make enterprise Gemini invisible to the developer. No ticket. No wait. It is simply present when they open their IDE. Enforcement happens at the infrastructure layer — not the policy layer.

### Guiding Principles
1. **Friction kills compliance.** If enterprise tools are harder than personal tools, developers will use personal tools. Always.
2. **Invisible enforcement beats visible policy.** A credential injected by MDM is more reliable than a policy document.
3. **Audit everything.** Every API call logged. Who, when, what model, how many tokens.

### Solution Architecture
Three layers — inject, scan, log:

| Layer | Mechanism | Owner | Dev Experience |
|---|---|---|---|
| Inject | MDM pushes enterprise credential to dev machine | IT | Nothing — it's just there |
| Scan | Raven pre-commit blocks personal key patterns | Engineering | Blocked at commit if personal key found in code |
| Log | Every API call logged — identity, timestamp, tokens | IT/Security | Invisible — happens in background |

### Key Design Decisions
- Keys scoped to Google Workspace identity — auto-revoked on offboarding
- Quarterly key rotation automated — devs never touch it
- 24-hour credential cache for offline scenarios
- No approval ticket required for standard dev usage

---

## Architecture Decision Record (ADR)

**ADR-001: Enterprise Gemini Enforcement via MDM Injection**
**Status:** Decided
**Date:** 2026-05-09

### Context
Three enforcement options considered:
1. Approval ticket process (current state)
2. Trust + acceptable use policy
3. MDM credential injection + code scanning

### Decision
Option 3 — MDM injection + Raven pre-commit scanning + audit logging.

### Rationale

| Factor | Why it matters |
|---|---|
| Approval tickets take 2 weeks | Proven bypass — Arun used personal key under deadline pressure |
| Policy without enforcement | Zaid shared a personal login with two teammates. Policy failed. |
| MDM already deployed | No new infrastructure — extend existing MDM capability |
| Raven already scanning | Pre-commit hook extended with personal key pattern detection |
| Google Workspace identity scoping | Key dies automatically when employee offboards |

### Consequences
- **Positive:** Zero dev friction. Auditable. Auto-revocation. Quarterly rotation.
- **Negative:** MDM dependency. Offline grace period creates 24hr window.
- **Risks:** MDM failure = dev blocked. Mitigated by 24hr cache.

### Alternatives Rejected

| Option | Reason rejected |
|---|---|
| Approval ticket process | Too slow. Devs bypass under deadline pressure. Proven. |
| Trust + policy only | Failed already. Zaid shared credentials. Arun used personal key. |
| Hard block without injection | Creates rage. Blocks work without providing the alternative. |

---

## Action Plan

| # | Action | Owner | By When | Done When |
|---|---|---|---|---|
| 1 | Configure MDM to push enterprise Gemini credential to all dev machines | IT | Week 1 | All dev machines show enterprise key in environment |
| 2 | Add personal Gemini key patterns to Raven `secret-scan.py` | Engineering | Week 1 | Pre-commit blocks `GOOGLE_API_KEY` personal format |
| 3 | Enable GCP Audit Logs for all Gemini API calls | IT/Security | Week 1 | Every call logged with identity + tokens |
| 4 | Configure 24hr credential cache in MDM | IT | Week 1 | Devs can work offline up to 24hrs |
| 5 | Set up quarterly key rotation automation | IT | Week 2 | Rotation runs without dev intervention |
| 6 | Communicate to all 70 devs — no ticket needed | Engineering Lead | Week 1 | Team notified, old process retired |
| 7 | Revoke all personal Gemini keys in use | Security | Week 2 | Audit log shows zero personal key usage |
| 8 | Add enterprise Gemini to Raven `manifest.org.json` Tier 1 whitelist | Architecture | Week 1 | Auto-approved in all projects |

### Success Metrics
- Personal Gemini key usage: 0 within 30 days
- Dev complaints about access: 0 (invisible injection)
- Audit log coverage: 100% of Gemini API calls

---

## Risks
*(surfaced by Arun and Zaid)*

| Risk | Source | Mitigation |
|---|---|---|
| MDM fails to push credential | Infra failure | 24hr cache + IT alert on push failure |
| Dev extracts injected key for personal use | Boundary Pusher (Zaid) | Key scoped to Workspace identity — unusable outside org context |
| Enterprise Gemini goes down | SLA gap | Google Enterprise SLA — escalate to Google, not internal architecture problem |
| Devs find new personal AI tools | Human nature (Arun) | Raven scans for known personal API key patterns — update list quarterly |

## Ruled Out
- **Approval ticket process** — Two weeks average. Proven to cause bypasses under deadline pressure.
- **Policy-only enforcement** — Zaid shared credentials. Arun used personal key. Policy without enforcement is theater.
- **Hard block without alternative** — Creates developer rage. Never block without providing the path forward.

## Open Questions
- What is Google's enterprise Gemini SLA? → Needs IT to confirm with Google account team
- Which MDM platform is in use? → Needs IT to confirm (Jamf / Intune / Mosyle)
- Are there contractors who need access? → Needs HR/Legal to define contractor credential policy
