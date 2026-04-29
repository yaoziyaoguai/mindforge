# v0.7.7 Dogfooding Friction Fixes

Goal: run the local dogfooding path on disposable non-sensitive vault copies and smooth confusing CLI handoffs.

Dogfooding path:

```bash
mindforge start --vault examples/demo-vault
mindforge commands
mindforge obsidian next --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --limit 5
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --staged-export --output-dir /tmp/mindforge-v077-staged --diff --write --confirm
mindforge obsidian preflight --vault examples/demo-vault --manifest /tmp/mindforge-v077-staged/Agent-Runtime-Observer.manifest.json
```

Friction fixed:

- `commands` now includes Obsidian next, staged export, and preflight handoffs.
- `scan` / `links` / `stage --dry-run` now point to the next Obsidian dogfooding command.
- staged export diff output says how to inspect files before preflight.
- `obsidian next` shows staged export and manifest counts plus the recommended preflight command.
- `today` / `next` use the configured state file path when deciding whether scan is still needed.
- `process --profile fake` ends with explicit approve-list guidance.

Safety boundary:

- No formal Obsidian notes are written.
- No `.env`, real LLM, telemetry upload, RAG/embedding, plugin, Web UI, automatic vault cleanup, or wikilink rewrite is used.
