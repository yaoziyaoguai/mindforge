# v0.7.1 Obsidian Stage Preview

## Goal

Make `mindforge obsidian stage --dry-run` clear enough for a user to inspect a disposable, non-sensitive vault copy before any staged output is written.

## Recommended Command

```bash
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

## Preview Boundary

The preview reports vault/source status, proposed action, proposed staged path, title, wikilinks, frontmatter keys, source type, skipped reason, risk warning, and next command. It does not write files, move notes, rewrite wikilinks, call an LLM, read `.env`, upload telemetry, or modify formal Obsidian notes.

## Smoke

```bash
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

## Non-goals

- No Obsidian plugin.
- No automatic vault cleanup.
- No formal note writes.
- No RAG / embedding.
- No real LLM.
- No Web UI / TUI.
