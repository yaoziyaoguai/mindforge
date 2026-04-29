# v0.7.x Obsidian Integration Readiness

Version train:

- v0.7.1: stronger Obsidian stage preview with safer skipped reports.
- v0.7.2: staged export directory, manifest, and diff preview for manual inspection.
- v0.7.3: include/exclude rules and vault safety doctor.
- v0.7.4: write-gate preflight that validates staged export readiness without writing notes.
- v0.7.5: dogfooding flow and checklist for disposable non-sensitive vault copies.

Recommended dogfooding path:

```bash
mindforge obsidian next --vault <disposable-vault-copy>
mindforge obsidian doctor --vault <copy>
mindforge obsidian scan --vault <copy> --limit 20
mindforge obsidian links --vault <copy>
mindforge obsidian stage --vault <copy> --source <note.md> --dry-run
mindforge obsidian stage --vault <copy> --source <note.md> --staged-export --output-dir /tmp/mindforge-obsidian-staged --diff --write --confirm
mindforge obsidian preflight --vault <copy> --manifest /tmp/mindforge-obsidian-staged/<export>.manifest.json
```

Current capabilities:

- doctor
- scan
- links
- stage dry-run
- staged export
- diff preview
- include/exclude
- safety doctor
- preflight
- dogfooding checklist

Current boundaries:

- No formal Obsidian note writes.
- No Obsidian plugin.
- No automatic vault cleanup or wikilink rewrite.
- No default real LLM path.
- No RAG / embedding.
- No telemetry upload.

Next candidates:

- v0.8 Real LLM Opt-in
- v0.7.7 write-gate hardening
- manual dogfooding
