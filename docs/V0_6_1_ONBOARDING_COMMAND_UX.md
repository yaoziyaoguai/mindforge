# MindForge v0.6.1 Onboarding / Command UX

## Goal

Make MindForge easier to open on day one: show current local state, explain the
safe default path, and point to the next command without adding Web UI, TUI, or a
plugin.

## First Day

```bash
mindforge start --vault examples/demo-vault
mindforge commands
mindforge today --vault examples/demo-vault
mindforge doctor --vault examples/demo-vault --paths
```

## Product Fixes

- Added `mindforge start` as a read-only onboarding entry.
- `commands` is grouped by user goals: first start, import/process, approve,
  recall, review, Obsidian dry-run, backup/doctor, debug/safety.
- `start` and `commands` keep safety visible: fake by default, no `.env` read,
  no real LLM, no formal Obsidian note writes.

## Non-goals

- No Web UI / TUI.
- No real LLM default path.
- No `.env` read.
- No RAG / embedding.
- No Obsidian plugin.
- No automatic approve or telemetry upload.
