# MindForge ROADMAP — 项目状态机

> 这份文档是 MindForge 的"项目状态机"。每个 Milestone 都是一个**可完成、可验收、可停止**的阶段，用来防止在 Cubox / PDF / Docx / Obsidian 插件 / RAG / 多模型 / 复习系统之间反复横跳，导致 v0.1 边界失控。
>
> **使用方法**：每个 Milestone 必须按统一的六段结构推进：**目标 / 交付物 / 验收标准 / 明确不做什么 / 停止规则 / 进入下一阶段的条件**。

---

## 学习型说明：为什么要先写 Roadmap，而不是先写代码？

如果不先冻结 Roadmap：
- 容易在做 Cubox adapter 时，顺手开始想"PDF 怎么解析"，进而陷入 OCR/表格抽取的兔子洞；
- 容易在做 LLM 调用时，顺手实现 fallback / 多模型路由，导致 v0.1 拖到三个月；
- 容易把 Obsidian 插件、浏览器插件、复习调度算法等"每一项都很合理"的需求，全部塞进 v0.1。

Roadmap 的本质是：**把"什么时候该做什么"和"什么时候该停"明确写下来**，让每一次"想多做一点"都需要先说服自己更新 Roadmap，而不是直接动手。这就是 MindForge 的项目级"状态机"。

---

## Milestone 总览

