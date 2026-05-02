# V0.13 Real Ingestion Deferred Gates (Cubox / Obsidian)

> 本文档列出 **真实 Cubox API ingestion** 与 **真实 Obsidian vault
> 写入** 的启用前置条件。当前 v0.13 Stage 1 **不实现** 任何此类真实
> ingestion / 写入路径; 本文仅作为未来启动这些方向的安全门 (gate)
> 清单。

## 1. 当前状态

| 维度 | 状态 |
| --- | --- |
| 真实 Cubox API ingestion | **未启用** |
| 真实 Obsidian vault 写入 | **未启用** |
| 真实 home 目录扫描 | **永久禁止** (违反 local-first privacy contract §5) |
| Cubox dry-run / preview presenter | 已存在 (`src/mindforge/cubox_preview_presenter.py`, `cubox_dryrun_presenter.py`) — 仅用 fake / synthetic 输入 |
| Obsidian preview / dry-run | 已存在 (`src/mindforge/obsidian_workflow.py` 等) — 仅用显式 vault 路径参数 |

## 2. 共同启用前置 (适用于 Cubox 与 Obsidian)

- 显式 opt-in flag (例: `--allow-real`), 默认 off;
- 输出仅为 `preview_packet` / `ai_draft_preview` 类型 artifact;
- 输出 **不能** 升级为 `human_approved` (由 ApprovalService 单一路径
  保护);
- 不写入 repo 的任何 fixture / docs / tests / commit;
- 不打印任何 secret / api token;
- 失败 fall-back 到 fake / synthetic 路径, 不重试放大;
- tests 必须证明 "未传 opt-in flag 时绝不真实调用"。

## 3. Cubox 真实 ingestion 专属门

启用真实 Cubox API ingestion **必须同时** 满足:

1. **测试账号**: 使用专门的 test/dogfooding Cubox 账号, 不能使用
   用户主账号; 账号内只允许 synthetic / non-sensitive 内容;
2. **范围限定**: 单次 ingestion 限定到 sample folder (例如 "MindForge
   Test"); 不允许全库拉取;
3. **数量上限**: 单次 ingestion item 数量硬上限 (例如 ≤ 10);
4. **不持久化原文 (no-persist)**: 真实 Cubox 内容仅在内存中过 preview
   pipeline, 不落盘到 repo / cards / vault;
5. **不索引**: 不为真实 Cubox 内容建立任何 embedding / RAG / lexical
   index 持久化条目;
6. **审计输出**: ingestion 完成后输出 `{count, folder, no_persist:
   True, no_index: True, no_secret_print: True}` 摘要;
7. **回退命令**: 提供一键清理 — 删除任何过程中临时落盘文件;
8. **opt-in flag**: 例如 `mindforge cubox sync --allow-real
   --folder=<test-folder> --max-items=N`, 默认 off。

未满足以上 **任意一条** 时, 真实 Cubox ingestion 不允许实施。

## 4. Obsidian 真实 vault 写入专属门

启用真实 Obsidian vault 写入 **必须同时** 满足:

1. **显式 vault 路径**: 必须由 CLI 参数显式传入, 不允许 `Path.home()`
   或环境变量隐式发现;
2. **dry-run 优先**: 写入前必须先输出 dry-run preview (已有
   `obsidian_workflow.py` 提供此能力);
3. **单文件粒度**: 一次写入仅允许单一 markdown 文件; 批量写入需要
   逐文件 `--allow-write` 确认;
4. **不覆盖现有文件**: 默认 fail-if-exists; 显式 `--overwrite` flag
   且 dry-run 已展示 diff 后才允许;
5. **写入内容必须是 `human_approved` artifact**: 真实 LLM ai_draft 不
   允许直接写 vault — 必须先经 `mindforge approve` 升格为
   `ApprovedKnowledgeCard`;
6. **审计输出**: `{written: True, vault, file, bytes, no_overwrite:
   True}` 摘要; 不打印文件内容;
7. **回退**: 写入前生成同名 `.bak` 备份 (若文件已存在);
8. **opt-in flag**: 例如 `mindforge obsidian write --allow-write
   --vault=<path> --file=<name>`, 默认 off。

未满足以上 **任意一条** 时, 真实 Obsidian 写入不允许实施。

## 5. 与 v0.13 Stage 1 的关系

v0.13 Stage 1 仅交付:

- 真实 LLM provider opt-in 路径 (`provider_readiness.py` +
  `real_smoke.py` + `mindforge provider {readiness,smoke}` CLI);
- 上述路径 **不触发** Cubox 真实 API, 也 **不写** Obsidian vault;
- 本文档作为 deferred gates 的 canonical 清单, 未来若启动 Cubox / Obsidian
  真实路径, 必须先实现 §3 / §4 全部 gates 才能合入。

## 6. 与隐私契约的关系

本文档是 `docs/LOCAL_FIRST_PRIVACY_CONTRACT.md` §9 "推迟项" 的展开;
两者出现矛盾时, 以隐私契约为准。
