# v0.7.5 Obsidian Dogfooding Flow

Goal: make the safe Obsidian integration path easy to run on a disposable, non-sensitive vault copy.

Recommended entry:

```bash
mindforge obsidian next --vault <disposable-vault-copy>
```

Flow:

```bash
mindforge obsidian doctor --vault <copy>
mindforge obsidian scan --vault <copy> --limit 20
mindforge obsidian links --vault <copy>
mindforge obsidian stage --vault <copy> --source <note.md> --dry-run
mindforge obsidian stage --vault <copy> --source <note.md> --staged-export --output-dir /tmp/mindforge-obsidian-staged --diff --write --confirm
mindforge obsidian preflight --vault <copy> --manifest /tmp/mindforge-obsidian-staged/<export>.manifest.json
```

Manual steps:

- Inspect the staged markdown and manifest.
- Confirm backup expectations before any future write gate.
- Record feedback in `docs/templates/OBSIDIAN_DOGFOODING_CHECKLIST.md`.

Safety boundary:

- No formal Obsidian notes are written.
- No `.env`, real LLM, telemetry upload, RAG/embedding, plugin, Web UI, automatic vault cleanup, or wikilink rewrite is used.
