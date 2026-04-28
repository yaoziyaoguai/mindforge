# MindForge v0.5.0 Review — Read-Only Obsidian Binding

## Summary

v0.5.0 adds the minimum Obsidian Binding / Bridge. Obsidian is now a read-only
source of personal knowledge context, not a machine runtime store and not an
automatic vault organizer.

## Shipped

- `ObsidianVaultSourceAdapter`
  - `adapter_name: obsidian_vault`
  - `source_type: obsidian_note`
  - parses frontmatter, tags, aliases, created/updated, `[[wikilinks]]`,
    headings, relative path, and content hash.
- `mindforge obsidian doctor`
- `mindforge obsidian scan`
- `mindforge obsidian links`
- `mindforge obsidian stage`
- config block: `obsidian.vault_path`, `staging_dir`, `review_dir`,
  `include_dirs`, `exclude_dirs`, `read_only`.
- demo Obsidian-style notes under `examples/demo-vault/`.
- regression tests in `tests/test_v0_5_obsidian.py`.

## Safety Decisions

- Real Obsidian notes are never modified by scan/links/doctor.
- `stage` defaults to dry-run; real writes require `--write --confirm`.
- Stage output is restricted to `obsidian.staging_dir` or `obsidian.review_dir`.
- Source notes are not moved, wikilinks are not rewritten, and nothing is
  automatically approved.
- Machine runtime state remains outside formal Obsidian notes.
- No real LLM, no `.env` read, no network, no RAG, no vector DB, no graph DB, no
  Obsidian plugin.

## Smoke

```bash
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault --limit 5
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault \
  --source 02-Knowledge/agent-runtime-observer.md --dry-run
mindforge doctor --vault examples/demo-vault
```

## Remaining Risk

- Real user vaults may have different folder conventions, large files, unusual
  wikilinks, or frontmatter variants.
- The MVP does not yet persist Obsidian scan state.
- Staging templates are fixed and intentionally simple.

## Recommended Next Step

Run read-only dry-run validation on a small non-sensitive Obsidian vault sample.
Use findings to decide between v0.5.1 polish and later v0.6 design work.
