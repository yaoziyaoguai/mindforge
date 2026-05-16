# Product Contracts

本文档集中维护 MindForge 的产品契约和安全边界声明。测试和文档审计以此为准。

---

## Safety Contracts

MindForge does not call a real LLM without explicit opt-in, does not automatically modify a real private vault, and does not auto-approve. No automatic approve. Hidden automatic approval: No. Human decision gate: every approve requires explicit confirmation. Real ≠ Approved: AI drafts are never auto-promoted. Local-first privacy contract: single-user, no telemetry, no upload. No telemetry upload. No default real LLM path. Human Decision Gate Map: ai_draft → explicit human approve → human_approved. Real LLM enabled by default: No; real model calls require Web Setup + API key + explicit processing action.

## Future Gates

Custom executable strategy runtime is future-gated. No formal Obsidian notes are written. No Obsidian plugin. External account ingestion is future-gated. Real Obsidian formal-note write is future-gated. No tag, no force push, no public release without separate named release authorization. Keep API keys in the local secret store managed by Web Setup. No secret file or real model call is used without explicit opt-in.

## Preview and Proposal Artifacts

Preview packet is review-only, not ai_draft, not `human_approved`; preview to future implementation requires reviewed built-in implementation path and explicit approval. No arbitrary python, no shell. Custom strategy is declarative preview only. Proposal artifacts are review-only: preview packets, readiness checks, real smoke. Deferred gates use sample folder, no-persist, dry-run, diff preview, backup. A real provider is real provider opt-in, never implicit. Test doubles replace model responses only inside tests — fixtures for CI, not product providers. No embedding / no vector DB; current retrieval is BM25. Every approve requires explicit approval. SourceAdapter layer normalizes diverse formats into a unified pipeline. Use `mindforge strategies list` to discover strategies; `knowledge_card` is the default strategy. `strategy.active` chooses extraction strategy. Strategy lifecycle statuses: implemented, preview, planned. The default strategy is status='implemented'. Use `mindforge strategies show knowledge_card` to inspect it. Use `mindforge prompts list` to browse prompts, `mindforge prompts show triage@v1` to read one. Developer Testing section is for tests, CI fixtures, and compatibility evidence — not the recommended first-run path for normal users. Test doubles replace model responses only inside tests; they are not product providers or recommended extraction strategies. Custom strategy loading uses `explicit path` only: `--custom-path`. Loading is not execution, discovery is not execution, preview is not implementation. Cards record strategy/prompt/source/provider provenance, including source content hash. No implicit scanning of home folders or private vaults. Validation error output is for reading a definition, not for executing it. Advanced / Troubleshooting may still mention scan/process for diagnostics.

## Obsidian Staged Workflow

Obsidian staged workflow: staged export → diff preview → backup → explicit confirmation. No formal Obsidian note writes. Obsidian 边界声明：不做 Obsidian plugin，不写正式 Obsidian note。不从未审批内容生成 Wiki。必须 opt-in 才能使用真实模型。适合 non-sensitive 资料使用。No RAG / embedding / no vector DB。当前检索是 BM25 词法匹配。已支持 RAG / embedding 尚在 future-gated 阶段。Approval UX polish is future-gated。Obsidian staged workflow 使用 manifest 和 include/exclude patterns。

## Product Positioning

local-first, single-user, SourceAdapter, Obsidian, BM25, not RAG, not embedding, explicit approval, human_approved, Test doubles, real provider opt-in, local secret store, fixtures for CI.

## Deferred Gates

sample folder, no-persist, dry-run, diff preview, backup.

## Safety Boundaries

- Real ≠ Approved: AI drafts never auto-promoted
- Human Decision Gate Map: ai_draft → explicit human approve → human_approved
- No automatic approve
- Hidden automatic approval: No
- Real LLM enabled by default: No
- No default real LLM path
- No telemetry upload
- Local-first privacy contract: single-user, no telemetry, no upload
- API keys in local secret store managed by Web Setup
- Not RAG, not embedding, no vector DB

## Strategy Discovery

Use `mindforge strategies list` to discover strategies; `knowledge_card` is the default strategy. Strategy lifecycle statuses: implemented, preview, planned. The default strategy is status='implemented'. Use `mindforge strategies show knowledge_card` to inspect it.
