# M4 · Recall / Review / Project Memory 候选设计（**只读调研**）

> 本文不是实现计划，是 **M4 设计调研报告**。明确目标：在不写一行业务代
> 码的前提下，把"M3 之后到底做什么、做到什么程度、怎么做不会偏掉"完整
> 想清楚，再请人决定是否进入实现。
>
> 阅读约定：
> - **[现状]** = 仓库当前已有的事实
> - **[推断]** = 我基于 v0.1 经验做出的判断
> - **[建议]** = 给 M4 的具体提议（仍待人确认）
> - **[未决]** = 必须 ask 人才能定的问题（汇总在 §9）

---

## 0. 上下文与约束

[现状]
- v0.1.0-rc2 已锁定：`scan / process / approve / status / llm ping` 五条 CLI；
- Knowledge Card 已有 frontmatter 字段：`id / title / status / track /
  projects / tags / value_score / confidence / source_* / created_at /
  prompt_version / profile / stage_models / run_id`；
- `state.json` 以 `<source_type>::<source_path>` 为键索引 ItemState；
- 反 AI 污染闸门生效：只有人在 CLI 上显式 approve 才能进入 `human_approved`。

[建议] M4 必须服务**已经成为 `human_approved` 的卡片为主**，把 `ai_draft`
排除在 review 候选外。recall 可以照看 ai_draft（"我以前看过类似的，记得不
确定"），但默认按 `human_approved` 优先。

---

## 1. M4 总目标（一句话）

让"经过审核的长期记忆"**真正被用起来**：定期回顾、按需召回、按项目装填
LLM 上下文 — 全部基于现有 frontmatter 的**规则检索**，不引入 embedding /
RAG / 自动调度。

---

## 2. Review 子系统

### 2.1 review due 如何定义？

[建议] v0.1 阶段不做 SM-2 / FSRS 等正式 spaced repetition，理由：
1. 算法细节会立刻把 review 字段从 3 个膨胀到 8+ 个，污染 frontmatter；
2. 调度本身需要一个守护进程或 cron，违反 v0.1 "本地 CLI" 边界；
3. **真正的瓶颈不是"算法不够好"，而是"我根本没坐下来 review"**。先把
   "what to review next" 这件事做对，再谈"when"。

[建议] M4 用极简 due 规则：

```
due_for_review(card, now) = (
    card.status == "human_approved"            # 仅 human_approved 进入 review 池
    AND (
        card.last_reviewed_at is None          # 从未 review 过
        OR now - card.last_reviewed_at >= card.review_interval_days
    )
)
```

`review_interval_days` 是一个**手动**字段（不自动学习），默认 14 天，
人可以在卡片 frontmatter 上改；M4 不替它做调度。

### 2.2 候选排序

[建议]：

1. **优先级第一档**：`status==human_approved AND last_reviewed_at is None`
   （刚审核完还没 review 过的）；
2. **优先级第二档**：`status==human_approved AND now - last_reviewed_at >=
   interval`，按"逾期天数"降序；
3. **打散噪音**：同一 track 单次 review batch 中最多 N 条（默认 5），避免
   一打开全是同一主题；
4. **不**做基于 value_score 的智能排序 — 那是另一个独立 feature，留待 M4.x。

### 2.3 frontmatter 字段草案

| 字段 | 类型 | 谁写 | 含义 |
|---|---|---|---|
| `last_reviewed_at` | ISO datetime \| null | `mindforge review mark` | 上次 review 完成时间 |
| `review_count` | int | `mindforge review mark` | 累计 review 次数 |
| `review_interval_days` | int | 人手填，默认 14 | 复习间隔（M4 不自动学习） |
| `review_status` | enum: `due` / `done` / `snoozed` / `archived` | `mindforge review mark` | 当前状态 |
| `review_after` | ISO datetime \| null | 衍生字段，可不存盘 | last_reviewed_at + interval，方便排序 |

[建议] 这 4 个字段全部 **optional**，缺失按 `null/0/14/null` 默认值处理；不强制
回填历史 ai_draft / human_approved 卡片。

### 2.4 v0.1 / v0.2 阶段表

| 阶段 | 范围 |
|---|---|
| **M4 v0.2.0**（建议本次实现） | `review due` 命令打印候选清单；`review mark <card>` 更新 `last_reviewed_at` / `review_count` |
| **M4 v0.2.1** | `review snooze <card> --days N` |
| **未来 v0.3+**（**不**进入 M4） | spaced repetition 算法、自动调度守护进程、review session UI |

---

## 3. Recall 子系统

### 3.1 为什么先做规则检索，不做 embedding/RAG

[推断]
- v0.1 卡片库规模在数百到数千之间；按 frontmatter 索引 + 子串匹配完全够用；
- embedding 一旦引入需要：选 model / 持久化 vector / 增量重算 / 相似度阈值
  调参 — 每一项都是独立的复杂度；
- RAG 在"我自己的卡片"场景下经常输给精确的 frontmatter 过滤（track /
  project / source_type），因为我**知道自己想要什么 track**；
- 如果发现规则检索召回质量明显不够，再升级到 embedding 也不迟，且届时
  M4 已经积累了"哪些字段最常被用来召回"的真实经验。

