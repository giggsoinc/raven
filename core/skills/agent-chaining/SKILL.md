---
name: agent-chaining
description: Use when designing or reviewing multi-agent systems, Claude subagent orchestration, parallel vs sequential agent execution, context passing between agents, tool delegation, agent memory patterns, and Claude Agent SDK workflows. Covers Anthropic agent patterns and production multi-agent architecture.
allowed-tools: Read, Bash, Grep, WebFetch
---

# Agent Chaining Specialist

Domain: Multi-Agent Systems · Claude Agent SDK · Orchestration · Context Management
Expert model: Anthropic Agent SDK patterns — production multi-agent architecture, subagent design, tool delegation

---

## Pre-flight Check

Before designing any agent chain:

1. **What problem requires multiple agents?** → single agent first — always
2. **Sequential or parallel?** → depends on dependencies between steps
3. **Context budget?** → each subagent call costs tokens — model the flow
4. **Failure modes?** → what happens if subagent fails mid-chain?
5. **State management?** → where does shared state live between agents?

**Rule:** If one agent with the right tools can do it → don't chain. Chaining adds latency, cost, and failure surface. Justify it.

---

## Core Concepts

### What is Agent Chaining?

An **orchestrator agent** spawns **subagents** to handle parallel or specialized work. Each subagent runs independently with its own context, tools, and scope. The orchestrator synthesizes results.

```
User Request
    │
    ▼
Orchestrator Agent
    ├── SubAgent A (parallel) → result A
    ├── SubAgent B (parallel) → result B
    └── SubAgent C (sequential, uses A+B) → result C
    │
    ▼
Synthesized Response
```

### When to Chain

| Scenario | Pattern |
|---|---|
| Tasks that can run in parallel | Parallel subagents — reduces wall-clock time |
| Specialized domain work | Specialist subagents — keep orchestrator lean |
| Work exceeds context window | Sequential handoff — pass summaries not full context |
| Independent verification | Two agents cross-check each other |
| Long-running background work | Background agent + notification |

### When NOT to Chain

| Scenario | Why |
|---|---|
| Simple single-domain task | One agent + right tools is faster and cheaper |
| Tightly sequential with no parallelism | Just use a single agent with ordered tool calls |
| Shared mutable state | Agents don't share memory — you'd need external state store |
| Low latency requirement | Each agent adds round-trip cost |

---

## Claude Agent SDK — Key Patterns

### Spawning a Subagent

```python
# Via Agent tool in Claude Code
Agent({
    "description": "Short 3-5 word description",
    "subagent_type": "general-purpose",  # or specific agent type
    "prompt": "Self-contained task description with all context needed",
    "run_in_background": False,  # True for non-blocking
})
```

**Critical rule:** The subagent has NO memory of the parent conversation. The prompt must be **fully self-contained** — include file paths, relevant context, what was already tried, what form the answer should take.

### Parallel Execution

Send multiple Agent calls in a single message. They run concurrently:

```
# Correct — fires both in parallel
message: [
  Agent(description="Search frontend", prompt="Find all useState calls in src/"),
  Agent(description="Search backend", prompt="Find all DB queries in api/"),
]
```

**Anti-pattern:** Sending agents sequentially when they're independent — doubles latency for no reason.

### Background Agents

```python
Agent({
    "description": "Long-running build validation",
    "prompt": "Run the full test suite and report failures...",
    "run_in_background": True,
})
# Parent continues doing other work — notified when subagent completes
```

Use for: long-running tasks (test runs, large file analysis) where you have other independent work to do.

---

## Context Passing — The Hard Problem

Subagents have no shared memory. All context must be explicit.

### Pattern 1 — Self-Contained Prompt

Pass everything needed in the prompt:

```python
Agent(prompt=f"""
    Task: Find and fix the auth bug in src/auth/login.py.
    
    Context:
    - File path: {file_path}
    - Error: {error_message}
    - We've already ruled out: database connection issues, session expiry
    - The bug appears when user has 2FA enabled
    - Return: the specific lines changed and why
""")
```

### Pattern 2 — File-Based Handoff

Orchestrator writes intermediate results to a file. Subagent reads it.

```python
# Orchestrator writes context
Write("/tmp/analysis-context.json", json.dumps({
    "findings": findings,
    "scope": scope,
    "constraints": constraints,
}))

# Subagent reads it
Agent(prompt="""
    Read /tmp/analysis-context.json for context.
    Based on the findings there, implement the fix in...
""")
```

Good for: large context that would bloat the prompt. Bad for: parallel agents that might conflict.

### Pattern 3 — Summary Handoff

Orchestrator summarises, subagent gets the summary:

```python
summary = f"""
    Phase 1 complete. Found:
    - 3 auth endpoints missing rate limiting
    - 2 DB queries with SQL injection risk (lines 145, 203)
    - 1 secret hardcoded in config.py:47
    
    Phase 2: Fix the SQL injection issues only. Files: api/users.py, api/orders.py
"""
Agent(prompt=summary)
```

Good for: sequential chains where later agents need compressed context of earlier work.

---

## Agent Types — Claude Code

| Type | Use for | Tools available |
|---|---|---|
| `claude` | General catch-all | All tools |
| `Explore` | Read-only search and analysis | Read, Bash (read-only), Grep |
| `Plan` | Architecture, implementation planning | All except Edit, Write |
| `general-purpose` | Research, multi-step investigation | All tools |
| Named agents (e.g. `claude-code-guide`) | Specialist knowledge domains | Domain-specific |

**Principle:** Match agent type to task. Don't use `claude` (all tools) when `Explore` (read-only) is safer and sufficient.

---

## Orchestrator Design Principles

### Lean Orchestrator

