# MindForge Future Backlog

This file tracks future candidates only. Completed work is summarized in
[CHANGELOG.md](./CHANGELOG.md) and detailed in release reviews.

## Completed: Obsidian Binding / Bridge

v0.5.0 connected MindForge to Obsidian as read-only personal knowledge context.
See [OBSIDIAN_BINDING.md](./OBSIDIAN_BINDING.md) and
[V0_5_OBSIDIAN_BINDING_REVIEW.md](./V0_5_OBSIDIAN_BINDING_REVIEW.md).

Delivered:

- read-only Markdown scan;
- frontmatter, tags, aliases, `[[wikilinks]]`, headings, and directory parsing;
- `ObsidianVaultSourceAdapter` in the SourceAdapter system;
- staging/review output boundary;
- Clear rule that machine indexes, caches, logs, and intermediate state stay out
  of formal notes.

Non-goals:

- no automatic vault organization;
- no formal-note edits;
- no file moves;
- no wikilink rewrites;
- no plugin implementation in this step;
- no large-scale real-vault dogfooding before the read-only boundary is tested.

## Candidate 1: Real Dogfooding Notes

Goal: collect real usage data after the Obsidian read-only binding boundary is
clear.

Deliverable:

- `docs/DOGFOODING_NOTES.md` or an equivalent local note.
- Concrete friction points: Obsidian scan, onboarding, process, approve, recall,
  review, and project context.
- No private source content in the repository.

## Candidate 2: RAG / Embedding Spike Design

Goal: decide whether lexical BM25/hybrid is insufficient after Obsidian binding
and real usage produce concrete recall gaps.

Design-only deliverable:

- proposed design note: `V0_5_RAG_SPIKE_DESIGN.md`
- Relation to current BM25 index.
- Privacy, storage, and cost analysis.
- Explicit reason why local lexical search is not enough.
- No vector database or graph database implementation in this backlog item.

## Candidate 3: PDF / Docx Baselines

Goal: make current lightweight document adapters more predictable without expanding scope.

Possible work:

- Fixture coverage for larger text PDFs and docx files.
- Performance baseline.
- Better error messages for encrypted or malformed files.
- Still no OCR, table reconstruction, or layout restoration.

## Candidate 4: CLI Polish From Dogfooding

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
- Automatic Obsidian vault reorganization.
- Automatic formal-note edits, file moves, or wikilink rewrites.
