# MindForge First Release Notes

This note describes the first public-facing local MVP scope. It is not a next-version RFC or SDD.

## Included

- Local workspace initialization with `mindforge init`, `mindforge start`, and `mindforge status`.
- Web Setup as the primary model configuration entry.
- LLM-first Knowledge Card Workflow for local markdown sources.
- `ai_draft` generation followed by explicit human approval.
- Library, BM25 Recall, and Wiki generation from `human_approved` cards only.
- LLM-first Wiki synthesis, with deterministic/template rebuild kept as Advanced / Troubleshooting fallback.
- Bounded provider timeout/retry behavior and visible run progress for model calls.
- Workspace-anchored config and secret lookup for CLI and Web paths.

## Safety Boundaries

- API keys are entered through Web Setup and stored in the local secret store.
- API keys must not be committed, pasted into docs, or written into YAML.
- Raw source files are not promoted into Library / Recall / Wiki without explicit approval.
- No automatic approve path exists.
- No RAG, embedding, vector database, semantic merge, Obsidian plugin, or real Obsidian formal-note write is included in this release.

## Known Limitations

- Use non-sensitive material first; do not start with a private or work-sensitive vault.
- Long documents may need to be split or processed with a higher `timeout_seconds`.
- Large directory processing can take time; use `mindforge runs show <run_id>` to inspect current progress.
- Full per-source progress UI, partial success UI, and source-level retry UX are future work.
- Advanced config files exist for maintainers and deployment references, but normal users should use workspace + Web Setup.

## Future Work

- Long document chunking with source provenance.
- Per-source progress metadata and clearer partial success UI.
- Source-level retry UX.
- RAG / embedding / semantic merge after separate design review.
- Obsidian plugin or formal-note write only after a separate safety design and explicit authorization.
