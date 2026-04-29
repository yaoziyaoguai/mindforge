# v0.6.3 Recall / Search UX

## Goal

Make local recall easier to understand: what matched, why it matched, whether the index is trustworthy, and what to do next.

## Recommended Usage

```bash
mindforge recall --query "agent" --vault examples/demo-vault
mindforge recall --query "agent" --explain --vault examples/demo-vault
mindforge recall --query "missing topic" --vault examples/demo-vault
mindforge index rebuild --vault examples/demo-vault
```

## Local Lexical Boundary

Recall remains local BM25 / hybrid lexical search over safe Knowledge Card fields. It does not read source originals, call an LLM, upload data, read `.env`, use RAG, or use embeddings.

## Non-goals

- No RAG / embedding implementation.
- No real LLM call.
- No automatic approve.
- No writes to real Obsidian notes.
- No telemetry upload.
