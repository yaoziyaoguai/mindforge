# v0.6.2 Approval / Review UX

## Goal

Make human approval and review feel like a daily learning workflow, while keeping MindForge local, explicit, and safe.

## Recommended Daily Path

1. Run `mindforge today --vault examples/demo-vault` or `mindforge next --vault examples/demo-vault`.
2. Check pending drafts with `mindforge approve list --vault examples/demo-vault`.
3. Explicitly approve one card with `mindforge approve --card <card-path>`.
4. Search approved memory with `mindforge recall --query "agent" --vault examples/demo-vault`.
5. Plan review with `mindforge review weekly --vault examples/demo-vault`.

## Smoke Commands

```bash
mindforge approve list --vault examples/demo-vault
mindforge recall --query "agent" --vault examples/demo-vault
mindforge review weekly --vault examples/demo-vault
```

## Non-goals

- No automatic approve.
- No real LLM call by default.
- No `.env` reading for approval / review / recall UX.
- No writes to real Obsidian notes.
- No RAG / embedding.
- No Obsidian plugin.
- No telemetry upload.
