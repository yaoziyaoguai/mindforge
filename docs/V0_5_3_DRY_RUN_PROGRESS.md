# MindForge v0.5.3 Dry-run Progress

## Goal

Make Obsidian dry-run safer for disposable, non-sensitive vault copies. This is
local dogfooding polish, not a new feature class.

## Product Fixes

- `obsidian stage` still defaults to dry-run and now prints a preview report:
  source file, proposed path, action type, skipped reason, risk warning, and
  next command suggestion.
- Dry-run reports missing source, directory source, non-Markdown source, and
  parse failures without writing files.
- `obsidian scan` and `obsidian links` now give clearer empty-vault messages.
- Bad single-note frontmatter is skipped with a safe path/error summary instead
  of crashing the whole scan.

## Safe Trial

Use only a disposable, non-sensitive vault copy:

```bash
mindforge obsidian doctor --vault examples/demo-vault
mindforge obsidian scan --vault examples/demo-vault
mindforge obsidian links --vault examples/demo-vault
mindforge obsidian stage --vault examples/demo-vault \
  --source 02-Knowledge/agent-runtime-observer.md --dry-run
```

## Non-goals

- No RAG / embedding.
- No Obsidian plugin.
- No real LLM call.
- No `.env` read in Obsidian dry-run commands.
- No automatic approve.
- No formal note edits, file moves, or wikilink rewrites.
