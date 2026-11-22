# Domain Packs — Format Specification

**Version:** 1.0
**Part of:** Raven v4 Agent Architecture (Tier 2a)

## What is a Domain Pack?

A lightweight JSON knowledge file that dynamic-specialist loads on demand. Cheaper than a full specialist skill (1-2K tokens vs 3-5K), covers the long tail of tools and frameworks without permanent token cost.

## When to use a Domain Pack vs a Full Specialist

| Signal | → Use |
|--------|-------|
| Tool/framework used frequently (3+ times) | Full specialist (Tier 1) |
| Tool category with multiple options to compare | Domain pack (Tier 2a) |
| Single tool, rarely used | dynamic-specialist without pack |
| Unknown tool, not in any pack | Tier 2b discovery |

## File Format

```json
{
  "pack": "pack-name",
  "version": "1.0",
  "last_reviewed": "2026-05-27",
  "description": "One line — what this pack covers",
  "consumed_by": ["specialist-name"],
  "tokens_estimated": 1500,

  "tools": [
    {
      "name": "Tool Name",
      "category": "category-tag",
      "description": "One sentence — what it does",
      "best_for": "When to pick this over alternatives",
      "gotchas": ["gotcha 1", "gotcha 2"],
      "anti_patterns": ["anti-pattern 1"],
      "docker": "image:tag, ports, volumes (if applicable)",
      "version_note": "Current stable version or version-specific info",
      "links": ["official docs URL"]
    }
  ],

  "decision_matrix": [
    {
      "signal": "When customer says or needs X",
      "recommend": "Tool Name",
      "why": "One sentence"
    }
  ],

  "relationships": {
    "upstream": ["what feeds into this domain"],
    "downstream": ["what this domain feeds"],
    "related_specialists": ["specialist-name"]
  }
}
```

## Rules

1. **Max 2K tokens** — if it's bigger, it should be a full specialist
2. **Decision matrix required** — packs exist to help CHOOSE, not just list
3. **Gotchas required per tool** — the value is knowing what breaks
4. **last_reviewed date required** — stale packs get flagged
5. **consumed_by required** — must name which specialist loads this pack
6. **No code examples** — packs are knowledge, not implementation. Specialists write code.

## How dynamic-specialist uses packs

```
Step 0 → Check packs/ directory for matching pack
  If found → Load pack JSON, skip search agent (Step 5)
  If not found → Proceed with normal dynamic flow
  
Pack loaded → dynamic-specialist uses:
  - tools[].description for context
  - tools[].gotchas for warnings
  - decision_matrix for recommendations
  - relationships for handoff awareness
```

## File naming

`packs/{pack-name}.json` — lowercase, hyphenated.

Examples:
- `packs/agent-frameworks.json`
- `packs/local-dev.json`
- `packs/graph-visualization.json`
