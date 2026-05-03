# MindForge Changelog

This file summarizes user-visible and architecture-relevant changes. Detailed historical reviews live in `docs/archive/`.

## v0.13 Stage 4 — Controlled Dogfood Preflight (local)

- 新增 `mindforge dogfood preflight <path>` 子命令; 静态分类 input
  路径 (synthetic / non_sensitive_local / private_real_data_forbidden /
  obsidian_vault_forbidden / home_scan_forbidden / path_does_not_exist),
  组合 provider readiness, 输出 allowed/refused 决策。
- 新增 `src/mindforge/dogfood_safety.py` 纯模块: 不读 input 内容、
  不调用 LLM、不写 vault、不会产生 `human_approved`; AST 守卫纳入
  现有 `_GUARDED` 列表。
- 新增 `tests/test_v013_stage4_dogfood_preflight.py` (14 cases) 覆盖
  分类规则、Obsidian / home / 不存在路径拒绝、CLI exit code、
  无 LLM/无文件读取断言。
- 新增 `docs/V0_13_DOGFOOD_PREFLIGHT.md` 工作流文档。
- 默认仍然 fake-safe; 真实 provider 仍是 explicit opt-in。

## v0.13 Stage 3 — Real LLM Smoke Closure (local)

- 修复 P1 接口错配: `real_smoke` 之前用 `.complete/.chat` 而真实
  `LLMProvider` ABC 是 `.generate(LLMRequest) -> LLMResult`; 修正为
  严格走标准契约, 测试改用真正符合契约的 stub。
- 修复 `provider_cli` 未走 `.env` 注入的不一致: 新增
  `_load_cfg_with_dotenv` 与 `cli.py::_load_cfg` 一致语义 (silent /
  non-overriding / once-only)。
- `mindforge provider smoke` 新增 `--profile` 临时覆盖 active_profile,
  与 `llm ping --profile` 行为一致, 不写 yaml。
- audit-trail 新增 `tokens_in` / `tokens_out` / `latency_ms`;
  `ProviderError` 单独捕获, message 不回显。
- AST 守卫 `_PER_FILE_ALLOWLIST` 显式允许 `provider_cli` 使用
  `env_loader` (其它两个守卫文件仍禁止)。
- 新增 docs/V0_13_REAL_LLM_SMOKE_SAFETY.md 完整工作流。
- **真实 LLM smoke 已端到端运行成功** (DashScope Coding Plan,
  synthetic prompt, 44/72 tokens, 1434ms); 输出停留在
  `ai_draft_preview`, `human_approved=False`, `written=False`。

## v0.13 Stage 1 — Real-Capable Opt-in Readiness (local)

- Added `mindforge provider readiness` (`--format text|json`) and
  `mindforge provider smoke [--allow-real]` 命令; both 默认安全, 拒绝
  在未显式 opt-in 的前提下接触真实 provider。
- Added `src/mindforge/provider_readiness.py`: 纯数据 readiness 报告
  (presence-only env 检查, 永远不返回 secret value)。
- Added `src/mindforge/real_smoke.py`: 受 `allow_real` + active profile
  ≠ fake + api_key 在环境中三重 gate 控制的合成 smoke; 输出仅作为
  `ai_draft_preview`, 永远不会变成 `human_approved`, 永远不写入 vault。
- Added canonical privacy doc
  [docs/LOCAL_FIRST_PRIVACY_CONTRACT.md](LOCAL_FIRST_PRIVACY_CONTRACT.md)
  (v2: fake-default + real-opt-in)。
- Added [docs/V0_13_INDUSTRY_PATTERN_MAP.md](V0_13_INDUSTRY_PATTERN_MAP.md)
  和 [docs/V0_13_REAL_INGESTION_DEFERRED_GATES.md](V0_13_REAL_INGESTION_DEFERRED_GATES.md);
  Cubox / Obsidian 真实接入仍 deferred。
- Capability matrix §8 新增 real-opt-in 矩阵 (与 §6 "Excluded" 一致, §6 不变)。
- v0.13 Stage 2 (consolidation): readiness JSON 输出 + 默认 fake profile
  完整性测试 + ping/readiness 一致性测试 + matrix §6/§8 一致性测试。
