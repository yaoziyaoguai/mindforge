# v0.7.2 Obsidian Staged Export

## Goal

Make Obsidian integration safer to inspect by writing generated candidates to a staged export directory instead of formal Obsidian notes.

## Recommended Command

```bash
mindforge obsidian stage \
  --vault examples/demo-vault \
  --source 02-Knowledge/agent-runtime-observer.md \
  --staged-export \
  --write --confirm
```

Use `--output-dir <path>` to choose a disposable export directory. Add `--diff` to compare the proposed markdown with an existing staged file.

## Safety Boundary

- Staged export writes only markdown + manifest files in the staged export directory.
- It does not overwrite existing staged files; a unique filename is generated.
- If a formal vault note may conflict, MindForge only warns and leaves it unchanged.
- The manifest records no real LLM, no `.env`, no telemetry upload, and no formal Obsidian note write.

## Smoke

```bash
mindforge obsidian stage --dry-run --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md
mindforge obsidian stage --staged-export --write --confirm --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md
mindforge obsidian stage --staged-export --diff --write --confirm --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md
```

## Non-goals

- No Obsidian plugin.
- No automatic apply into a formal vault.
- No automatic wikilink rewrite or vault cleanup.
- No RAG / embedding / real LLM.
