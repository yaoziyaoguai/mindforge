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

Some archived documents still describe future gates and historical evidence.
They are retained as guard material, not as active roadmap forks:

- `V0_14_FUTURE_GATES.md` - future gated capabilities.
- `ROADMAP_COMPLETION_LEDGER.md` - test-pinned ledger for safety status rows.
- `LOCAL_FIRST_PRIVACY_CONTRACT.md` - privacy and fake-default contract.
- `RFC_G1_CUBOX_REAL_INGESTION.md` - future Cubox HTTP ingestion discussion.

Opening any gated capability requires a fresh design review, updated tests, and
explicit user authorization. It is not unlocked by editing this roadmap.
