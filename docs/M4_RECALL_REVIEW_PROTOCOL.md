# M4 · Recall / Review / Project Memory 协议（v0.2.0 实现契约）

> 本文是 M4 的**实现契约**。原调研报告已归档到
> [`archive/v0_2/M4_RECALL_REVIEW_DESIGN.md`](./archive/v0_2/M4_RECALL_REVIEW_DESIGN.md)。
> 设计阶段的 8 个 [未决] 问题在本协议中已通过**默认决策**收
> 敛 — 见 §0。本文一旦冻结，src 实现按本文为准；偏离协议必须先改本文。
>
> 阅读约定：
> - **[规范]** = 实现必须遵守的硬约束
> - **[默认]** = 可在 `configs/mindforge.yaml` 中调整的默认值
> - **[禁止]** = 任何实现路径都不允许做的事
>
> 与 M3 协议的关系：M4 复用 M3 建立的"**审计入口必须唯一**"原则 ——
> `review mark` 是 review 字段的唯一写入口，正如 `approve` 是
> `human_approved` 的唯一写入口。

---

## 0. 默认决策汇总（M4_DESIGN §10 八个未决问题的收敛结果）

| # | 设计期 [未决] | 协议期 [默认] / [规范] | 可调整 |
|---|---|---|---|
| 1 | review_interval_days 默认 | 不再用单一 interval 字段；改为按 result 分桶：`remembered=14d / partial=7d / forgotten=1d` | 是，`review.intervals.*` 配置项 |
| 2 | review_status 枚举 | 改为 `last_review_result ∈ {remembered, partial, forgotten}` + 派生字段 `review_after`；不再单独维护 status 枚举 | 否（结构性约束） |
| 3 | recall keyword 搜索范围 | **仅** title + frontmatter 字段（track / projects / tags），**不**搜 body | 否，避免 ai_inference / human_note 内容意外暴露到 stdout |
| 4 | project context 是否含 Reusable Prompts | **默认包含**（这是项目记忆的核心价值之一） | 是，`--no-prompts` 可关 |
| 5 | `mindforge project list` 来源 | 扫所有卡片 `projects[]` 字段做并集，**不**要求显式 yaml | 是，未来如发现噪音多再引入 `configs/projects.yaml` |
| 6 | runs jsonl 是否记 keyword 痕迹 | 仅记 `keyword_provided: bool` + `keyword_hash`（sha256 前 8 字符），**不**记原文 | 否（隐私强约束） |
| 7 | recall JSON 输出是否一等公民 | **是**，`--format json` 与 `markdown` 同等支持，schema 在 §6.4 锁定 | 否 |
| 8 | review 是否服务 ai_draft | **默认不**；用 `--include-drafts` 显式打开 | 是，仅命令行选项级别 |

---

## 1. 范围与目标

[规范]
- M4 服务**已经成为 `human_approved`** 的卡片为主体；`ai_draft` 仅在显式
  `--include-drafts` 时进入候选。
- M4 提供三类命令：**review**（带写）、**recall**（只读）、**project context**（只读）。
- M4 全程**不**调用 LLM、**不**读取 `.env`、**不**改写源文件、**不**引入新存储。
- M4 沿用 M3 反 AI 污染原则：仅 `mindforge approve` 写 `human_approved`；M4
  任何命令都**不**修改 `status` 字段。

[禁止]
- ❌ embedding / 向量库 / RAG
- ❌ 自动复习调度（cron / 守护进程 / 后台任务）
- ❌ Obsidian / 浏览器 / IDE 插件 / MCP server
- ❌ 改写 `00-Inbox/**` 任何源文件
- ❌ AI 自动 approve / AI 自动 review mark / AI 辅助决策
- ❌ 批量修改卡片（`review mark` 一次只能 `--card <一个路径>`，与 M3 `approve` 一致）
- ❌ 调用真实或 fake LLM provider
- ❌ 复杂知识图谱 UI / Web GUI
- ❌ 引入新数据库 / SQLite

---

## 2. 数据模型扩展

### 2.1 Knowledge Card frontmatter 新增字段（全部 optional，向前兼容）

