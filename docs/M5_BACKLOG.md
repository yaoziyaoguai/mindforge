# MindForge · M5 Backlog（拆解 ≠ 实现）

> 本文是 **backlog 拆解**，不是实现承诺；每条都列出"先不做什么"。
> v0.2.x 在出 v0.3.0 之前不应进入任何 M5 子项，避免又走回大而全。

---

## M5.1 · PDF / Docx adapter（v0.3.x 候选）

- **目标**：扩展 `SourceAdapter` 抽象的真实实现，让 `00-Inbox/PDFs/` 与
  `00-Inbox/Docs/` 真正能产出 `SourceDocument`。
- **不做**：OCR、复杂表格抽取、Word 复杂样式、跨页脚注合并、扫描件图像识别。
- **验收**：
  - 一份 5–20 页 PDF / 一份普通 docx 都能被 `mindforge scan` 看到，
    `process` 时通过 fake LLM 可走完 5 stage；
  - 解析层失败不污染 state.json（状态归 `failed` + `error_message`）；
  - PDF 解析依赖（如 `pypdf` / `pdfplumber`）必须 lazy import，未安装时
    `mindforge llm ping` / 其他无关命令仍能运行。
- **风险**：PDF 千差万别；切勿被一份"难解析的 PDF"逼成 OCR 工程。
- **优先级**：⭐⭐⭐（个人 PKM 真实价值高）

---

## M5.2 · WebClip / ChatExport adapter

- **目标**：覆盖 Obsidian Web Clipper / MarkDownload 网页存档；
  ChatGPT / Claude 对话导出（json / md）。
- **不做**：浏览器插件本身、对话流的完整重放、token 级别的 cost 统计。
- **验收**：
  - WebClip：保留 `source_url` / `captured_at`；
  - ChatExport：保留 turn 级 metadata，但 `raw_text` 仍是统一 markdown；
  - 与 v0.2.0 的 cubox / plain markdown 共存，无 if/else 散布业务模块。
- **风险**：ChatExport 的 prompt 内容可能含 secret，必须在 adapter 层做
  **入口脱敏**（默认抹去 `sk-` / `Bearer` 等 pattern），不进 raw_text。
- **优先级**：⭐⭐（Web 存档常用；ChatExport 可后置）

---

## M5.3 · Better project context / prompt pack

> ✅ **已落地于 v0.2.2**（[复盘](./V0_2_2_REVIEW.md) · [协议](./M5_3_PROJECT_CONTEXT_PROTOCOL.md)）

- **目标**：在 v0.2.1 已有 `project context` 基础上，再加：
  - 多 project 联合上下文（`mindforge project context a b c`）；
  - 按 project 自动维护 `30-Projects/<name>.md` 的"已审核证据栏"
    （**追加** + 幂等，不覆盖人手写内容）；
  - 一键导出可粘贴到 Claude Code / Copilot 的 `.context.md`。
- **v0.2.2 已交付**：
  - 单 project 的 target-aware context pack（`--target {claude-code|copilot|codex|generic}`）；
  - 项目 profile（`30-Projects/<name>.md` frontmatter）+ Knowledge Cards
    混合数据源；profile 优先、cards 补充、缺失自动降级；
  - markdown / json（`version: 2`）双输出；suggested prompt 按 target 拼装；
  - excluded_content 段始终输出，明示安全边界。
- **v0.2.3 已交付（M5.3 收尾）**：
  - ✅ 多 project 联合上下文：`mindforge project context a b [c ...]`，
    11 段固定输出 / path 级 dedup / 缺 profile 仅该 project 降级 /
    cross-project principles 不自动裁决冲突，按 source 并列展示。
  - ✅ 30-Projects evidence block 幂等追加：
    `mindforge project update-evidence <name> [--dry-run] [--include-drafts]`，
    `<!-- MINDFORGE:EVIDENCE:START/END -->` 受控区块，多次运行幂等，
    profile 不存在时拒绝（不自动创建）。
- **不做**：自动写 ai_inference 进项目笔记、自动生成新 prompt、调 LLM。
- **风险**：追加块的幂等性已是测试重点；切勿把人手写笔记吃掉。
- **优先级**：⭐⭐⭐ → ✅ 已落地 v0.2.3，详见 [`V0_2_3_REVIEW.md`](./V0_2_3_REVIEW.md)。

---

## M5.4 · Optional embedding / RAG spike（**仅 spike**）

- **目标**：评估"是否值得引入 embedding"。**不**直接实现产品级 RAG。
- **不做**：默认开启、写到主 pipeline、依赖云端 embedding API 作为强依赖。
- **验收（spike 完成的标志）**：
  - 一份独立报告 `docs/M5_4_RAG_SPIKE.md`，包含：
    1. 在我现有 vault 上跑 embedding 的成本/收益数字（对比 keyword 召回）；
    2. 至少 10 个真实查询的对比表（keyword vs embedding，谁更好用）；
    3. 是否决定进入 v0.4.0 实现，给出结论与 owner。