| Milestone | 主题 | 是否调用 LLM | 是否写 src/ 业务代码 | v0.1 必经 |
|---|---|---|---|---|
| **M0** | 项目契约冻结 | ❌ | ❌ | ✅ |
| **M1** | Source Ingestion MVP | ❌ | ✅ | ✅ |
| **M1.5** | M2 Preflight：运行事件日志 | ❌ | ✅ | ✅ |
| **M2** | LLM Processing MVP | ✅ | ✅ | ✅ |
| **M2.5** | Anthropic-compatible provider 接入 + 加固 | ✅ | ✅ | ✅ |
| **M2.7** | `.env` 自动加载 + `--profile` / `--dry-run` / `llm ping` | ❌（仅校验） | ✅ | ✅ |
| **M2.8** | 真实 provider smoke 收口（lazy provider build） | ✅（一次性 smoke） | ✅ | ✅ |
| **M2.9** | 卡片模板清理 + v0.1 收口测试 + rc1 tag | ❌ | ✅ | ✅ |
| **M3** | 显式 `mindforge approve` 反 AI 污染闸门（[协议](./M3_HUMAN_APPROVAL_PROTOCOL.md)） | ✅ | ✅ | ✅ |
| **M4** | 回顾 / 召回 / 项目记忆（[设计](./M4_RECALL_REVIEW_DESIGN.md) → [协议](./M4_RECALL_REVIEW_PROTOCOL.md) → [复盘](./V0_2_0_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.0 |
| **M4.1** | recall 排序/格式 + project context output/include flags（[复盘](./V0_2_1_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.1 |
| **M5.3** | project context 产品化（target / project profile / suggested prompt 模板）（[协议](./M5_3_PROJECT_CONTEXT_PROTOCOL.md) → [复盘](./V0_2_2_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.2 |
| **M5.3 收尾** | 多 project 联合 context + 30-Projects evidence block 幂等追加（[复盘](./V0_2_3_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.3 |
| **M5.7** | 本地 only telemetry（白名单字段 / status / summary）（[协议](./M5_7_TELEMETRY_PROTOCOL.md) → [复盘](./V0_2_3_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.3 |
| **M5.2** | WebClip / ChatExport adapter 实装（[协议](./M5_2_WEBCLIP_CHATEXPORT_PROTOCOL.md) → [复盘](./V0_2_4_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.4 |
| **CLI polish #1** | `mindforge version` / 全局 `--debug` / 友好错误（[复盘](./V0_2_4_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.4 |
| **M5.1** | PDF / Docx adapter 最小真实实装（lazy import + 友好错误，**不**做 OCR）（[协议](./M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md) → [复盘](./V0_2_FINAL_REVIEW.md)） | ✅ | ✅ 最小 | ✅ v0.2.5 |
| **M5.5** | Vault 友好度（`vault index/links/refresh`，**不**改卡片正文）（[复盘](./V0_2_FINAL_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.5 |
| **CLI polish #2** | 全局 `--vault` 覆盖 / `mindforge doctor` / completion 文档（[复盘](./V0_2_FINAL_REVIEW.md)） | ✅ | ✅ | ✅ v0.2.5 |
| **v0.2.6 日用化** | `mindforge init` / approve workflow polish (`approve list` / `--source-id` / `--all`) / doctor action items / onboarding smoke（[复盘](./V0_2_6_REVIEW.md) · [smoke](./ONBOARDING_SMOKE.md)） | ✅ | ✅ | ✅ v0.2.6 |
| **M5.4 Lexical Recall (BM25)** | `mindforge recall --query [--explain]` / `mindforge index rebuild|status` / 仅索引安全字段 / 不引入 RAG / embedding（[协议](./M5_4_LEXICAL_RECALL_PROTOCOL.md) · [复盘](./V0_3_0_REVIEW.md)） | ✅ | ✅ | ✅ v0.3.0 |
| **M5.4.1 BM25 配置化 + Hybrid 排序** | `search:` 块（字段权重 / k1 / b / hybrid 权重） · `recall --ranking hybrid` · `config_hash` + `index status` 漂移检测 · `doctor` 索引 hint（[复盘](./V0_3_1_REVIEW.md)） | ✅ | ✅ | ✅ v0.3.1 |
| **M5.4.2 Recall/Search UX polish** | `recall --weight-bm25/--weight-value-score/--weight-review-due` 临时覆盖 · `recall --explain` 增强（why_this_matched / weight_source）· `index info [--json]` / `index status --json` · doctor 搜索 hint 增强（[复盘](./V0_3_2_REVIEW.md)） | ✅ | ✅ | ✅ v0.3.2 |
| **M5.8 Review Scheduling MVP** | `review schedule [--days N]` 按日分组 · `review backlog`（overdue/today/upcoming/missing）· `review stats [--json]` · `review mark --dry-run/--note` · 仍为本地计划，**不**做后台调度 / 系统提醒（[协议](./V0_4_REVIEW_SCHEDULING_PROTOCOL.md) · [复盘](./V0_4_0_REVIEW.md)） | ✅ | ✅ | ✅ v0.4.0 |
| **M5.8.1 Review polish + Onboarding** | `review schedule --format ical` 本地 .ics 导出 · `review weekly` 周报（无 LLM）· doctor overdue/due-this-week hint · `GETTING_STARTED.md` / `USER_GUIDE.md` / `ROADMAP_PROGRESS.md`（[复盘](./V0_4_1_REVIEW.md)） | ✅ | ✅ | ✅ v0.4.1 |
| **M5** | 高级集成（插件 / OCR / RAG / 调度）— [backlog 拆解](./M5_BACKLOG.md) | ✅ | 🟡 backlog 已拆 | ❌（明确推迟） |

---

## Milestone 0 · 项目契约冻结

### 目标
把"MindForge 是什么 / 不是什么 / v0.1 边界 / 协议 / 配置 / 状态"全部锁定到文档，作为后续所有实现的唯一依据。本阶段没有写一行业务代码，但有了**不可漂移的契约**。

### 交付物
- `docs/ROADMAP.md`（本文件）
- `docs/MINDFORGE_PROTOCOL.md` — Pipeline 协议、`SourceDocument` 数据契约、Knowledge Card frontmatter 契约、stage 列表
- `docs/V0_1_SCOPE.md` — v0.1 in/out scope 单页清单 + 8 条停止规则
- `configs/mindforge.yaml` — 含 `vault` / `sources` / `llm` / `state` / `triage` / `prompts` / `logging`
- `configs/learning_tracks.yaml`
- `configs/llm.example.yaml` — `default` / `local_first` / `all_local` 三种 profile 的完整样例
- `prompts/{triage,distill,link_suggestion,review_questions,action_extraction}/v1.md` + `manifest.yaml`
- `templates/knowledge_card.md.j2`
- `vault_template/`（Obsidian Vault 目录骨架与 README）

### 验收标准
- 阅读上述文档，可以独立回答："v0.1 完成了什么？没完成什么？为什么是这样？"
- 任意一个新契约字段都能在 `MINDFORGE_PROTOCOL.md` 找到出处。
- 任意一个 stage 都能在 `mindforge.yaml.llm.profiles` 找到映射；`profiles` 中每个 alias 都能在 `llm.models` 找到定义。
- `sources.enabled` 中每一项都在 `sources.registry` 找到对应 adapter。

### 明确不做什么
- ❌ 不写 `src/` 任何业务代码
- ❌ 不安装运行时依赖
- ❌ 不连任何 LLM
- ❌ 不实现任何 SourceAdapter / LLMClient / Scanner / Processor / Writer

### 停止规则
五份核心文档（ROADMAP / PROTOCOL / SCOPE / mindforge.yaml / knowledge_card 模板）评审通过即停。**不要**在 M0 阶段顺手补 PDF/RAG/插件的设计；这些进入 M5 backlog 即可。

### 进入下一阶段的条件
- `MINDFORGE_PROTOCOL.md` 与 `V0_1_SCOPE.md` 通过自审；
- 未来一周内对核心契约无改动需求；
- 用户（项目所有者）显式 approve "M0 → M1"。

---

## Milestone 1 · Source Ingestion MVP（不调 LLM）

### 目标
把"多源 → SourceDocument"链路打通；让 `mindforge scan` 与 `mindforge status` 在不依赖 LLM 的情况下能跑通。

### 交付物
- `src/mindforge/sources/base.py` — `SourceAdapter` 抽象 + `SourceDocument` 数据类
- `src/mindforge/sources/registry.py` — 按 `sources.registry` 派发
- `src/mindforge/sources/cubox_markdown.py`（**实现**）
- `src/mindforge/sources/plain_markdown.py`（**实现**）
- `src/mindforge/sources/{webclip_markdown,pdf,docx,chat_export,manual_note}.py`（**仅 stub** + `NotImplementedError`，类型 / 目录 / 配置占位齐全）
- `src/mindforge/scanner.py` — 扫描 `00-Inbox/<sub>/`，调用对应 adapter 输出 `SourceDocument` 流
- `src/mindforge/checkpoint.py` — 写入 `state.json`，记录 `source_id` / `source_type` / `adapter_name` / `source_path` / `content_hash` / `status=raw`
- `src/mindforge/cli.py` — `scan` / `status` 命令
- `src/mindforge/config.py` — yaml 加载与全链路校验
- `src/mindforge/models.py` — dataclass 集合
- `tests/test_sources_cubox.py`、`tests/test_sources_plain.py`、`tests/test_checkpoint.py`

### 验收标准
- 在样例 vault 上 `mindforge scan` 能识别 Cubox 与 Plain Markdown 两类文件并正确生成 `SourceDocument`。
- `state.json` 字段齐全，重复 scan 同一未变更文件不会改变 `content_hash`。
- `mindforge status` 正确打印每种 `source_type` 的计数。
- 单测全部绿；adapter stub 调用会 `NotImplementedError`。

### 明确不做什么
- ❌ 不调用任何 LLM
- ❌ 不写 Knowledge Card 文件
- ❌ 不实现 PDF / Docx / WebClip / ChatExport 的真实解析逻辑（仅 stub）
- ❌ 不做 OCR / 网页抓取

### 停止规则
上述验收满足即停；**不要**把 PDF/Docx 真实解析、OCR 或网页抓取塞进 M1。

### 进入下一阶段的条件
- `SourceDocument` 协议在两种真实 adapter 上稳定；
- 下游模块只依赖该协议，不出现 `if source_type == "cubox"` 类分支；
- 用户显式 approve "M1 → M2"。

---

## Milestone 1.5 · M2 Preflight：运行事件日志（不调 LLM）

> **定位**：这是 M1 完成后、M2 正式开工前的"准备工作"，**不是** M2 本身。
> 目的是先把 observer / event log 的接线和契约固定下来，让 M2 加入 LLM
> 调用时**只需要 `logger.emit("llm_call", stage=..., model_alias=..., ...)`
> 即可**，不必再改日志框架。

### 目标
- 引入"每次 CLI 运行 = 一份 `.mindforge/runs/<run_id>.jsonl`"的事件日志机制。
- 把 `state.json`（checkpoint / 现状快照）与 `runs/*.jsonl`（observer / 过程回放）的职责彻底分离。
- 把已有的 `scan` / `status` 命令接入事件日志，跑通最小事件集。

### 交付物
- `src/mindforge/run_logger.py`：`RunLogger` 类（context manager；append-only jsonl；字段白名单防止"顺手把原文塞进日志"；自动 emit `run_started` / `run_finished` / `run_failed`）。
- `scan` 命令接入事件：`run_started` / `source_seen` / `source_skipped_or_unchanged` / `source_error` / `state_written` / `run_finished`（异常时 `run_failed`）。
- `status` 命令接入事件：`run_started` / `status_reported` / `run_finished`。
- `tests/test_run_logger.py` + `tests/test_scanner_cli.py` 中两条新增 e2e 用例验证 jsonl 落盘与字段。

### 事件结构（v0.1）
每行一条 JSON：
```
{"ts": "...", "run_id": "...", "event": "<name>", ...其他白名单字段}
```
字段白名单（v0.1）：`command` / `config_path` / `source_id` / `source_type` /
`adapter_name` / `source_path` / `path` / `content_hash` / `status` /
`error_message` / `counts` / `items_count` / `active_profile`。
M2 起追加（已预登记）：`stage` / `model_alias` / `provider` / `actual_model` /
`prompt_version` / `input_file_hash` / `tokens_in` / `tokens_out` / `latency_ms`。

### 明确不做什么
- ❌ 不实现 `llm/`、`LLMClient`、`triager` / `distiller` / `linker`、`process` 命令、Knowledge Card 写出。
- ❌ 不调用任何云端或本地大模型。
- ❌ 不在事件中写入 `raw_text` / 文章正文 / 卡片正文（白名单已强制拒绝）。

### 停止规则
当 `scan` / `status` 都能产出符合事件结构的 jsonl 且测试覆盖到位即停。

### 进入 M2 的条件
- 事件结构稳定，M2 加入 LLM 调用时只需新增 `llm_call` 事件即可；
- 用户显式 approve "M1.5 → M2"。

---

## Milestone 2 · LLM Processing MVP

### 目标
在已有 `SourceDocument` 之上接入 LLMClient，跑通五个 stage 的最小链路：`triage → distill → link_suggestion → review_questions → action_extraction`。

### 交付物
- `src/mindforge/llm/base.py` / `openai_compatible.py` / `factory.py` / `client.py`
  - `LLMClient.resolve_model_for_stage(stage)`
  - `LLMClient.generate(stage, prompt, vars, options)`
- `prompts/{triage,distill,link_suggestion,review_questions,action_extraction}/v1.md` 投入使用
- `src/mindforge/triager.py` / `distiller.py` / `linker.py`
- `src/mindforge/cli.py` 增加 `process` / `process --file <path>` / `process --limit N`
- 每次 LLM 调用写入 `.mindforge/runs/<run_id>.jsonl`（含 `stage` / `model_alias` / `provider` / `actual_model` / `prompt_version` / `input_file_hash` / `tokens` / `latency` / `status`）
- `state.json` 中 `stages.<stage>` 子结构按协议写入

### 验收标准
- 单文件 `mindforge process --file <path>` 能跑完五个 stage，并落地到 `state.json` 与 run jsonl。
- 切换 `active_profile`（`default` ↔ `local_first` ↔ `all_local`）能改变实际调用的模型，无需改代码。
- 同一 `cloud_openai_compatible` provider 下 `cheap_cloud` 与 `strong_cloud` 可被不同 stage 同时使用。
- LLM 调用失败按重试策略执行；最终失败的项标 `failed` 并记录 `error_message`。

### 明确不做什么
- ❌ 不做 fallback、多模型投票、按 value_score 动态切换、token-aware routing
- ❌ 不做 embedding / RAG / agent loop
- ❌ 不写 Knowledge Card 文件（写文件留到 M3）

### 停止规则
五个 stage 都能稳定产出结构化结果即停。**不要**为了"再稳一点"加 fallback 或重试金字塔。

### 进入下一阶段的条件
- 同一文件跑两次 process 结果可在 run jsonl 中复盘；
- prompt_version 切换可被记录；
- 用户显式 approve "M2 → M3"。

---

## Milestone 3 · Vault 输出与人工确认机制

### 目标
把 LLM 产出真正落到 `20-Knowledge-Cards/`，并保证 raw source 与 generated card 物理分离、AI 内容默认 `ai_draft`、必须人工晋升 `human_approved`。

### 交付物
- `src/mindforge/writer.py`（jinja2 渲染 `templates/knowledge_card.md.j2`）
- Knowledge Card frontmatter 含：`source_id` / `source_type` / `adapter_name` / `source_path` / `source_url` / `source_excerpt` / `ai_summary` / `ai_inference` / `human_note` / `confidence` / `prompt_version` / `profile` / `stage_models` / `status: ai_draft`
- 写文件冲突策略：默认不覆盖，写 `<filename>.conflict.md`
- `mindforge status` 增加"`ai_draft` 卡片堆积数"提示
- 反向同步：人工把 Card `status` 改为 `human_approved` 后，下一次 `scan`/`status` 把该状态回写到 `state.json`

### 验收标准
- 端到端：`scan → process → 卡片落到 20-Knowledge-Cards/<track>/`，frontmatter 字段齐全。
- 原始 inbox 文件零改动。
- 手动改 Card status 后，`state.json` 同步出现 `human_approved`。

### 明确不做什么
- ❌ 不自动晋升 `human_approved`
- ❌ 不改写原始 Cubox/PDF/Docx 文件
- ❌ 不做 GUI / 卡片浏览器

### 停止规则
端到端跑通 + 人工晋升机制工作即停。

### 进入下一阶段的条件
- v0.1 完成。可以正式打 tag `v0.1.0` 并冻结。
- 满足 `docs/V0_1_SCOPE.md` 中的 8 条整体停止规则。

---

## Milestone 4 · 回顾、召回与项目记忆（v0.2 / v0.3 候选）

### 目标
让长期沉淀真正"被用起来"。

### 交付物（候选，按需）
- `mindforge review --due` — 基于 Card 内已生成的 review_questions，输出最小复习清单（**不**做调度算法）
- `mindforge recall --project <id>` — 基于 frontmatter `projects:` 字段做静态过滤召回（**不**做向量检索）
- learning track index — 自动生成 `20-Knowledge-Cards/<track>/_index.md`
- prompt library — 把 Card 中提炼出的 `Reusable Prompts / Principles` 汇总到 `40-Reviews/prompt-library.md`
- weekly review 模板

### 明确不做什么
- ❌ 不做 embedding / RAG
- ❌ 不做自动复习调度算法（SM-2 / FSRS 等）
- ❌ 不做项目记忆的 LLM 自动写回

### 停止规则
任一交付物达到"我自己每周会用"的程度即可停，不必全部完成。

---

## Milestone 5 · 高级集成（明确推迟，不进入 v0.1 / v0.2）

仅作为 **backlog** 占位，避免任何阶段被诱惑提前实现：

- Obsidian 插件 / 浏览器插件
- PDF 深度解析 / OCR / 表格抽取
- Docx 深度解析
- Embedding / RAG
- 自动双链重写
- 多模型 fallback / 投票 / 智能路由
- 自动复习调度（SM-2 / FSRS）
- 知识图谱 UI

→ 这些一旦在 M0–M3 期间被讨论，**应当一律记入本节 backlog，而不是插入当前 milestone**。

---

## v0.1 整体停止规则（硬约束）

当**全部**满足以下条件时，v0.1 必须停手、打 tag、写复盘，**不**再加功能：

1. 能扫描 `00-Inbox/`，识别多种 source_type
2. 能为 Cubox Markdown 与 Plain Markdown 生成统一 `SourceDocument`
3. 能通过 LLMClient（profile + stage routing）跑通 triage / distill / link_suggestion / review_questions / action_extraction
4. 能写入 `20-Knowledge-Cards/`，frontmatter 字段齐全，默认 `status: ai_draft`
5. 能在 `state.json` 与 `runs/*.jsonl` 中追溯每个文件的 stage / model_alias / provider / actual_model / prompt_version / content_hash
6. 人工把 Card `status` 改为 `human_approved` 能被识别并回写 `state.json`
7. 有最小测试覆盖（adapters / checkpoint / config 校验）
8. 有 `README.md` + `docs/ROADMAP.md` + `docs/MINDFORGE_PROTOCOL.md` + `docs/V0_1_SCOPE.md` 四份文档

满足以上 8 条 = v0.1 完成。**不要**继续塞 PDF / RAG / Obsidian 插件 / 自动复习。

---

## 当 Roadmap 自身需要修改时

如果在 M1+ 任何时刻你想增加一个新需求：

1. **先**回到本文件，看它属于哪个 Milestone；
2. 如果属于当前或下一个 Milestone — 更新对应章节；
3. 如果属于 M5 backlog — 加入 backlog，**不**插入当前 Milestone；
4. 如果与 v0.1 整体停止规则冲突 — 先冻结 v0.1，再立 v0.2 提案。

→ Roadmap 是项目级状态机；改 Roadmap = 改状态。改状态必须显式，不能"顺手就做了"。
