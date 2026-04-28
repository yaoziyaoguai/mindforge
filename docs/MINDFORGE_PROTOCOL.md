# MindForge 协议（PROTOCOL）

> 这份文档定义 MindForge 的**核心数据契约与处理协议**，是 v0.1 起所有模块都必须遵守的唯一来源。任何模块的实现，只要与本文不一致，应优先修改实现而不是协议；如果协议本身需要演化，必须显式更新本文 + ROADMAP，并标注版本。
>
> 当前协议版本：**v0.1.0-draft**。

---

## 学习型说明：为什么要先冻结协议？

软件工程里反复出现的一个反模式：**先写实现，再倒推协议**。结果是每个模块对"输入是什么"都有一套自己的假设，新增一个源类型就要改五个地方。

MindForge 早期就有"多源、多 stage、多 model"的复杂度。如果协议不冻结：
- 加一个 PDF adapter 要改 Triager；
- 加一个 stage 要改 LLMClient；
- 改一个 prompt 要改 Card 模板；
- 一年后回看，根本说不清"某条卡片是怎么生成的"。

所以本文要做的事是：**把"任何模块都能依赖"的最小协议先定下来**，让 SourceAdapter 增减、stage 增减、provider 切换、prompt 升级都不破坏其他人。

---

## 1. Pipeline 协议

MindForge 的处理链路严格遵守以下顺序：

```
Source Ingestion → Triage → Distill → Link → Apply → Review → Memory
```

| 阶段 | 中文 | 谁负责 | 输入 | 输出 |
|---|---|---|---|---|
| Source Ingestion | 多源接入 | `SourceAdapter` + `Scanner` | inbox 中的原始文件 | `SourceDocument` |
| Triage | 分流 + 价值评分 | `Triager`（LLM stage = `triage`） | `SourceDocument` | `track`、`value_score`、`should_process` |
| Distill | 提炼 | `Distiller`（LLM stage = `distill`） | `SourceDocument` + triage 结果 | Card 草稿（含 `source_excerpt` / `ai_summary` / `ai_inference`） |
| Link | 双链建议 | `Linker`（LLM stage = `link_suggestion`） | Card 草稿 | `suggested_links` 列表 |
| Apply | 行动项 / 项目钩子 | `Linker`/独立模块（LLM stage = `action_extraction`） | Card 草稿 + 项目列表 | `action_items` / `project_hooks` |
| Review | 复习题生成 | LLM stage = `review_questions` | Card 草稿 | `review_questions` 列表 |
| Memory | 长期记忆 | `Writer` + 人工 | Card + status 变化 | `20-Knowledge-Cards/<track>/*.md`，`status: ai_draft → human_approved` |

> **关键点**：Apply 与 Review 在 v0.1 都是**生成结构化字段**，不做执行（不真正"提醒做"）。Memory 阶段的"晋升"完全由人触发。

---

## 2. SourceDocument 数据契约（adapter 统一输出）

**任何 `SourceAdapter.load(path)` 必须返回一个 `SourceDocument`，下游模块只依赖此结构**。

```python
@dataclass
class Highlight:
    text: str
    note: str | None = None
    location: str | None = None  # 例如 "p.42" / "char 1200-1300"

@dataclass
class SourceDocument:
    source_id: str          # 稳定主键。建议: sha1(source_type + ":" + source_path)
    source_type: str        # cubox_markdown | plain_markdown | webclip_markdown
                            # | pdf | docx | chat_export | manual_note
    adapter_name: str       # CuboxMarkdownAdapter / PlainMarkdownAdapter / ...
    source_path: str        # 相对 vault root 的路径
    title: str | None
    author: str | None
    source_url: str | None
    created_at: datetime | None    # 原始文档的创建时间（如能解析）
    captured_at: datetime | None   # 收藏 / 入 inbox 的时间
    tags: list[str]
    highlights: list[Highlight]    # 仅适用源（Cubox 等）会有
    raw_text: str                  # 统一为纯文本/Markdown，供 LLM 使用
    metadata: dict                 # adapter 特有字段，不向上层泄漏
    content_hash: str              # sha256(raw_text + 关键 metadata)
```

