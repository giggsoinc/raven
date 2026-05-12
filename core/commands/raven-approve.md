---
name: raven-approve
description: Use when an architect wants to approve a pending library
  request. Updates manifest.json and notifies the requesting developer.
---

# /approve

Usage: /approve {library} {version}

Steps:
1. Read .raven/manifest.json
2. Add library to stack.libraries with approved_by + approved_at
3. Bump manifest version + add changelog entry
4. Output: "✅ {library}=={version} approved — update manifest.json and notify dev"

Dev must pull latest manifest before proceeding.