→ M4 v0.2.0 **只**做规则检索，**不**引入向量库。

### 3.2 召回维度

[建议] 一律按 frontmatter 字段做精确 / 子串 / 集合匹配：

| 维度 | 字段 | 匹配方式 | 示例 |
|---|---|---|---|
| 学习主线 | `track` | 精确 | `--track agent-runtime` |
| 项目 | `projects[]` | 集合包含 | `--project my-first-agent` |
| 源类型 | `source_type` | 精确 | `--source-type cubox_markdown` |
| 标签 | `tags[]` | 集合包含 | `--tag checkpoint` |
| 状态 | `status` | 精确，默认 `human_approved` | `--status ai_draft` 调试用 |
| 关键词 | `title` + body 子串 | OR / AND | `--keyword "ReAct"` |
| 时间窗 | `created_at` / `last_reviewed_at` | 区间 | `--since 2026-01-01` |

### 3.3 输出形态（草案）

```
$ mindforge recall --track agent-runtime --project my-first-agent --limit 10

# 返回 markdown 列表（默认）
- [[20260428--react-loop-checkpoint]] · status=human_approved · score=8 · last_reviewed=2026-04-30
- [[20260415--tool-calling-error-handling]] · status=ai_draft · score=7 · last_reviewed=null
...

# 或 JSON（机器可读，方便 LLM 上下文装填）
$ mindforge recall --track agent-runtime --format json
```

### 3.4 与 review 的关系

`recall` 只读 / 只列；不修改任何 frontmatter / state。`review mark` 是唯一
写 review 字段的入口（与 M3 `approve` 是唯一写 `human_approved` 的入口
保持一致的设计哲学：**审计入口必须唯一**）。

---

## 4. Project Memory 子系统

### 4.1 `track` vs `projects` 字段是否分开？

[建议] **必须分开**，理由：

| 字段 | 含义 | 数量 | 谁定义 |
|---|---|---|---|
| `track` | 学习领域主线（强分类） | 单值 | `learning_tracks.yaml` 全局枚举 |
| `projects[]` | 关联到的具体项目 | 多值 | 自由文本，跟随个人项目命名 |

- 一张"ReAct loop checkpoint"卡片：`track=agent-runtime`，
  `projects=[my-first-agent, agent-tool-harness]`；
- track 决定它**属于**哪条领域；project 决定它**服务**哪个具体目标。
- 不应当把 project 当 tag — tag 是松散的，project 是有上下文召回责任的。

### 4.2 项目上下文包（context bundle）

[建议] M4 v0.2.0 提供一个 read-only 命令：

```
$ mindforge project context my-first-agent [--limit 20] [--format json|markdown]
```

行为：
1. 找出所有 `human_approved` 且 `projects` 包含 `my-first-agent` 的卡片；
2. 按 `last_reviewed_at` desc + `value_score` desc 排序；
3. 输出每张卡片的：`id / title / track / source_url / Source Excerpt /
   AI Summary / Reusable Prompts` 五段；
4. **不**输出 `AI Inference (low confidence)` 与 `Human Note` 之外的私
   人理解（除非 `--include-human-note`）。

### 4.3 后续如何服务 Claude Code / Copilot

[建议] **不**做 IDE 插件、**不**做 MCP server。M4 仅保证 `project context`
输出能被任何 prompt 工具直接 cat 进去：

```
$ mindforge project context my-first-agent --format markdown > /tmp/ctx.md
# 然后用任何 LLM CLI 读 /tmp/ctx.md
```

未来如果要做 MCP server，那是 M5 / v0.3 的事，不进入 M4。

---

## 5. 数据模型扩展

### 5.1 frontmatter 新字段（全部 optional，向前兼容）

```yaml
# review 子系统
last_reviewed_at: 2026-05-12T10:00:00+08:00
review_count: 3
review_interval_days: 14            # 默认 14；人手改
review_status: due                  # due | done | snoozed | archived
```

### 5.2 ItemState 新字段（如需写到 state.json）

[建议] **暂时不**把 review 字段同步到 state.json — 单一事实源是卡片
frontmatter，state.json 只存"加工进度"。理由：
- review 是**长期、低频**事件；不需要快速查询索引；
- state.json 一旦同步 review 字段，就有了"双写一致性"问题；
- recall 命令可以接受"扫一遍卡片目录"的 O(N) 成本（N≈数千，本地秒级）。

如果未来 N 长到秒级搞不定，再用 `.mindforge/index.jsonl` 做派生索引（不
是 single source of truth）。

---

## 6. CLI 草案

```
# Review
mindforge review due [--limit 10] [--track agent-runtime]
mindforge review mark --card <path> [--snooze-days N]

# Recall
mindforge recall --track <id>
mindforge recall --project <name>
mindforge recall --tag <name> [--tag <name> ...]
mindforge recall --keyword "<text>"
mindforge recall --status human_approved   # 默认值
共同选项: [--limit N] [--format markdown|json] [--since DATE] [--until DATE]

# Project Memory
mindforge project list
mindforge project context <project-name> [--limit N] [--format markdown|json]
                                         [--include-human-note]
```