```yaml
# review 子系统（仅 'mindforge review mark' 写）
reviewed_at: 2026-05-12T10:00:00+08:00       # 上次 review 完成时间
review_count: 3                              # 累计 review 次数
last_review_result: remembered               # remembered | partial | forgotten
review_after: 2026-05-26T10:00:00+08:00 # 下一次 review 候选时间（派生）

# project memory（人手填或既有；M4 不自动推断）
projects:
  - my-first-agent
  - agent-tool-harness
```

[规范]
- 旧卡片缺这些字段时按 `null/0/null/null` / `[]` 默认值处理；**不**触发
  schema migration、**不**强制回填。
- `review_after` 由 `review mark` 写入，由 `last_review_result` +
  `reviewed_at` + 配置间隔计算得出；**不**手动维护。
- `last_review_result` 取值仅限三种字符串；其他值视为损坏（exit 3）。

### 2.2 ItemState（state.json）**不**扩展

[规范] M4 不向 `state.json` 添加 review / recall 字段。理由：
- review 是低频写入；卡片 frontmatter 是单一事实源（与 M3 `approve` 哲学一致）；
- recall 是纯读，扫卡片目录的 O(N) 成本可接受（数千卡片本地秒级）；
- 双写 = 一致性问题，违反 v0.1 "克制"原则。

如果未来 N 大到秒级搞不定，再用 `.mindforge/index.jsonl` 做**派生**索引
（不是 single source of truth）— 这是 v0.3+ 的事，不在 M4。

### 2.3 `configs/mindforge.yaml` 新增 `review` 配置块

```yaml
review:
  intervals:
    remembered: 14   # days
    partial: 7
    forgotten: 1
  default_include_drafts: false   # CLI 总开关；--include-drafts 仍按命令行优先
```

[默认] 三个间隔默认值如上；用户可改。`default_include_drafts` 默认 false。

---

## 3. 命令清单（M4 v0.2.0 最小实现）

### 3.1 review

```
mindforge review due [--limit N=10] [--track <id>] [--project <name>]
                     [--include-drafts] [--include-missing-review-after]
                     [--format markdown|json]
                     [--config <mindforge.yaml>]

mindforge review mark --card <path>
                      --result remembered|partial|forgotten
                      [--config <mindforge.yaml>]
```

### 3.2 recall

```
mindforge recall [--track <id>] [--project <name>] [--tag <name> ...]
                 [--keyword <text>] [--source-type <type>]
                 [--status human_approved|ai_draft|all]   # 默认 human_approved
                 [--include-drafts]                        # = --status all 的语法糖
                 [--since YYYY-MM-DD] [--until YYYY-MM-DD]
                 [--limit N=20] [--format markdown|json]
                 [--config <mindforge.yaml>]
```

### 3.3 project

```
mindforge project list [--format markdown|json]
                       [--config <mindforge.yaml>]

mindforge project context <project_name>
                          [--limit N=20]
                          [--format markdown|json]
                          [--no-prompts]            # 关掉 Reusable Prompts 段
                          [--include-drafts]
                          [--config <mindforge.yaml>]
```

---

## 4. Review 子系统协议

### 4.1 `review due` 候选规则

[规范] 一张卡片满足以下**全部**条件才进入 due 列表：

1. `status == "human_approved"`（除非 `--include-drafts`）；
2. 满足以下任一：
   - `review_after is None` **且** 命令带 `--include-missing-review-after`；
   - `review_after <= now`；
3. 通过可选过滤器（`--track` / `--project`）。

[规范] **不**带 `--include-missing-review-after` 时，**从未 review 过**的
卡片不会出现在 due — 这是为了防止"刚 approve 完一堆卡片 → 全部立刻进 due"
的洪水效应。让人**显式**说"我想看看那些还没 review 过的"。

### 4.2 排序

[规范] due 列表按以下顺序：
1. `review_after` 升序（越早到期越靠前）；
2. `review_after is None` 的（仅 `--include-missing-review-after` 模式下出现）排在最后；
3. 同 review_after 时按 `value_score` 降序；
4. 同分时按 `id` 字母序（稳定排序）。

### 4.3 `review mark` 行为

[规范] 必须传 `--card` 与 `--result` 两个参数（无默认值）。

