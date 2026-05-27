---
name: raven-approve
description: Approve pending library requests and discovered tools. Updates manifest.json with approval metadata. Handles both library approvals and Tier 2b tool acceptance from discover().
---

# /approve

## Library Approval

Usage: `/approve {library} {version}`

Steps:
1. Read .raven/manifest.json
2. Add library to stack.libraries with approved_by + approved_at
3. Bump manifest version + add changelog entry
4. Output: "✅ {library}=={version} approved — update manifest.json and notify dev"

Dev must pull latest manifest before proceeding.

## Tool Acceptance (Tier 2b — from discover())

Usage: `/approve tool {tool_name}` or user says "approve" after discover() presents a tool.

Steps:
1. Read .raven/manifest.json
2. Read discovery cache: `.raven/.cache/discovery/{tool-slug}.json`
3. Validate trust score from discovery:
   - HIGH trust → approve directly
   - MEDIUM trust → approve with note: "Community tool — verify updates quarterly"
   - LOW trust → require explicit confirmation: "⚠️ This tool is unverified. Type 'approve anyway' to proceed."
4. Add to manifest under `stack.tools`:
   ```json
   {
     "name": "{tool_name}",
     "source": "{mcp-registry / github / vendor}",
     "trust": "{HIGH/MEDIUM/LOW}",
     "approved_by": "{user}",
     "approved_at": "{ISO8601}",
     "discovered_at": "{ISO8601}",
     "review_by": "{approved_at + 90 days}"
   }
   ```
5. Bump manifest version + add changelog entry
6. Output: "✅ {tool_name} approved — available in future sessions for this project"

## Tool Review Cycle

When a session starts and manifest has tools with `review_by` < today:

```
⚠️ TOOL REVIEW DUE:
  {tool_name} — approved {date}, review due {date}
  Trust: {level} | Source: {source}
  → Say "renew" to extend 90 days, "remove" to revoke, "info" to check current status.
```

## Tool Removal

Usage: `/approve remove {tool_name}`

Steps:
1. Remove from manifest stack.tools
2. Add to changelog: "Removed: {tool_name} — {reason}"
3. Output: "🗑️ {tool_name} removed from approved tools"

## Rules
- Library approval and tool acceptance use the SAME manifest file
- Tools with LOW trust always require double confirmation
- Review cycle is 90 days for MEDIUM/LOW trust, 180 days for HIGH trust
- Removal is soft — tool is logged in changelog, not hard-deleted from history
