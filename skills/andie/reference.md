# Andie Reference — Loaded at Pre-Flight

## Name Pool (culturally diverse — pick fresh each session)

Product/Startup: Seibel · Ruchi · Garry · Amara · Priya · Leila · Yuki
AI/Security: Bruce · Mikko · Fatima · Kenji · Aisha · Lior · Devon
Architecture: Martin · Kelsey · Meera · Andres · Omar · Sigrid · Ravi
Enterprise: Frank · Yamini · Kofi · Aaron · Ingrid · Tariq · Mei

RULES:
- Names must feel natural for a practitioner in the domain
- Span diversity: South Asian · East Asian · West African · East African · Middle Eastern · Latin American · European · Southeast Asian
- Every character is a hands-on practitioner — not a theorist
- Background must be specific to the PROMPT, not generic

## Framework Selection Guide

| Situation | Framework |
|-----------|-----------|
| Fast tactical loop | OODA |
| Recurring defect / process improvement | DMAIC or 5 Whys |
| Ambiguous complexity | Cynefin |
| Architecture choice | ADR + C4-level framing |
| Security risk | STRIDE or threat model |
| Business strategy | market / competitive / value framework |
| High-stakes decision | pre-mortem + risk register |
| Cross-domain, high-stakes | Cynefin + MDMP |
| Product / startup tradeoffs | RICE + Jobs to be Done |
| Innovation / design | Double Diamond |

RULE: Pick the lightest framework that improves the plan. Framework choice is a proposal if it changes scope.

## Model Routing

| Mode | Claude | OpenAI / ChatGPT | Gemini | Perplexity | Manus |
|------|--------|-------------------|--------|------------|-------|
| War — fast | Haiku | gpt-4o-mini | Flash | Sonar Small | fastest |
| Deep — balanced | Sonnet prev | gpt-4o | Pro | Sonar Large | standard |
| Kaizen — balanced | Sonnet prev | gpt-4o | Pro | Sonar Large | standard |
| Drama — sharp | Sonnet latest | gpt-4o | 1.5 Pro | Sonar Huge | premium |
| Summaries / notes | Haiku | gpt-4o-mini | Flash | Sonar Small | fastest |
| Max — explicit only | Opus | o1 / o3 | Ultra / 2.0 | — | — |

RULE: Never use max-tier by default. Only when user explicitly asks.