### 设计要点
- **`metadata` 是 adapter 的"逃生舱"**：任何源特有字段（Cubox 的 `bookmark_id`、PDF 的页数等）都进 `metadata`，**不**进顶层字段。
- **下游模块禁止 `if source_type == "cubox"` 这类分支**。任何源类型差异必须在 adapter 内部抹平。
- **`source_id` 必须稳定**：同一文件在同一路径，多次 ingest 应返回同一 `source_id`。这样 `state.json` 可以以 `source_id` 为键稳定增量。
- **`content_hash` 决定是否需要重处理**：未变化跳过，变化重跑。

---

## 3. SourceAdapter 接口

```python
class SourceAdapter(Protocol):
    name: str           # 例如 "CuboxMarkdownAdapter"
    source_type: str    # 例如 "cubox_markdown"

    def can_handle(self, path: str) -> bool: ...
    def load(self, path: str) -> SourceDocument: ...
```

### v0.1 落地范围

| Adapter | v0.1 状态 | 备注 |
|---|---|---|
| `CuboxMarkdownAdapter` | ✅ 必须实现 | 解析 Cubox 官方插件同步的 Markdown / frontmatter / highlights |
| `PlainMarkdownAdapter` | ✅ 建议实现 | 普通 Markdown 与手写笔记 |
| `WebClipMarkdownAdapter` | 🟡 仅 stub | 接口预留 |
| `PdfAdapter` | 🟡 仅 stub | 不做 OCR / 表格抽取 |
| `DocxAdapter` | 🟡 仅 stub | 不做复杂样式解析 |
| `ChatExportAdapter` | 🟡 仅 stub | ChatGPT/Claude/Copilot 对话导出 |
| `ManualNoteAdapter` | 🟡 可选 | 与 PlainMarkdownAdapter 可合并 |

### 学习型说明：为什么 Cubox 只是第一个，不是唯一？

Cubox 是"读取最多"的入口，但不是"知识发生最多"的地方。你的：
- PDF 论文、Docx 报告 — 来自学术 / 工作；
- 浏览器剪藏 — 来自即时阅读；
- ChatGPT/Claude/Copilot 对话导出 — 来自实战（这是 Agent 工程师独特的素材！）；
- 手写笔记 — 来自思考时的灵感；

如果 MindForge 只接 Cubox，就只能加工"轻收藏"，错过"重思考"。所以协议必须从一开始就支持多源；Cubox 优先实现只是因为它**最容易打通**，不代表它最重要。

---

## 4. LLM 配置协议（profile + stage routing）

### 4.1 概念

- **profile**：一组工作模式，描述"在这种模式下，每个 stage 用哪个 model_alias"。例如 `default` / `local_first` / `all_local`。
- **model_alias**：模型的逻辑名称，例如 `cheap_cloud` / `strong_cloud` / `local_fast` / `local_strong`。
- **model**：alias 背后的具体配置，含 `provider` / `type` / `base_url` / `api_key_env` / `model` / `timeout_seconds` / `max_retries`。

### 4.2 stage 列表（v0.1 固定五项）

| stage | 用途 |
|---|---|
| `triage` | 分流 + 价值评分（轻量、可走小模型） |
| `distill` | 生成 Card 主体（高价值、走强模型） |
| `link_suggestion` | 双链与项目钩子建议（轻量） |
| `review_questions` | 复习题（中等） |
| `action_extraction` | 行动项（中等） |

任何新增 stage 必须同时更新本文与 `prompts/<stage>/v1.md`。

### 4.3 LLMClient 接口