行为：
1. 加载卡片 frontmatter；卡片不存在 → exit 2；YAML 损坏 → exit 3；
2. **不**校验 `status`：M4 默认只 mark `human_approved` 卡片，但若用户
   通过 CLI 显式 mark 了 `ai_draft`（例如 `--include-drafts` 工作流），
   也允许 — review 不构成 AI 污染（review 不晋升 status）；
3. 计算：
   ```
   reviewed_at = now (ISO with tz)
   review_count = (旧值 or 0) + 1
   last_review_result = <参数>
   review_after = reviewed_at + review.intervals[last_review_result]
   ```
4. 原子写回（参考 M3 `_atomic_write` 实现）；
5. 写 runs jsonl `review_mark_completed` 事件。

[规范] **不**改卡片正文、**不**改 16 个原 frontmatter 字段、**不**改源文件、
**不**改 state.json。

### 4.4 退出码

| Exit | 含义 |
|---|---|
| 0 | 成功（review due / mark 都用此） |
| 2 | 卡片文件不存在 / 配置错 |
| 3 | frontmatter 缺 / YAML 损坏 / `last_review_result` 取值非法 |
| 4 | （保留）—— review 命令族当前无此分支 |

---

## 5. Recall 子系统协议

### 5.1 数据源

[规范]
- **唯一**数据源：vault 内 `cards_dir` 下递归扫到的 Knowledge Card；
- **不**读 source 文件（`00-Inbox/**`）；
- **不**读 `state.json`；
- **不**读 `runs/*.jsonl`；
- **不**读 `.env` / 环境变量（除常规系统变量）。

### 5.2 过滤语义

[规范]
- 多个过滤器之间是 **AND**；
- `--tag` 可重复；多个 `--tag` 之间也是 AND（"同时含这几个 tag"）；
- `--track` / `--project` / `--source-type` 单值精确匹配；
- `--keyword` 子串匹配，**仅**搜以下范围：
  - frontmatter `title`
  - frontmatter `track`
  - frontmatter `projects[]`
  - frontmatter `tags[]`
  - frontmatter `source_title`
  - 卡片**文件名**（不含路径）
  - **不**搜 body / Source Excerpt / AI Summary / AI Inference / Human Note
- 大小写不敏感；`--keyword` 仅作为**辅助过滤**（与其他过滤器 AND），不
  做相关性打分；
- `--status` 默认 `human_approved`；`--include-drafts` = `--status all` 的语法糖；
- `--since` / `--until` 比对的是 `created_at`（卡片首次写入时间）。

### 5.3 输出字段（白名单 — 安全摘要）

[规范] recall 仅输出以下字段：

```
id, title, path, status, track, projects, tags,
source_type, source_url, created_at,
reviewed_at, review_after, value_score
```

[禁止] 不得输出：
- 卡片 body（任何段落）；
- `prompt_text` / `completion_text` / `raw_text`；
- `api_key` / `Authorization` / 任何 secret；
- frontmatter 中除上述白名单外的字段（即使该字段未来被新增）。

### 5.4 输出 schema（`--format json` 锁定）

```json
{
  "version": 1,
  "query": {
    "track": "agent-runtime",
    "project": null,
    "tags": [],
    "keyword_provided": true,
    "keyword_hash": "a3f0c1de",
    "status_filter": "human_approved",
    "since": null,
    "until": null,
    "limit": 20
  },
  "count": 7,
  "items": [
    {
      "id": "20260428-react-loop-checkpoint",
      "title": "ReAct Loop 中加 checkpoint 的两种方式",
      "path": "20-Knowledge-Cards/agent-runtime/20260428--react-loop-checkpoint.md",
      "status": "human_approved",
      "track": "agent-runtime",
      "projects": ["my-first-agent"],
      "tags": ["agent", "checkpoint"],
      "source_type": "cubox_markdown",
      "source_url": "https://example.com/post/xxx",
      "created_at": "2026-04-28T13:00:00+08:00",
      "reviewed_at": "2026-05-12T10:00:00+08:00",
      "review_after": "2026-05-26T10:00:00+08:00",
      "value_score": 8
    }
  ]
}
```

[规范] 此 schema 是 v0.2.0 的**稳定承诺**：v0.2.x 内只能新增可选字段，不
删除、不改语义。

