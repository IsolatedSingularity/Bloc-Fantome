---
name: bloat-purge
description: Directory bloat detection and cleanup. Find oversized files, orphaned artifacts, redundant content, and recommend archive or deletion.
---

# Bloat Purge

## When to Use
- Repo feels large or slow to clone
- After a major feature is complete (cleanup pass)
- Before a release or archive operation
- User requests a directory health check

## Detection Steps
1. **Size audit:** find files > 1MB, directories > 50MB
2. **Orphan check:** files not referenced by any code or config
3. **Duplicate check:** same content in multiple locations
4. **Stale check:** files not modified in 6+ months with no references
5. **Gitignore audit:** large files that should be ignored

## Report Format
```
## Bloat Report: <repo name>
Total size: X MB (Y files)

### Top 10 Largest Files
| File | Size | Last Modified | Recommendation |
|------|------|---------------|----------------|

### Orphaned Files (no references found)
### Gitignore Gaps
### Recommended Actions
```

## Rules
- Never delete without explicit approval
- Distinguish between "safe to delete" and "archive first"
- Respect data files in scientific repos (they may look like bloat but are results)
