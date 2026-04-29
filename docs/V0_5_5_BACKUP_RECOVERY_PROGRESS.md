# MindForge v0.5.5 Backup / Recovery Progress

## Goal

Add local safety rails for backup, export, and recovery checks without turning
MindForge into cloud sync or a vault organizer.

## Product Fixes

- Added `mindforge backup export` for local safe exports.
- Export includes human_approved card summaries, state summary, and a 7-day
  review schedule.
- Existing export directories are never overwritten.
- `mindforge doctor --paths` shows local read/write boundaries.
- Doctor now checks state, cards, BM25 index, review schedule, package assets,
  and demo-vault availability with next-action hints.

## Smoke

```bash
mindforge doctor --vault examples/demo-vault --paths
mindforge backup export --vault examples/demo-vault
```

## Non-goals

- No cloud sync.
- No telemetry upload.
- No `.env` read.
- No real LLM call.
- No Obsidian plugin.
- No formal Obsidian note writes or vault reorganization.
