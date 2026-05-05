# MindForge Roadmap

This is the canonical roadmap. Historical milestone notes and gate ledgers may
remain in `docs/`, but they are not competing roadmap sources.

## Current State

MindForge can now start real local dogfood on non-sensitive data:

- CLI has a real-data usability path for status, config/workspace diagnosis,
  drafts, explicit approval, and local lexical recall.
- Web first slice provides a localhost-only Local Console for status, setup,
  source/draft visibility, approval confirmation, and recall.
- Fake provider remains the default. Real provider and real Cubox paths are
  opt-in and readiness checks do not call external services.
- True writes must be previewed or explicitly confirmed. `human_approved` is
  produced only by explicit approval.

## Completed Milestones

- Local usability and packaged dogfood path: safe demo, local readiness, package
  assets, and first-run guidance.
- Web first slice: FastAPI + React Local Console over existing MindForge
  service/policy/storage boundaries.
- Real Data CLI Usability: terminal-friendly status/doctor/config/workspace,
  safe draft review, explicit approval, and lexical recall over local data.
- Documentation cleanup: canonical architecture, implementation, roadmap, usage,
  and concise README.
- Strategy and source architecture: SourceAdapter normalization,
  KnowledgeStrategy metadata/discovery, default fake strategy path, and
  declarative custom strategy previews.
- Obsidian binding readiness: read-only scan/link/stage/preflight path for
  disposable or project-only vaults, with formal-note writes still gated.

## Next Recommended Work

1. Real non-sensitive vault dogfood: run the CLI/Web paths against a disposable
   or project-only vault and record friction without using private material.
2. Packaging/install readiness: make first install and `mindforge web` startup
   boring on a fresh machine.
3. CLI/Web polish: improve messages, empty states, and recovery steps observed
   during real dogfood.
4. Keep boundary tests current: add tests only when a safety or architecture
   boundary is at risk of regression.

## Not Current Direction

MindForge is deliberately not pursuing these in the current roadmap:

- RAG, embeddings, vector stores, or semantic merge.
- Obsidian plugin.
- Automatic organization of a real vault.
- Real LLM enabled by default.
- Real Cubox API calls enabled by default.
- Cloud sync, accounts, OAuth, payments, hosting, or multi-user permissions.
- Hidden automatic approval.

## Future Gates

Some future capabilities remain explicitly gated:

- G1 Real Cubox ingestion: sample folder / sample-folder scope, item cap, dry-run-first, and
  no-persist preview before any real API path.
- G2 Real Obsidian formal-note write: diff preview, per-write confirmation,
  backup, rollback, and no automatic vault organization.
- G3 Approval UX: ergonomics only; never timer-based, similarity-based, or
  model-driven auto-approval.
- G4 Custom executable strategy runtime: not active; any future work would need
  an out-of-process sandbox and explicit capability limits.
- G5 RAG / embedding / semantic merge: not active; any future retrieval work
  must remain local-first by default and produce suggestions, not merges.
- G6 Public release / git tag: requires named human authorization; automation
  must not create tags.

There is no tag and no release attached to the current local dogfood closure.

`ROADMAP_COMPLETION_LEDGER.md` remains as a compact guard ledger while tests
still use it to protect these buckets.

Opening any gated capability requires a fresh design review, updated tests, and
explicit user authorization. It is not unlocked by editing this roadmap.
