---
name: agent-chaining
description: Use when designing or reviewing multi-agent systems, Claude subagent orchestration, parallel vs sequential agent execution, context passing between agents, tool delegation, agent memory patterns, and Claude Agent SDK workflows.
allowed-tools: Read, Bash, Grep, WebFetch
---

# Agent Chaining Specialist

Domain: Multi-Agent Systems · Claude Agent SDK · Orchestration · Context Management

---

## Pre-flight — ask before designing any chain

1. What problem actually requires multiple agents? → single agent first, always
2. Sequential or parallel? → depends on step dependencies
3. What's the token budget? → each subagent call costs tokens
4. What are the failure modes? → what happens if a subagent fails mid-chain?
5. Where does shared state live? → agents don't share memory

**Rule:** If one agent with the right tools can do it → don't chain. Chaining adds latency, cost, and failure surface. Justify it.

---

## When to chain vs not

| Chain when... | Don't chain when... |
|---|---|
| Work can run in parallel | Single-domain task |
| Specialist isolation needed | Tightly sequential, no parallelism |
| Context window exceeded | Shared mutable state needed |
| Independent verification needed | Low latency requirement |
| Long-running background work | You're adding complexity for no gain |

---

## Agent types — match to task

| Type | Use for |
|---|---|
| `claude` | General catch-all (all tools) |
| `Explore` | Read-only search and analysis |
| `Plan` | Architecture, implementation planning |
| `general-purpose` | Research, multi-step investigation |
| Named agents | Specialist knowledge domains |

Don't use `claude` (all tools) when `Explore` (read-only) is safer and sufficient.

---

## Spawning — the critical rules

**Subagent has NO memory of the parent conversation.** The prompt must be fully self-contained.

```python
Agent({
    "description": "Short 3-5 word description",
    "subagent_type": "general-purpose",
    "prompt": "...",           # must include file paths, context, what was tried, expected output form
    "run_in_background": False # True for non-blocking long tasks
})
```

**Parallel:** send multiple Agent calls in a single message — they run concurrently. Never send independent agents sequentially — doubles latency for no reason.

---

## Context passing — 3 patterns

- **Self-contained prompt** — include all context inline: file paths, error, what's ruled out, expected output format
- **File handoff** — orchestrator writes intermediate results to a temp file; subagent reads it. Good for large context. Bad for parallel agents that might conflict.
- **Summary handoff** — orchestrator summarises Phase 1 findings; subagent gets compressed context. Good for sequential chains.

---

## Orchestrator design — lean

```
✅ Orchestrator: decides what, in what order, who does it — synthesizes results
❌ Orchestrator: heavy computation, large file reads, code writing — push this to subagents
```

Keep orchestrator context budget for coordination. Subagents do the work.

**Good subagent prompt pattern:**
1. Goal in the first sentence
2. Absolute file paths — no relative references
3. What you've already done / ruled out
4. Expected output form
5. Scope cap — "only look at src/api/, not tests/"
6. Failure instruction — "if X not found, report that, don't guess"

---

## Common patterns

| Pattern | Structure |
|---|---|
| Research → Implement → Verify | Explore (read-only) → Plan → Claude → Explore (verify) |
| Parallel domain analysis | [Security · DB · API] in parallel → Orchestrator synthesizes |
| Map-Reduce | Orchestrator splits → N agents process chunks → Orchestrator reduces |
| Cross-Check | Agent A implements → Agent B reviews independently → Orchestrator reconciles |

---

## Failure handling

| Failure | Handle with |
|---|---|
| Empty / error response | Retry once with expanded context |
| Parallel agents conflict | Orchestrator resolves, flags conflict |
| Background agent stalls | Check with TaskOutput, set timeout |
| Context too long for subagent | Summarise before passing |
| Subagent goes off-scope | Narrow prompt, add explicit scope boundaries |

---

## Anti-patterns — hard stops

```
❌ Chaining when one agent suffices
❌ Passing secrets in subagent prompts
❌ Assuming subagent has parent context
❌ Sequential chain where steps are independent — use parallel
❌ Orchestrator doing all the heavy work itself
❌ No failure handling — assuming success
❌ Infinite agent recursion
❌ Shared mutable file writes without locking
```

---

## Raven integration

```
1. Declare agent dependencies in manifest
2. Subagents respect Raven rules — no manifest bypass
3. Never pass manifest.secrets.json in subagent prompts
4. Orchestrator logs what each subagent was asked to do
5. Guard agents fire on subagent PostEdit hooks same as direct edits
```

---

## Deliverable format

```markdown
## Agent Chain Design — {task}
### Justification: why chaining / why single agent insufficient
### Chain Diagram: [Orchestrator] → [SubAgent A (parallel)] → [result]
### Agent Specs: | Agent | Type | Tools | Scope | Output |
### Context Passing: how results flow between agents
### Failure Handling: | Scenario | Handling |
### Token Budget: orchestrator ~Xk · subagents ~Xk each · total ~Xk / 200k = X%
### Risks: [list]
```
