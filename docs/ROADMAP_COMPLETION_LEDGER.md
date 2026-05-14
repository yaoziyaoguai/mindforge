# Roadmap Completion Ledger

This compact guard ledger is intentionally the only retained roadmap-adjacent
document besides `ROADMAP.md`. Tests keep it because it protects future-gate
status buckets without requiring dozens of historical milestone files.

## Status Buckets

| Bucket | Meaning | Who can move it |
| --- | --- | --- |
| `available` | Safe local capability is usable now | Normal contribution flow |
| `real-opt-in` | Real provider path exists but requires explicit opt-in | Named human authorizer |
| `review-only` | Produces inspectable artifacts, not approved knowledge | Normal contribution flow |
| `pushed` | Implemented, committed, and validated in the local branch history | Normal contribution flow |
| `local-complete` | Finished locally but not pushed | Current maintainer |
| `future-gated` | Requires fresh design review and explicit human authorization | Named human authorizer |
| `release-gated` | Requires named release authorization before tag/release | Named human authorizer |
| `forbidden` | Conflicts with MindForge identity or safety model | Nobody |

## Current Guarded Gates

| Capability | Bucket | Boundary |
| --- | --- | --- |
| External account ingestion | `future-gated` | sample folder, item cap, dry-run-first, no-persist preview |
| Real Obsidian formal-note write | `future-gated` | diff preview, backup, rollback, per-write confirmation |
| Approval UX polish | `future-gated` | ergonomics only; no timer/model/similarity auto-approval |
| Custom executable strategy runtime | `future-gated` | not active; declarative custom strategies only |
| RAG / embedding / semantic merge | `future-gated` | not active; lexical recall remains current path |
| Public release / git tag | `release-gated` | no automation may create a tag |
| Auto-approve / generated `human_approved` | `forbidden` | only explicit human approval can promote a draft |

No tag and No release are part of the current local workflow closure. Public
tags or release artifacts require a separate named release authorization.

## Completion Claim

MindForge is clean enough for long-term local use on non-sensitive or
project-only data. The current safe path and product direction are documented in
`README.md`.

Opening a future gate requires updating `README.md`, this ledger, and the
boundary tests in the same change.

## Post-release Technical Debt

这些条目不是当前 release blocker：它们要么需要较大架构拆分，要么会改变
processing / Web UX 的产品语义。release 前只保留现有 characterization tests
和边界说明；release 后必须按单项设计、单项测试、单项 PR 推进，不能混成
一个大改。

| Item | Release-preflight status | Release-after action |
| --- | --- | --- |
| `config.py` split | First low-risk slice done: provider timeout/retry defaults live outside config schema. Dataclass/schema/loader remain in place because moving them would touch many core imports. | Next split pure validation helpers, then schema vs loader; each step must preserve `tests/test_config.py` characterization coverage. |
| `web_config_service.py` split | First low-risk slice done: Web Setup secret handling is isolated from config view/write. Reader/writer/readiness stay in the service to avoid a release-preflight Web Setup rewrite. | Split `WebConfigReader` / `WebConfigWriter` / `WebConfigReadinessPresenter` only after API response contract tests are in place. |
| long document chunking | 会改变 source splitting、prompt budget、card provenance 与 merge 语义，是新 processing 能力。 | 先写设计文档和 fixtures，再实现 per-source chunk provenance 与用户可见说明。 |
| per-source progress | 当前 run 已展示 provider call progress；完整 per-source progress 需要扩展 run event schema 和 Web/CLI 展示。 | 增加 source-level stage events 与 batch position metadata，先覆盖 CLI `runs show`，再扩展 Web。 |
| partial success UI | 需要定义 batch succeeded-with-errors 的产品语义，避免误导成完全成功或完全失败。 | 先设计状态枚举和 copy，再用 fixture run logs 做 Web/CLI characterization tests。 |
| source-level retry UX | 当前 provider timeout/retry 已有界；source-level retry 涉及 idempotency、already_processed、failed source selection。 | 先定义 retry target 与 dedupe 规则，再实现单 source retry command / Web action。 |
