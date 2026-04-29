# MindForge v0.5.1 Review — Local Usability

## Summary

v0.5.1 promotes Local Usability / 本地友好使用 to a formal roadmap milestone.
This release does not add a new intelligence layer. It makes the existing
local-first CLI path easier to run, explain, and verify from initialization to
knowledge use.

## Shipped

- Roadmap, progress, backlog, changelog, README, and getting-started docs now
  describe `v0.5.1 Local Usability`.
- Non-Obsidian commands accept user-natural post-command vault overrides such as
  `mindforge next --vault examples/demo-vault`.
- `mindforge commands` now escapes Rich markup so `[[wikilinks]]` displays
  correctly.
- `FakeProvider` now extracts source titles from the rendered prompt variable
  table, so local demo cards are not generated as `Untitled`.
- Fake-provider local smoke does not read `.env`.
- Version metadata is `0.5.1`.

## Local Smoke

All commands below were run against the fictional `examples/demo-vault` or an
equivalent temporary copy:

```bash
mindforge doctor --vault examples/demo-vault
mindforge commands
mindforge next --vault examples/demo-vault
mindforge scan --vault examples/demo-vault
mindforge process --profile fake --limit 1 --vault examples/demo-vault
mindforge approve list --vault examples/demo-vault
mindforge index rebuild --vault examples/demo-vault
mindforge recall --query "agent runtime" --ranking hybrid --explain --vault examples/demo-vault
mindforge review weekly --format markdown --vault examples/demo-vault
mindforge review schedule --days 7 --format markdown --vault examples/demo-vault
mindforge project context my-first-agent --target claude-code --vault examples/demo-vault
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --limit 5
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

Observed results:

- `doctor` reports `active_profile=fake`, local-only telemetry, `.env` presence
  without reading contents, and actionable approve/review hints.
- `commands` lists the local workflow and correctly displays `[[wikilinks]]`.
- `next --vault` works in the natural post-command position.
- `scan` sees demo inbox files with 0 failures.
- `process --profile fake --limit 1` writes an `ai_draft` card with the source
  title inherited from the demo source.
- `approve list` surfaces pending `ai_draft` cards.
- `index rebuild` and hybrid `recall --explain` work locally.
- `review weekly` and `review schedule` produce markdown without LLM calls.
- `project context` produces a Claude Code context pack from human-approved
  cards and project profile metadata.
- Obsidian `doctor`, `scan`, and `links` are read-only.
- Obsidian `stage --dry-run` reports its target path and writes nothing.

## Safety Decisions

- No RAG / embedding.
- No Obsidian plugin.
- No automatic edits to formal Obsidian notes.
- No real LLM calls in the local smoke path.
- No `.env` contents are read by doctor/next/local fake smoke commands.
- No real private vault or private source material was used.
- No automatic approval.
- No remote telemetry or upload path.

## Quality Gate

- Focused local usability tests: `44 passed`.
- Full test suite: `360 passed, 2 skipped`.
- Lint: `ruff check .` clean.
- Release is local only; no push.

## Remaining Risk

- Real non-sensitive dogfooding is still needed; demo vault coverage is not a
  substitute for a user's actual folder conventions and note habits.
- Packaging/install readiness remains a separate v0.5.x patch because default
  prompts/templates/configs still need package-resource handling.

## Recommended Next Step

Proceed to v0.5.2 Packaging / Install Readiness before adding new feature
classes.