- **风险**：embedding 极易把 v0.x 拖成"AI 笔记产品"；做之前必须先确认
  v0.2.x 的 keyword recall 真的不够用。
- **优先级**：⭐（**先不要做**；用满 1 个月 keyword 再说）

---

## M5.5 · Obsidian plugin spike

- **目标**：评估"是否值得做 Obsidian 插件"，用作 in-vault 浏览 / 一键
  approve 入口。
- **不做**：从一开始把所有 CLI 重写成 plugin；尝试自己做 Obsidian 同步。
- **验收（spike 完成的标志）**：
  - `docs/M5_5_PLUGIN_SPIKE.md`，记录：
    1. Obsidian Plugin API 是否能稳定调本机 CLI / IPC；
    2. 如果做，建议范围（仅 review 一键、approve 一键、project context 拉取）；
    3. 真实使用 1 周后我自己是否仍想要插件，给出结论。
- **风险**：插件项目自带维护成本、跨平台、Obsidian 升级 break 风险高。
- **优先级**：⭐（除非 CLI 用够了仍觉得 in-vault 缺位）

---

## M5.6 · Review scheduling / weekly review

- **目标**：在 `mindforge review due` 之上加调度算法（FSRS / SM-2 / 自研）
  与 `mindforge review weekly` 一键周复盘。
- **不做**：真正的 spaced repetition 学术优化、推送通知、跨端同步。
- **验收**：
  - 调度算法配置为 yaml 可换；默认仍是 v0.2.0 的固定间隔；
  - `mindforge review weekly` 输出一份 markdown 报告：上周新审核数 /
    上周复习数 / 下周建议复习清单，全部基于 frontmatter 与 runs 数据；
  - 不调 LLM。
- **风险**：调度算法极易过度复杂；先做"按 result 选间隔"已经够用 1 个季度。
- **优先级**：⭐⭐（在 v0.2.x 真实复习节奏跑一段后再判断）

---

## M5.7 · Real usage telemetry without content leakage

> ✅ **已落地于 v0.2.3**（[复盘](./V0_2_3_REVIEW.md) · [协议](./M5_7_TELEMETRY_PROTOCOL.md)）

- **v0.2.3 已交付**：
  - 独立模块 `src/mindforge/telemetry.py`（**不**与 RunLogger 复用），
    白名单 10 字段 + `record_event` 二次过滤兜底；
  - 写入 `<state.workdir>/telemetry.jsonl`，`.gitignore` 已加；
  - 默认开、永久 `local_only`；`enabled: false` 零开销；
  - `mindforge telemetry status` / `telemetry summary` 命令；
  - 6 条正则审计 telemetry.jsonl，多用例断言不含 `sk-...` / `Bearer ...` /
    关键词原文 / 卡片 body / `.env` / 项目名 / 卡片标题；
  - 写盘失败 swallow，不影响业务命令。
- **不做**（继续）：上传到任何远程服务；持久化任何 LLM 输入输出；
  keyword 原文 / 项目名 / 卡片标题。

---

## 优先级总览（推荐）

| 子项 | 优先级 | 何时考虑 |
|---|---|---|
| **M5.3** Better project context | ✅ v0.2.2 + ✅ v0.2.3 收尾 | — |
| **M5.7** Telemetry | ✅ v0.2.3 | — |
| **M5.2** WebClip/ChatExport adapter | ✅ v0.2.4（[复盘](./V0_2_4_REVIEW.md) · [协议](./M5_2_WEBCLIP_CHATEXPORT_PROTOCOL.md)） | — |
| **CLI polish #1** (`version` / `--debug` / 友好错误) | ✅ v0.2.4 | — |
| **M5.1** PDF/Docx adapter | 🟡 协议占位 v0.2.4 ([协议](./M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md))；实装仍 ⭐⭐⭐ | 当真实有 PDF/docx 输入需求时 |
| **M5.6** Review scheduling | ⭐⭐ | 复习节奏跑通 1 个季度后 |
| **M5.4** RAG spike | ⭐ | **不要急**；先把 keyword 用满 |
| **M5.5** Obsidian plugin spike | ⭐ | **不要急**；CLI 用够了再考虑 |

---

## 不进入 M5 的反清单（永久 backlog 黑名单）

以下方向无论看起来多诱人，**都不要**塞进 v0.3.x：

- 浏览器插件 / Cubox API 重新实现
- 自己做 Obsidian 同步
- 自动 approve / AI 直接写 long-term memory
- 多端同步 / 自家云
- 复杂 GUI / Web UI
- 知识图谱可视化
- 任何"自动决策不询问人"的能力

理由：这些都直接破坏 v0.1 已经定下的 **AI 永远只能写 ai_draft，人是
长期记忆唯一晋升者** 这条根。
