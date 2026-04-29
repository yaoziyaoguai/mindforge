# MindForge v0.5.4 Personal Daily Loop Progress

## Goal

Make MindForge feel useful when opened every day: show what changed, what needs
approval, what is due for review, whether recall is ready, and the next command
to run.

## Daily Command

```bash
mindforge today --vault examples/demo-vault
mindforge next --vault examples/demo-vault
mindforge approve list --vault examples/demo-vault
mindforge recall --query "agent" --vault examples/demo-vault
mindforge review weekly --vault examples/demo-vault
```

## Product Fixes

- Added `mindforge today` as a read-only daily status board.
- Enhanced `next` with a compact daily snapshot while keeping suggestions.
- Empty `approve list`, `recall`, and `review weekly` now include next-action
  hints instead of only empty results.

## Non-goals

- No RAG / embedding.
- No Obsidian plugin.
- No real LLM call.
- No `.env` read in daily-loop commands.
- No automatic approve or telemetry upload.
- No real Obsidian note writes.
