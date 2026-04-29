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

## Completed: Local Usability Milestone

v0.5.1 promoted Local Usability / 本地友好使用 to a roadmap milestone. This
closed the first full local product loop on `examples/demo-vault` without
private data, `.env` reads in the fake path, real LLM calls, RAG, embeddings, or
an Obsidian plugin.

Delivered:

- full local smoke across doctor / commands / next / scan / fake process /
  approve list / index / recall / review / project context / Obsidian dry-run;
- user-natural post-command `--vault` compatibility for non-Obsidian commands;
- command-map rendering fix for `[[wikilinks]]`;
- fake provider demo output now inherits source titles instead of producing
  `Untitled` demo cards.

Non-goals:

- no RAG / embedding;
- no Obsidian plugin;
- no automatic formal-note edits;
- no real LLM call;
- no private data dogfooding in the repository;
- no automatic approve or uploaded telemetry.

## Completed: Packaging / Install Readiness

v0.5.2 moved runtime default prompts, templates, and configs into package assets
and resolved them with `importlib.resources`. This makes local installs less
dependent on a development checkout while keeping explicit user path overrides.

Delivered:

- package assets under `src/mindforge/assets/`;
- default process prompts/tracks/template loaded from package resources;
- `mindforge init` default configs copied from package resources;
- explicit `--prompts-dir`, `--tracks`, and `--template` preserved;
- packaged-like tests from a non-repo current directory.

Non-goals:

- no SourceAdapter / SourceDocument / processor / approval / recall redesign;
- no RAG / embedding;
- no Obsidian plugin;
- no live LLM or private vault processing.

## Candidate 1: Install Smoke Polish

Goal: continue polishing real install behavior after v0.5.2.

Possible work:

- Wheel/sdist smoke in a disposable environment.
- Better messages when user-supplied asset paths are wrong.
- Cross-platform path output polish.

## Candidate 2: Real Dogfooding Notes

Goal: collect real usage data after the Obsidian read-only binding boundary is
clear.

Deliverable:

- `docs/DOGFOODING_NOTES.md` or an equivalent local note.
- Concrete friction points: Obsidian scan, onboarding, process, approve, recall,
  review, and project context.
- No private source content in the repository.

## Candidate 3: RAG / Embedding Spike Design

Goal: decide whether lexical BM25/hybrid is insufficient after Obsidian binding
and real usage produce concrete recall gaps.

Design-only deliverable:

- proposed design note: `V0_5_RAG_SPIKE_DESIGN.md`
- Relation to current BM25 index.
- Privacy, storage, and cost analysis.
- Explicit reason why local lexical search is not enough.
- No vector database or graph database implementation in this backlog item.

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
- Automatic Obsidian vault reorganization.
- Automatic formal-note edits, file moves, or wikilink rewrites.