CLI 设计原则：
- 所有命令**不调 LLM**；
- 所有命令**不修改源文件**；
- 仅 `review mark` 修改 frontmatter（且唯一入口，参考 M3 `approve`）；
- 所有命令默认 `--status human_approved`；调试时显式带 `--status ai_draft`。

---

## 7. state / runs 如何记录 review / recall

### 7.1 runs/*.jsonl 新增事件（白名单字段）

| 事件 | 关键字段 |
|---|---|
| `recall_executed` | `command="recall"` / `count`（返回卡片数）/ `filters`（结构化过滤参数 hash，不存原文）|
| `review_listed` | `count` / `filters` |
| `review_marked` | `card_path` / `prev_review_status` / `new_review_status` / `review_count` |
| `project_context_emitted` | `project_name` / `count` / `output_format` |

[建议] 新增白名单字段：`filters` / `count` / `prev_review_status` /
`new_review_status` / `review_count` / `project_name` / `output_format`。
其余字段沿用现有白名单。

**禁止**：jsonl 不得记录 keyword 文本本身（避免泄漏检索意图历史）—
仅记录 `keyword_provided: true` 等元数据。

### 7.2 state.json 不变

按 §5.2，review 字段不进 state.json。

---

## 8. M4 验收标准（建议门槛）

```
[必达]
1. mindforge review due  能在 fake vault 上正确列出候选并按规则排序；
2. mindforge review mark 写 frontmatter 正确，且 runs jsonl 留审计；
3. mindforge recall --track / --project / --tag / --keyword 四种过滤都有
   单测覆盖；
4. mindforge project context <name> 输出包含五段必需内容（id / title /
   track / source_url / Source Excerpt / AI Summary / Reusable Prompts）；
5. 所有 M4 命令不触发 HTTP（沿用 rc1 stop-rule httpx.Client.post 拦截
   测试模板）；
6. 所有 M4 命令零 .env 可跑通；
7. 反向断言：M4 任何命令都不能写 status=human_approved（保护 M3 闸门）；
8. ruff clean；测试增量 ≥ 25 条，总数预期 ≥ 148。

[非必达 / 留待 M4.x]
- review snooze
- 复杂排序（value_score 加权）
- JSON 输出 schema 锁定
```

---

## 9. M4 明确不做（硬约束）

- ❌ embedding / RAG
- ❌ 自动复习调度（SM-2 / FSRS / 守护进程 / cron）
- ❌ Obsidian 插件 / 浏览器插件 / IDE 插件 / MCP server
- ❌ 自动改写原始 source 文件（`00-Inbox/**` 仍只读）
- ❌ AI 自动批准 / AI 自动 review mark
- ❌ 复杂知识图谱 UI / Web GUI
- ❌ 调用真实 LLM
- ❌ 引入新数据库（依然 `state.json` + 卡片 frontmatter）

---

## 10. 进入实现前需要人确认的问题（[未决]）

1. **review_interval_days 默认值** 14 天合适吗？还是 7 / 30？
2. **review_status 的 4 个枚举值**（`due` / `done` / `snoozed` / `archived`）
   是否够用？要不要加 `skipped`？
3. **recall 的 keyword 搜索**应只看 title，还是 title + body？body 全文
   搜索本地 grep 即可，但会暴露 ai_inference / human_note 的内容到 stdout，
   是否要默认排除这两段？
4. **project context 是否默认包含 `Reusable Prompts / Principles` 段？**
   还是要用 `--include-prompts` 显式开启？
5. **`mindforge project list`** 的 project 列表来源：扫所有卡片
   `projects[]` 字段做并集，还是要求 `configs/projects.yaml` 显式声明？
   后者更可控，但增加一份配置维护成本。
6. **runs jsonl 是否记录 `keyword_provided: true` 这类元数据**？还是
   完全不记 keyword 痕迹（连"是否传了"也不记）？
7. **是否需要 `mindforge recall --json | jq ...`** 可组合管道作为一等
   公民？这会影响 markdown / json 两种输出的细节稳定性承诺。
8. **review 是否服务 ai_draft？** 我倾向于"不"（理由见 §0），但你可能
   希望"我审一遍 AI 草稿后再决定要不要 approve"。如果需要，要不要新加
   一个独立命令 `mindforge triage queue` 而不是塞进 review？

---

## 11. 推荐的 M4 最小范围（一句话）

> **M4 v0.2.0 = `review due` + `review mark` + `recall --track/--project/
> --tag/--keyword` + `project context <name>` + 8 项验收测试。
> 全部基于现有 frontmatter，不引入新存储、不调 LLM、不写源文件。**

如果 §9 任意一项被破坏（哪怕"先做个 embedding 试试"），M4 就已经偏离
v0.1 → v0.2 路线。

---

## 12. 下一步

1. 请人确认 §10 八个 [未决] 问题；
2. 一旦确认，写 `docs/M4_RECALL_REVIEW_PROTOCOL.md`（落地协议，
   类似 M3 的格式）；
3. 然后才开始 src 实现。

**M4 实现不在本次范围**。本文档只提供调研结论。