---

## 6. Project Memory 子系统协议

### 6.1 `project list`

[规范] 扫描所有卡片，对 `projects[]` 字段做并集去重；按字母序输出
`(name, card_count)`。**不**要求 `configs/projects.yaml`（默认决策 #5）。

### 6.2 `project context <name>`

[规范] 输出一个**只读**的 markdown context pack，结构固定：

```markdown
# Project Context · <name>

> Generated by mindforge project context at <iso datetime>
> 仅含 status=human_approved 的卡片摘要（除非 --include-drafts）
> 字段范围：见 docs/M4_RECALL_REVIEW_PROTOCOL.md §5.3

## Related Learning Tracks
- agent-runtime (3 cards)
- harness-engineering (1 card)

## Knowledge Cards (sorted by review_after asc, then value_score desc)

### [20260428-react-loop-checkpoint] ReAct Loop 中加 checkpoint 的两种方式
- track: agent-runtime · status: human_approved · value_score: 8
- source: https://example.com/post/xxx (cubox_markdown)
- reviewed_at: 2026-05-12 · review_after: 2026-05-26
- path: 20-Knowledge-Cards/agent-runtime/20260428--react-loop-checkpoint.md

#### Source Excerpt
> （从卡片正文 §Source Excerpt 段提取，原样不改）

#### AI Summary
（从卡片正文 §AI Summary 段提取）

#### Reusable Prompts / Principles  ← 可用 --no-prompts 关闭
（从卡片正文 §Reusable Prompts / Principles 段提取）

## Action Items
（汇总所有相关卡片的 §Action Items 段；如卡片无该段则跳过）

## Review Due
- [20260415-tool-calling-error-handling] (overdue 3 days)
- ...

## Safe Context Hint for LLM Tools

> 把以下原则告诉调用方 LLM（Claude Code / Copilot / 其他）：
> - 本文件由 mindforge 生成，含我审核确认过的长期记忆卡片摘要；
> - 不含我未确认的 AI 推测（ai_inference）与个人笔记（human_note）；
> - 不含 secret / api_key / source 原文 / prompt 全文；
> - 优先信任 Source Excerpt（原文事实）+ Reusable Prompts（已沉淀的方法）。
```

[禁止]
- 不输出 `AI Inference (low confidence)` 段；
- 不输出 `Human Note` 段（人手私笔记，不进 LLM 上下文）；
- 不调用 LLM 自动生成"项目摘要" — 这是 M4 强约束的**手工 prompt**，
  内容固定，仅做字段拼接。

### 6.3 排序与 limit

[规范] 卡片按以下顺序：
1. `review_after` 升序（即将到期的优先），`null` 排最后；
2. 同时按 `value_score` 降序；
3. `--limit` 默认 20。

---

## 7. 可观察性（runs/*.jsonl）

### 7.1 新增事件

| 事件名 | 命令 | 关键字段 |
|---|---|---|
| `review_due_listed` | `review due` | `count` / `filters` / `keyword_provided` / `keyword_hash` |
| `review_mark_started` | `review mark` | `card_path` / `result` |
| `review_mark_completed` | `review mark` | `card_path` / `result` / `prev_review_count` / `new_review_count` / `review_after` |
| `review_mark_failed` | `review mark` | `card_path` / `error_message` |
| `recall_executed` | `recall` | `count` / `filters` / `keyword_provided` / `keyword_hash` / `output_format` |
| `project_list_emitted` | `project list` | `count` / `output_format` |
| `project_context_emitted` | `project context` | `project_name` / `count` / `output_format` |

### 7.2 新增白名单字段（`run_logger._ALLOWED_FIELDS`）

```
filters, keyword_provided, keyword_hash, output_format,
result, prev_review_count, new_review_count, review_after,
project_name, count
```

[规范] `filters` 字段是结构化 dict，仅含**已知过滤器键**（track/project/
tag/source_type/status/since/until/limit/include_drafts/include_missing_review_after），
其值为字符串或 list[str]。绝不放原始 keyword、绝不放卡片正文、绝不放 path
列表。

### 7.3 [禁止] runs jsonl 中

