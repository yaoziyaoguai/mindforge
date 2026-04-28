# MindForge Security And Safety Contract

MindForge handles personal learning material. The default behavior must stay local, reviewable, and conservative.

## Hard Rules

1. Do not read or print `.env` contents in doctor/next/status-style commands.
2. Do not print API keys, bearer tokens, authorization headers, raw prompts, or completions in user-facing output.
3. Do not call real LLMs unless the user explicitly selects a real profile and validates it.
4. Do not upload telemetry. Telemetry is permanently local-only in v0.x.
5. Do not modify raw files under `00-Inbox/`.
6. Do not auto-approve AI output. `human_approved` requires explicit user action.
7. Do not index raw source text. Recall indexes Knowledge Card safe fields and whitelisted sections only.
8. Do not do OCR. Textless scanned PDFs fail with a clear error.
9. Do not add a background daemon, system notification, email, or calendar integration in v0.x.
10. Do not add remote sync or cloud storage.

## Default Safe Path

- `active_profile=fake`
- local `.mindforge/state.json`
- local `.mindforge/runs/*.jsonl`
- local `.mindforge/telemetry.jsonl`
- local `.mindforge/index/bm25.json`
- Knowledge Cards default to `status: ai_draft`

## Human Approval

`mindforge process` can produce `ai_draft` cards only. `mindforge approve --card`, `--source-id`, or explicitly confirmed batch approval is the only route into `human_approved`.

Detailed contract: [M3_HUMAN_APPROVAL_PROTOCOL.md](./M3_HUMAN_APPROVAL_PROTOCOL.md).

## Telemetry

Telemetry records command-level metadata only. It must never contain card body, raw source text, query text, title text, prompt text, completion text, API keys, or project names.

Detailed contract: [M5_7_TELEMETRY_PROTOCOL.md](./M5_7_TELEMETRY_PROTOCOL.md).

## Recall Indexing

BM25/hybrid recall is local. It indexes safe Knowledge Card frontmatter fields plus approved body sections such as `AI Summary`, `Action Items`, `Principles`, and `Known Risks`. It must not index `Source Excerpt`, `Human Note`, raw source files, runs, state, or `.env`.

Detailed contract: [M5_4_LEXICAL_RECALL_PROTOCOL.md](./M5_4_LEXICAL_RECALL_PROTOCOL.md).

## Provider Configuration

The fake provider is safe and offline. Real providers require explicit profile selection and `mindforge llm ping`.

Provider setup: [LLM_PROVIDER_CONFIG.md](./LLM_PROVIDER_CONFIG.md).

## Testing Expectations

Safety-sensitive changes should run the full test suite and preserve anti-leak assertions. See [TESTING.md](./TESTING.md).
