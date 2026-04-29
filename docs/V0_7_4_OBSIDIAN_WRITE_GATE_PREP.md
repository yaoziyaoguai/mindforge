# v0.7.4 Obsidian Write-Gate Prep

Goal: validate staged export readiness for a future explicit write gate without writing formal Obsidian notes.

Recommended command:

```bash
mindforge obsidian preflight --vault <disposable-vault-copy> --manifest <export.manifest.json>
```

Result meanings:

- `PASS`: manifest, staged markdown, proposed vault target, backup path, recovery plan, and local-only safety flags are present.
- `WARNING`: readiness evidence exists, but a human must inspect conflicts such as an existing proposed target.
- `BLOCKED`: evidence is missing or unsafe; do not proceed toward any future write gate.

Safety boundary:

- No formal Obsidian notes are written in v0.7.4.
- Future writing still requires staged export, diff preview, backup, explicit human confirmation, write gate, and recovery path.
- Preflight does not read `.env`, call a real LLM, upload telemetry, build RAG/embedding, or store runtime/cache/index/log/sqlite/vector/graph layers in notes.

Smoke:

```bash
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --staged-export --write --confirm
mindforge obsidian preflight --vault examples/demo-vault --manifest .mindforge/staged/obsidian/Agent-Runtime-Observer.manifest.json
```