- 不变: SourceAdapter / SourceDocument / processor / approval / recall /
  Obsidian write / RAG / embedding / Cubox real ingestion / custom strategy
  runtime 默认全部禁用; 默认路径仍是 fake provider。

## v0.5.2

- Added Packaging / Install Readiness design documentation.
- Bundled runtime default assets under `src/mindforge/assets/`: prompts,
  Knowledge Card template, and default configs.
- Resolved default runtime assets with `importlib.resources` so packaged
  installs and non-repo current directories do not depend on repo-root
  `prompts/`, `templates/`, or `configs/`.
- Preserved explicit user overrides for `--prompts-dir`, `--tracks`, and
  `--template`.
- Updated `mindforge init` to copy default configs from package assets rather
  than assuming a source checkout.
- Clarified relative `state.workdir` resolution so copied configs do not infer a
  fake repo root from their file location.
- Kept SourceAdapter, SourceDocument, processor, approval, and recall
  architecture unchanged; no RAG, embedding, Obsidian plugin, live LLM, private
  vault, or new heavy dependency was added.

## v0.5.1

- Promoted Local Usability / 本地友好使用 to a formal roadmap milestone.
- Ran the full `examples/demo-vault` local user path: doctor, commands, next,
  scan, fake process, approve list, index rebuild, hybrid recall, review weekly,
  review schedule, project context, and Obsidian doctor/scan/links/stage
  dry-run.
- Added compatibility for post-command `--vault`, so commands such as
  `mindforge next --vault examples/demo-vault` work as users naturally type
  them.
- Fixed `mindforge commands` Rich markup escaping so `[[wikilinks]]` is shown
  correctly.
- Improved fake provider demo output so generated cards inherit the rendered
  source title instead of becoming `Untitled`.
- Tightened local command boundaries so fake-provider local smoke does not read
  `.env`.
- Kept v0.5.1 explicitly out of RAG / embedding / Obsidian plugin work; no real
  LLM calls, private data handling, automatic approve, formal-note edits, or
  uploaded telemetry were added.

## v0.5.0

- Added read-only `ObsidianVaultSourceAdapter` with `source_type: obsidian_note`.
- Added `mindforge obsidian doctor`, `scan`, `links`, and `stage`.
- Added Obsidian config for vault path, staging/review dirs, include/exclude dirs, and `read_only`.
- Added staging bridge with dry-run default and `--write --confirm` guard.
- Kept Obsidian runtime/state/cache/index/log boundaries explicit: no formal-note edits, file moves, wikilink rewrites, RAG, vector DB, graph DB, or plugin.

## v0.4.3

- Added `mindforge init --interactive`.
- Polished `doctor` and `next` output with sections, status markers, priorities, and JSON schema `version=2`.
- Chinese-localized more user-facing errors.
- Added executable onboarding smoke coverage for `examples/demo-vault/`.

## v0.4.2

- Added `mindforge commands`.
- Added `mindforge next`.
- Formalized [SourceAdapter Protocol](./SOURCE_ADAPTER_PROTOCOL.md).
- Added `SourceDocument.adapter_name`.
- Added fictional `examples/demo-vault/`.

## v0.4.1

- Added iCal export for review schedules.
- Added weekly review reports.
- Added first versions of `GETTING_STARTED.md`, `USER_GUIDE.md`, and `ROADMAP_PROGRESS.md`.

## v0.4.0

- Added review scheduling MVP: schedule, backlog, stats, and `review mark --dry-run --note`.

## v0.3.x

- Added local BM25 recall.
- Added local hybrid ranking.
- Added configurable BM25/hybrid weights and config drift detection.
- Added index info JSON and recall explain improvements.

## v0.2.x

- Added review due, recall, and project context.
- Added multi-project context and project evidence block updates.
- Added local-only telemetry.
- Added WebClip and ChatExport adapters.
- Added PDF/docx text adapters with lazy optional dependencies and no OCR.
- Added `mindforge init`, approval workflow polish, doctor, and global `--vault`.

## v0.1.x

- Built the main source ingestion and five-stage processing pipeline.
- Added fake, OpenAI-compatible, and Anthropic-compatible provider layers.
- Added Knowledge Card writing and explicit human approval safety gate.
- Established the core protocol, state, runs, and safety boundaries.
