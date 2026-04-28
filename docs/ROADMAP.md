# MindForge Roadmap

This roadmap tracks product direction and explicit non-goals. Completed release details are summarized in [CHANGELOG.md](./CHANGELOG.md); current completion state is in [ROADMAP_PROGRESS.md](./ROADMAP_PROGRESS.md).

## Current Position

Current version: **v0.4.3**.

MindForge v0.x is a local-first CLI for personal learning memory:

- local source ingestion through adapters;
- five-stage LLM processing with safe fake default;
- explicit human approval;
- local lexical/hybrid recall;
- local review planning;
- project context packs;
- local-only telemetry;
- CLI onboarding and demo vault.

## Near-Term Priority

1. **Dogfooding**
   - Use MindForge for 1-2 weeks with non-sensitive personal material.
   - Record friction in onboarding, command discoverability, review workflow, and recall quality.
   - Avoid large features until real usage data exists.

2. **CLI Polish**
   - Fix issues found during dogfooding.
   - Keep errors actionable and Chinese-localized where user-facing.
   - Keep docs short and navigable.

3. **Design-Only v0.5 Spikes**
   - Obsidian plugin design.
   - RAG/embedding design.
   - No implementation until dogfooding shows a real need.

## Future Candidate Work

See [M5_BACKLOG.md](./M5_BACKLOG.md) for current spike candidates. The active future set is intentionally small:

- Obsidian plugin spike.
- RAG / embedding spike.
- PDF/docx performance baselines.
- More onboarding and cross-platform terminal polish.

## Explicit Non-Goals For v0.x

- No OCR.
- No remote telemetry.
- No cloud sync.
- No automatic approval.
- No background daemon.
- No system calendar or notification integration.
- No SM-2 / FSRS automation.
- No RAG/embedding in mainline without a separate design and review.

## Stable Architecture References

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [SECURITY.md](./SECURITY.md)
- [MINDFORGE_PROTOCOL.md](./MINDFORGE_PROTOCOL.md)
- [SOURCE_ADAPTER_PROTOCOL.md](./SOURCE_ADAPTER_PROTOCOL.md)
- [LLM_PROVIDER_CONFIG.md](./LLM_PROVIDER_CONFIG.md)

## When To Update This Roadmap

Update this file when a future direction changes. Use [CHANGELOG.md](./CHANGELOG.md) for completed version history and `docs/archive/` for detailed historical reviews.