```python
class LLMClient:
    def resolve_model_for_stage(self, stage: str) -> ResolvedModel: ...
    def generate(
        self,
        stage: str,
        prompt: str,
        variables: dict,
        options: dict | None = None,
    ) -> LLMResult: ...

@dataclass
class ResolvedModel:
    stage: str
    model_alias: str
    provider: str
    type: str           # "openai_compatible"
    base_url: str
    model: str
    timeout_seconds: int
    max_retries: int

@dataclass
class LLMResult:
    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    raw_response: dict | None
```

### 4.4 学习型说明：为什么用 active_profile + stage→alias 而不是单一 active_provider？

之前的设计错在"只允许一个 provider 生效"，过于限制：
- 用户可能想让 `triage` 走小模型省钱，`distill` 走强模型保质；
- 用户可能想在弱网时切到 `all_local` profile 一键全部本地化；
- 用户可能在同一个 cloud provider 下，配 `cheap` 和 `strong` 两个 model 灵活切换。

`active_profile` 让"配置层面开放、执行层面克制"成为可能：
- **配置层面开放**：你可以列任意多个 profile，任意多个 model；
- **执行层面克制**：MindForge 只严格按 `active_profile.<stage>` 静态映射，不做 fallback、不做投票、不做按 value_score 动态切换。

**v0.1 不做的**：fallback、多模型投票、按 score 动态切模型、token-aware routing、embedding/RAG、agent loop。

---

## 5. Knowledge Card 数据契约

### 5.1 文件位置
`<vault>/20-Knowledge-Cards/<track>/<YYYYMMDD>--<slug>.md`

### 5.2 frontmatter 必填字段

```yaml
id: 20260428-react-loop-checkpoint
title: "ReAct Loop 中加 checkpoint 的两种方式"
status: ai_draft           # ai_draft | human_approved | archived
track: agent-runtime
projects: [my-first-agent, agent-tool-harness]
tags: [agent, runtime, checkpoint]
value_score: 8
confidence: 0.7

# 来源（多源协议）
source_id: "sha1:..."
source_type: cubox_markdown
adapter_name: CuboxMarkdownAdapter
source_path: "00-Inbox/Cubox/2026-04-27-some-article.md"
source_url: "https://example.com/post/xxx"
source_title: "Some article on agent loop"

# 加工证据链
created_at: 2026-04-28T13:00:00+08:00
prompt_version: "distill@v1"
profile: "default"
stage_models:
  triage:    { alias: "cheap_cloud",  provider: "cloud_openai_compatible", model: "cheap-model" }
  distill:   { alias: "strong_cloud", provider: "cloud_openai_compatible", model: "strong-model" }
run_id: "2026-04-28T13-00-00_ab12cd"
```

### 5.3 内容分层（强制）

Card body 必须按以下顺序排列，分层不可合并：

1. **Source Excerpt** — 原文事实（adapter 抽取，不改写）
2. **AI Summary** — AI 总结（高置信，可读）
3. **AI Inference (low confidence)** — AI 推测（低置信，必须独立标注）
4. **Human Note** — 我的理解（默认空，人工补）
5. **Reusable Prompts / Principles**
6. **Project Hooks**
7. **Review Questions**
8. **Suggested Links**

### 5.4 学习型说明：为什么 AI 默认 ai_draft，不能直接 human_approved？

如果 AI 一生成就被当成"长期记忆"：
- 几个月后翻看，无法分清哪些是事实、哪些是 AI 编的；
- 错误内容会被反复双链引用，污染知识图谱；
- 个人的"理解"被 AI 的总结吞没。

强制 `ai_draft → human_approved` 的人工晋升关，是 MindForge 的**反 AI 污染机制**。它要求你在确认前至少看一眼，并在 `Human Note` 里写一两句自己的理解。这个动作很轻，但效果是巨大的——它把 AI 重新变回"草稿手"，把你重新变回"主人"。

> 该闸门的命令契约、状态转移、审计字段、反向断言由 [`docs/M3_HUMAN_APPROVAL_PROTOCOL.md`](./M3_HUMAN_APPROVAL_PROTOCOL.md) 统一约束。`mindforge approve` 是 v0.1 阶段**唯一**允许触发该转移的入口。

