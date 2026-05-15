---
name: tools-landscape
description: Tool and product registry for Andie pre-flight. Maps problem types to tool options with tradeoffs. Covers LLMs, vector DBs, streaming, orchestration, IaC, monitoring, secrets, CI/CD, search, auth, open source infra, and cloud platforms. Load when a tool selection decision is in scope.
---

# Tools Landscape

Andie's tool and product registry. Read registry.json alongside this skill.

---

## When to Load

Load this skill during pre-flight when the session involves:
- Choosing between tools or platforms
- Evaluating a new tool for adoption
- Comparing open source vs commercial options
- Recommending a stack for a new project
- Migrating from one tool to another

---

## How to Use registry.json

1. Detect the category from the user's domain (see routing below)
2. Load relevant category entries from registry.json
3. Present top 3 candidates with tradeoffs — not a wall of options
4. State why each is relevant to *this specific problem*
5. Flag staleness if `last_updated` is older than 90 days

**Staleness check — always run at load time:**
```
registry.json last_updated: [date]
Today: [date]
Age: [N] days

If age > 90:
⚠️ Tools registry is [N] days old. The landscape may have shifted.
   Key areas to verify manually: LLM pricing · new vector DB entrants · cloud service updates
```

---

## Category Routing

| Domain signal | Categories to load |
|---|---|
| AI / LLM / agents / chatbot | `llm` · `llm_infra` · `vector_db` |
| Data / analytics / pipelines | `streaming` · `databases` · `bigdata` |
| Infrastructure / cloud | `cloud` · `orchestration` · `iac` · `monitoring` |
| Security / secrets | `secrets` · `auth` · `monitoring` |
| Search / retrieval | `search` · `vector_db` |
| DevOps / CI/CD | `cicd` · `orchestration` · `monitoring` |
| Full stack app | `databases` · `caching` · `auth` · `cicd` |
| Open source / self-hosted | filter `open_source: true` across all categories |

---

## Presentation Format

Always present as:

```
Tool options for [category] — [problem context]

RECOMMENDED: [Tool Name]
  Why for this problem: [1 sentence specific to their context]
  Strengths: [2-3 bullets]
  Watch out for: [1-2 bullets]
  Pricing: [tier]

ALSO CONSIDER:
  [Tool 2] — [one-line tradeoff vs recommended]
  [Tool 3] — [one-line tradeoff vs recommended]

SKIP UNLESS:
  [Tool 4] — only if [specific condition]

Open source alternative: [name] — [one line]
```

---

## Comparison Rules

- Never recommend more than 3 tools without a clear differentiator
- Always include one open source option if one exists
- Always state the "when NOT to use this" for the top recommendation
- For LLMs: always include cost-per-token context relative to use case volume
- For managed vs self-hosted: always state ops burden difference

---

## Update Protocol

When the registry is stale or a new tool emerges mid-session:

```
⚠️ [Tool name] may have updated since this registry was last checked.
   Recommend verifying: [specific thing to check — pricing / API / benchmark]
```

To update: edit registry.json, bump `last_updated`, run bundle.sh.

---

*Part of Andie v4.0 — tools-landscape skill*
