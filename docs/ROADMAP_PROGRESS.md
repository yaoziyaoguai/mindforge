# MindForge — Roadmap Progress（v0.5.0 视角）

> 与 `docs/ROADMAP.md` 互补：本文档关注**完成度盘点**与**下一阶段建议**，
> 不重复列里程碑明细。
>
> 文档入口见 [`DOCS_INDEX.md`](./DOCS_INDEX.md)，版本历史见
> [`CHANGELOG.md`](./CHANGELOG.md)。

## 1. 当前最新版本：**v0.5.0**

- tag: `v0.5.0`（本地）
- HEAD branch: `main`
- 总测试：**357 passed, 2 skipped**（pytest 全绿，ruff clean，无 push）。

## 2. 已完成模块

### 输入（Source Ingestion）
- ✅ `SourceAdapter` 抽象（`src/mindforge/sources/base.py`）
- ✅ `CuboxMarkdownAdapter`、`PlainMarkdownAdapter`
- ✅ `WebClipMarkdownAdapter`、`ChatExportAdapter`（v0.2.4 真实落地）
- ✅ `PdfAdapter`、`DocxAdapter`（v0.2.5 文本最小落地，optional extras）
- ✅ `ObsidianVaultSourceAdapter`（v0.5.0，只读 Markdown / frontmatter / tags / wikilinks / headings）

### 处理（Pipeline）
- ✅ Knowledge Card pipeline（triage / distill / link_suggest / review_questions / action_extraction 五 stage）
- ✅ Provider 层：`fake` / `openai_compatible` / `anthropic_coding_plan`
- ✅ profile + stage routing（M2 契约保留）
- ✅ `ai_draft → human_approved` 双层闸门
- ✅ Prompt 版本化与 `prompts/<task>/manifest.yaml`

### 召回 / 复习
- ✅ `recall`：keyword + BM25（v0.3.0）+ hybrid（v0.3.1）+ weight override（v0.3.2）
- ✅ `index rebuild / status / info`，config_hash drift 检测
- ✅ `review due / mark`（v0.2.0/M4）
- ✅ `review schedule / backlog / stats / weekly`（v0.4.0 + v0.4.1）
- ✅ `review mark --dry-run --note`
- ✅ iCal 本地导出（v0.4.1，**不**接系统日历）

### 项目记忆
- ✅ `project list / context / update-evidence`（含 multi-project，v0.2.2 / v0.2.3）
- ✅ project profile (`30-Projects/<name>.md` frontmatter) + cards 混合
- ✅ Suggested prompt 多 target（claude-code / copilot / codex / generic）

### 产品化
- ✅ `mindforge init`（v0.2.6）—— 一键铺骨架
- ✅ `mindforge approve list/--all/--card/--source-id`（v0.2.6）
- ✅ `mindforge doctor`：Python/平台/配置/vault/optional deps/`.env` ignore/git
  风险/索引/复习 hint
- ✅ `mindforge vault index/links/refresh`（M5.5）
- ✅ `mindforge llm ping/inspect`，`--profile` 临时覆盖
- ✅ 全局 `--vault PATH`、`--debug`、`mindforge version`
- ✅ Local-only telemetry（v0.2.3 / M5.7），`.gitignore` 已防泄漏
- ✅ **`mindforge commands`**（场景化命令地图，v0.4.2）
- ✅ **`mindforge next [--format json]`**（基于 vault 状态的下一步建议，v0.4.2）
- ✅ **`examples/demo-vault/`** + **`docs/SOURCE_ADAPTER_PROTOCOL.md`**（v0.4.2）
- ✅ **`mindforge init --interactive`**（交互式初始化，v0.4.3）
- ✅ **doctor / next polish**（分区、图标、priority、JSON schema v2，v0.4.3）
- ✅ **onboarding smoke 测试固化**（`tests/test_onboarding_smoke.py`，v0.4.3）
- ✅ **`mindforge obsidian doctor/scan/links/stage`**（v0.5.0，只读 binding + staging bridge）

## 3. 部分完成模块

| 模块 | 当前能力 | 缺口 |
|---|---|---|
| PDF/Docx adapter | 文本型 PDF / 普通 docx 段落抽取，`OptionalDependencyError` 友好提示 | 不做 OCR；不解析复杂版式；尚无大文件性能基线 |
| Obsidian Binding | 只读扫描真实 vault Markdown；解析 frontmatter/tags/aliases/wikilinks/headings；stage 默认 dry-run | 还缺小规模非敏感真实 vault dry-run 验证；暂不做 plugin |
| 产品化 onboarding | `init --interactive` + `doctor` + `commands` + `next` + `GETTING_STARTED.md` + demo vault + smoke 测试 | 跨平台窄终端表现需人工观察 |
| Telemetry summary | `telemetry status / summary` 命令，10 字段白名单 | 无远端，未来也不打算上传 |

## 4. 未开始 / 仅 spike 的模块

- ❌ RAG / embedding / 向量检索 / 图数据库（v0.5 不做实现，后续仅在真实缺口出现后 spike）
- ❌ Obsidian plugin（v0.5 不做；先做 CLI/adapter 层 binding）
- ❌ OCR / 扫描件 PDF（明确不做）
- ❌ 云端同步 / 多端推送
- ❌ SM-2 / FSRS 等遗忘曲线算法
- ❌ GUI

## 5. 粗略完成度

> 基于"v0.1 stop rule + v0.2/v0.3/v0.4 scope"主观估算，仅供决策参考。

| 维度 | 完成度 |
|---|---|
| **CLI 本地产品（个人 PKM 加工管线）** | **~92%** —— 主链路 + 召回 + 复习 + 项目上下文 + telemetry + onboarding + Obsidian 只读 binding 都齐；剩真实 dry-run 验证 |
| **完整 Learning Memory OS** | **~50%** —— 缺 Obsidian plugin / RAG 召回 / 多端 / 自动复习调度 / GUI；这是有意为之，不是缺陷 |

## 6. 下一阶段推荐顺序

1. **小规模非敏感样本验证**：只验证只读扫描、frontmatter/tags/`[[wikilinks]]`/目录解析、
   staging/review 输出边界；不跑真实 vault 大规模 dogfooding。
2. **v0.5.1 Obsidian polish**：按 dry-run 反馈补齐 include/exclude 配置、错误文案、窄终端输出。
3. **M5.1 PDF/Docx 完善**：加 fixture 测试、`--strip-empty-pages`、
   `--max-pages` 等控制项；仍**不**做 OCR。
4. **RAG/embedding spike**：仅在 Obsidian binding 和真实反馈证明 BM25/hybrid 不够时再写设计；
   不入主干，不实现 vector/graph。
