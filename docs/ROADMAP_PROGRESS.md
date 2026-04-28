# MindForge — Roadmap Progress（v0.4.2 视角）

> 与 `docs/ROADMAP.md` 互补：本文档关注**完成度盘点**与**下一阶段建议**，
> 不重复列里程碑明细。

## 1. 当前最新版本：**v0.4.2**

- tag: `v0.4.2`
- HEAD branch: `main`
- 总测试：**339 passed, 2 skipped**（pytest 全绿，ruff clean，无 push）

## 2. 已完成模块

### 输入（Source Ingestion）
- ✅ `SourceAdapter` 抽象（`src/mindforge/sources/base.py`）
- ✅ `CuboxMarkdownAdapter`、`PlainMarkdownAdapter`
- ✅ `WebClipMarkdownAdapter`、`ChatExportAdapter`（v0.2.4 真实落地）
- ✅ `PdfAdapter`、`DocxAdapter`（v0.2.5 文本最小落地，optional extras）

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

## 3. 部分完成模块

| 模块 | 当前能力 | 缺口 |
|---|---|---|
| PDF/Docx adapter | 文本型 PDF / 普通 docx 段落抽取，`OptionalDependencyError` 友好提示 | 不做 OCR；不解析复杂版式；尚无大文件性能基线 |
| Obsidian 友好度 | `vault index/links` 自动维护 `_index.md` / `_link_candidates.md` | 没有 Obsidian 插件；没有批量双链重写 |
| 产品化 onboarding | `init` + `doctor` + `commands` + `next` + `GETTING_STARTED.md` + demo vault | 错误信息中文化未全覆盖；没有交互式 `init --interactive` |
| Telemetry summary | `telemetry status / summary` 命令，10 字段白名单 | 无远端，未来也不打算上传 |

## 4. 未开始 / 仅 spike 的模块

- ❌ RAG / embedding / 向量检索（明确不做主干）
- ❌ Obsidian plugin（明确不做）
- ❌ OCR / 扫描件 PDF（明确不做）
- ❌ 云端同步 / 多端推送
- ❌ SM-2 / FSRS 等遗忘曲线算法
- ❌ GUI

## 5. 粗略完成度

> 基于"v0.1 stop rule + v0.2/v0.3/v0.4 scope"主观估算，仅供决策参考。

| 维度 | 完成度 |
|---|---|
| **CLI 本地产品（个人 PKM 加工管线）** | **~85%** —— 主链路 + 召回 + 复习 + 项目上下文 + telemetry + onboarding 都齐；剩 onboarding 体验细节、错误中文化、文档打磨 |
| **完整 Learning Memory OS** | **~45%** —— 缺 Obsidian 插件 / RAG 召回 / 多端 / 自动复习调度 / GUI；这是有意为之，不是缺陷 |

## 6. 下一阶段推荐顺序

1. **真实 dogfooding 1–2 周**（强烈建议）：用 v0.4.1 把自己 vault 跑起来；
   现在功能/契约已经到位，再加更多代码不如先验证产品假设。
2. **CLI polish 收尾**：错误信息中文化全覆盖、`init --interactive` 交互式
   向导、`doctor --fix` 自动修小问题。
3. **M5.1 PDF/Docx 完善**：加 fixture 测试、`--strip-empty-pages`、
   `--max-pages` 等控制项；仍**不**做 OCR。
4. **M6 RAG/embedding spike**：仅 `docs/POC`，不入主干，决策"是否值得做"。
5. **Obsidian plugin spike**：同样仅 docs，不入仓库；先评估"能否只做读取插件
   而不动 vault"。
