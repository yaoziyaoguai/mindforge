# MindForge Future Backlog

This file tracks future candidates only. Completed v0.2-v0.4 work is summarized in [CHANGELOG.md](./CHANGELOG.md) and detailed in `docs/archive/`.

## Candidate 1: Real Dogfooding Notes

Goal: collect 1-2 weeks of real usage data before adding architecture-heavy features.

Deliverable:

- `docs/DOGFOODING_NOTES.md` or an equivalent local note.
- Concrete friction points: onboarding, scan/process, approve, recall, review, project context.
- No private source content in the repository.

## Candidate 2: Obsidian Plugin Design

Goal: decide whether an Obsidian plugin is useful after the CLI loop is proven.

Design-only deliverable:

- proposed design note: `V0_5_OBSIDIAN_PLUGIN_DESIGN.md`
- Minimal read-only surface.
- Clear boundary with existing `vault index/links`.
- No implementation until separately approved.

## Candidate 3: RAG / Embedding Spike Design

Goal: decide whether lexical BM25/hybrid is insufficient for real usage.

Design-only deliverable:

- proposed design note: `V0_5_RAG_SPIKE_DESIGN.md`
- Relation to current BM25 index.
- Privacy, storage, and cost analysis.
- Explicit reason why local lexical search is not enough.

## Candidate 4: PDF / Docx Baselines

Goal: make current lightweight document adapters more predictable without expanding scope.

Possible work:

- Fixture coverage for larger text PDFs and docx files.
- Performance baseline.
- Better error messages for encrypted or malformed files.
- Still no OCR, table reconstruction, or layout restoration.

## Candidate 5: CLI Polish From Dogfooding

Goal: patch real friction rather than imagined features.

Possible work:

- Narrow terminal output polish.
- More actionable `doctor` hints.
- Better command examples.
- Safer defaults for new vaults.

## Permanent Non-Goals

- OCR.
- Remote sync.
- Cloud telemetry.
- Automatic approve.
- Background daemon.
- System notifications.
- Email reminders.
- SM-2 / FSRS automation.