---

## 6. 处理状态机

```
raw           ← scanner 看到一个 inbox 文件，但还没 triage
triaged       ← 已分流（含 value_score / track），但还没出 Card
skipped       ← value_score 低于阈值，主动放弃
processed     ← Card 已写入，AI 部分完成
failed        ← LLM 调用 / 写文件 / 校验失败
human_approved ← 仅 `mindforge approve --card <path>` 触发；详见 [`M3_HUMAN_APPROVAL_PROTOCOL.md`](./M3_HUMAN_APPROVAL_PROTOCOL.md)
```

转移图与 `state.json` schema 详见仓库根的 `plan.md`（M1+ 落地）。

> Knowledge Card 在 `human_approved` 之后还会经历 review / recall / project
> context 三类**只读 + 单字段写**的命令（M4，[`M4_RECALL_REVIEW_PROTOCOL.md`](./M4_RECALL_REVIEW_PROTOCOL.md)）。
> 这些命令**不**改 `status` 字段、**不**调 LLM、**不**改源文件，只在 frontmatter
> 上维护 4 个 review 派生字段。它们扩展 pipeline 的"使用端"，但不破坏本节
> 状态机。

---

## 7. 可观察性契约

### 7.1 两份产物的职责边界

| 产物 | 角色 | 写入时机 | 读取者 | 是否入库 |
|---|---|---|---|---|
| `.mindforge/state.json` | **checkpoint / 现状快照** | 每条 source 处理完后增量更新；原子写 + `.bak` | `scan` / `status` / `process` / 反向同步 | ❌（per-machine，已 .gitignore） |
| `.mindforge/runs/<run_id>.jsonl` | **observer / event log** | 每次 CLI 运行 = 一份；append-only | 人工事后回放 / 复盘 / prompt A/B | ❌（per-machine，已 .gitignore） |
| `.mindforge/state.json.bak` | state 备份 | 每次原子写后保留上一份 | 灾难恢复 | ❌ |

**反模式**（任何阶段都不允许）：
- 把 `state.json` 当成事件流（不要 append！它是覆盖式快照）。
- 把 `runs/*.jsonl` 当成 checkpoint（它是事件流，不能被回头修改）。
- 把任一产物提交进 git（它们是个人知识库的扫描痕迹，含路径、tag、时间）。
- 在 `runs/*.jsonl` 中写入 `raw_text` / 文章正文 / 卡片正文（白名单已强制拒绝）。

### 7.2 每次 `mindforge` 命令运行都生成

- `.mindforge/runs/<run_id>.jsonl` — 事件流（M2 起含每条 `llm_call`）
- `.mindforge/state.json` — 当前累计状态（按 `source_id` 索引，M2 起含 `stages.<stage>` 子结构）

`llm_call` 事件**必须**包含：
`stage` / `model_alias` / `provider` / `actual_model` / `prompt_version` / `input_file_hash` / `tokens_in` / `tokens_out` / `latency_ms` / `status` / `error_message` / `processed_at`

→ 这是 MindForge 的"黑匣子"。任何卡片质量问题，都能凭 run jsonl + 当时的 prompt 版本回放。

`mindforge status` 会读取最新一份 jsonl（按 mtime）并打印 `command / run_id / event_count / started / last_event` 等非敏感摘要，便于人工排查"上一次到底跑了什么"。

---

## 8. 协议演化规则

- **不可破坏向后兼容**：新增字段 OK；删除字段需要明确版本号（例如从 v0.2 起）。
- **prompt 文件不可变**：改 prompt 必须新建 `vN+1`，更新 `manifest.yaml`。
- **stage 不能随便加**：增加 stage 必须同时更新本文 + ROADMAP + 每个 profile 的映射 + manifest。
- **adapter 不能"半实现"**：要么完整支持 `can_handle` + `load`（输出合规 SourceDocument），要么 stub + `NotImplementedError`。