- 卡片正文 / Source Excerpt / AI Summary / AI Inference / Human Note 任一段
- `prompt_text` / `completion_text` / `raw_text`
- `api_key` / `Authorization` / Bearer token / x-api-key
- 用户输入的 `--keyword` 原文

---

## 8. 反 AI 污染断言（沿用 M3 风格）

[规范] M4 测试套件必须包含以下反向断言（其中 #1 #2 是硬质量门）：

1. **M4 任何命令都不会写 `status: human_approved`**
   （扫所有卡片 frontmatter，跑 `review mark` / `recall` / `project context`
   后 `status` 字段集合不变）；
2. **M4 任何命令都不会发起 HTTP**（沿用 rc1 stop-rule httpx.Client.post 拦截测试）；
3. M4 任何命令在零 `MINDFORGE_*` 环境变量下可跑通；
4. `recall` / `project list` / `review due` 不修改任何文件；
5. `review mark` 仅修改指定卡片的 4 个字段（`reviewed_at` / `review_count`
   / `last_review_result` / `review_after`），其他字段 + 正文 byte 级不变；
6. `project context` 输出**不含** `AI Inference` / `Human Note` / 任何 secret；
7. runs jsonl 不出现 keyword 原文与卡片正文。

---

## 9. 验收标准（M4 v0.2.0 实现完成 = 同时满足）

```
[必达]
1. 7 个命令全部实现并通过 single-card / multi-card vault 端到端测试；
2. 反 AI 污染断言 §8 全部通过；
3. recall JSON schema §5.4 锁定，schema round-trip 测试通过；
4. project context 输出固定结构 §6.2，单测验证段落标题与字段范围；
5. `configs/mindforge.yaml.review.intervals.*` 三个 key 可被 yaml 改动并
   实际生效（review mark 计算正确间隔）；
6. ruff clean；测试增量 ≥ 25 条，总数预期 ≥ 148。

[非必达]
- review snooze 命令（v0.2.1）
- 复杂排序（如 value_score 加权 review）
- recall 输出色彩化 / table 化（rich.Table）
```

---

## 10. M4 明确不做（硬约束 — 偏离即违反协议）

参见 §1 [禁止] 列表 + §0 默认决策的反向约束。任何"先做个 embedding 试
试" / "顺手加个守护进程" / "再写个插件" 的提议都应被记入 ROADMAP M5
backlog，**不**进入当前 M4。

---

## 11. 实现顺序建议（下一轮）

按以下顺序实现，每步都是可独立 commit + 测试的最小单元：

1. **配置扩展**：`config.py` 加 `ReviewConfig`（intervals + default_include_drafts）；
   单测覆盖默认值与 yaml 覆盖；
2. **卡片读取层**：新建 `src/mindforge/cards.py`（或扩展 writer.py），提供
   `iter_cards(vault) -> Iterable[CardSummary]`，**纯只读**，输出仅含 §5.3
   白名单字段；单测覆盖 frontmatter 解析鲁棒性；
3. **recall 命令**：纯只读，最先实现，无副作用；用于**后续命令的子组件**；
4. **project list / project context**：复用 `iter_cards` + 新建段落抽取
   `extract_section(body, name)` 工具；
5. **review due**：在 `iter_cards` 上加 due 规则；只读；
6. **review mark**：唯一的写命令，参考 `approver.py` 模式（原子写 +
   runs jsonl + 退出码契约）；新建 `src/mindforge/reviewer.py`；
7. **run_logger 扩展**：白名单字段 + 7 个新事件常量；
8. **反向断言测试**：单独一份 `tests/test_m4_safety_guarantees.py`，集中
   覆盖 §8 七条；
9. **README / ROADMAP / CHANGELOG / archived v0.2 review**。

每步完成后运行 `pytest && ruff check src tests`，绿了才进下一步。

---

## 12. 实现前的人审核 checkpoint

[规范] 在开始第 1 步之前，必须确认：
- 本协议 §0 八个默认决策**没有**被人否决（否决任何一项 = 回到 design
  阶段重新调研）；
- `docs/ROADMAP.md` M4 行已标记"协议已收敛 · 待实现"；
- 没有任何 M5 backlog 项被偷偷塞进 M4 实现顺序。
