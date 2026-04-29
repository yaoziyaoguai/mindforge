# v0.7.3 Obsidian Scope Safety

## Goal

Make Obsidian dry-run and staged export safer by letting users narrow the vault scope and inspect vault safety before dogfooding.

## Recommended Commands

```bash
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --include 02-Knowledge --exclude 90-System
mindforge obsidian stage --dry-run --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --include 02-Knowledge
```

`--include` and `--exclude` can be repeated. Defaults continue to exclude runtime/tool directories such as `.obsidian`, `.git`, `.mindforge`, and `node_modules`.

## Safety Boundary

- Scope rules apply to both scan and stage preview.
- Stage writes are still gated; formal Obsidian notes are not modified.
- Vault safety doctor reports scope rules, runtime directory risks, staged export directory status, and next commands.
- Use only a non-sensitive disposable vault copy for dogfooding.

## Smoke

```bash
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --include 02-Knowledge
mindforge obsidian scan --vault examples/demo-vault --exclude 03-Projects
mindforge obsidian stage --dry-run --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --include 02-Knowledge
```

## Non-goals

- No Obsidian plugin.
- No automatic vault cleanup.
- No formal note writes.
- No RAG / embedding / real LLM.