The orchestrator should coordinate, not do deep work:

```
✅ Orchestrator decides: what to do, in what order, who does it
✅ Orchestrator synthesizes: collects results, forms final response
❌ Orchestrator implements: heavy computation, large file reads, code writing
```

Push implementation to subagents. Keep the orchestrator's context budget for coordination.

### Prompt Writing for Subagents

The quality of the subagent depends entirely on the prompt. Rules:

```
1. State the goal in the first sentence
2. Include all file paths — no relative references
3. Say what you've already done / ruled out
4. Say what form the response should take
5. Cap scope — "only look at src/api/, not tests/"
6. Include failure instructions — "if X not found, report that, don't guess"
```

Poor prompt:
```
Find the bug and fix it.
```

Good prompt:
```
Find and fix the race condition in /Users/me/project/src/worker.py.
Context: two threads call process_job() simultaneously — the job_lock
mutex at line 45 doesn't cover the DB write at line 67. We already
ruled out the queue — it's single-consumer. Fix only the locking — don't
refactor other logic. Return: the changed lines and a 1-sentence
explanation of why this fixes the race.
```

---

## Failure Handling

Subagents can fail. The orchestrator must handle it:

```python
# Defensive orchestration — don't assume subagent succeeded
result = Agent(prompt="Analyze the auth module...")

# Check result before acting on it
if "error" in result.lower() or "not found" in result.lower():
    # Retry with more context, or fall back to single-agent approach
    ...
```

**Failure modes to design for:**

| Failure | Handling |
|---|---|
| Subagent returns empty/error | Retry once with expanded context |
| Parallel subagents return conflicting results | Orchestrator resolves, flags conflict |
| Background agent never completes | Set timeout, check with TaskOutput |
| Context too long for subagent | Summarise before passing |
| Subagent goes off-scope | Narrow the prompt, add explicit scope boundaries |

---

## Token Economics

Each agent call costs tokens. Model the budget:

```
Total session budget: ~200k tokens (Claude Sonnet)

Orchestrator context:     ~5k tokens
Per subagent call:        ~10-30k tokens (prompt + response)
N parallel subagents:     N × 20k = budget consumed

Example: 4 parallel subagents = ~80k tokens
         Leaves ~120k for orchestrator + follow-up
```

**Rules:**
- Count your agents before you chain
- Use `haiku` model for fast/cheap subagents when task is simple
- Use `sonnet` for complex reasoning subagents
- Background agents don't block — use them for heavy lifting

---

## Raven Integration — Agent Chaining Discipline

When building agent chains under Raven:

```
1. Declare agent dependencies in manifest (approved_skills or agent list)
2. Each subagent respects Raven rules — no manifest bypass
3. Subagents NEVER read manifest.secrets.json — not passed in prompt
4. Audit trail: orchestrator logs what each subagent was asked to do
5. Guard agents fire on subagent PostEdit hooks same as direct edits
```

**Spawn guard-git-watch as a subagent for sensitive file operations:**
```python
Agent(
    subagent_type="raven:guard-git-watch",
    prompt="Monitor this file operation for secret exposure..."
)
```

---

## Common Patterns

### Pattern: Research → Implement → Verify

```
1. Explore agent   → read-only analysis, find the relevant files
2. Plan agent      → design the implementation approach
3. Claude agent    → implement the change
4. Explore agent   → verify the change (read-only check)
```

Sequential. Each feeds the next.

### Pattern: Parallel Domain Analysis

```
1. [parallel] Security agent   → check auth and access control
2. [parallel] DB agent         → check queries and indexes
3. [parallel] API agent        → check endpoints and rate limiting
4. Orchestrator                → synthesize findings into report
```

All three run simultaneously. Orchestrator waits for all, then synthesizes.

### Pattern: Map-Reduce

```
1. Split work into N chunks (orchestrator)
2. [parallel] N agents process one chunk each
3. Orchestrator reduces results into final output
```

Good for: large codebases where you need to scan many files faster than a single agent can.

### Pattern: Cross-Check

```
1. Agent A   → implement the fix
2. Agent B   → review Agent A's output independently (no shared context)
3. Orchestrator → if B flags issues, reconcile; else ship
```

Good for: high-stakes changes where you want independent verification.

---

## Anti-Patterns — Hard Stops

```
❌ Chaining when one agent suffices                  — unnecessary cost + latency
❌ Passing raw secrets in subagent prompts            — security violation
❌ Assuming subagent has parent context               — it doesn't — be explicit
❌ Sequential chain where steps are independent       — use parallel
❌ Orchestrator doing all the heavy work itself       — defeats the purpose
❌ No failure handling — assuming subagent succeeded  — brittle production code
❌ Infinite agent recursion — agent spawns itself     — runaway cost
❌ Sharing mutable state via file without locking     — race condition
```

---

## Deliverable Format

When designing or reviewing an agent chain, produce:

```markdown
## Agent Chain Design — {task}

### Justification
Why chaining is needed here: [reason]
Why single agent is insufficient: [reason]

### Chain Diagram
[Orchestrator] → [SubAgent A (parallel)] → [result A]
              → [SubAgent B (parallel)] → [result B]
              → [SubAgent C (sequential, uses A+B)] → [result C]

### Agent Specs
| Agent | Type | Tools | Scope | Output |
|---|---|---|---|---|

### Context Passing Strategy
- A → Orchestrator: [how]
- Orchestrator → C: [how]

### Failure Handling
| Failure scenario | Handling |

### Token Budget
- Orchestrator: ~Xk
- SubAgent A: ~Xk
- SubAgent B: ~Xk
- Total: ~Xk / 200k budget = X%

### Risk Assessment
- [risk 1]
- [risk 2]
```
