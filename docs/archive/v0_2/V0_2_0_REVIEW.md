# MindForge v0.2.0 · M4 复盘

> 范围：M4 — 回顾 / 召回 / 项目记忆最小闭环。
> 协议：[M4_RECALL_REVIEW_PROTOCOL.md](./M4_RECALL_REVIEW_PROTOCOL.md)
> 设计：[M4_RECALL_REVIEW_DESIGN.md](./M4_RECALL_REVIEW_DESIGN.md)
> 上一轮：[V0_1_RC2_REVIEW.md](./V0_1_RC2_REVIEW.md)

---

## 1. 本轮交付能力

| 能力 | 命令 | 备注 |
|---|---|---|
| 规则检索 | `mindforge recall` | 仅查 frontmatter 白名单 + 文件名；keyword **不**搜 body |
| 复习候选 | `mindforge review due` | 默认仅 `human_approved`；只读 |
| 复习标记 | `mindforge review mark` | 唯一允许写 4 个 review 字段的入口；不改 `status`、不改正文 |
| 项目枚举 | `mindforge project list` | 聚合所有卡片 frontmatter `projects[]`，按字母序 |
| 项目上下文包 | `mindforge project context <name>` | 输出固定结构 markdown / json，**不**含 `AI Inference` / `Human Note` |
| 安全边界 | — | 全部 M4 命令 ❌ 不调 LLM、❌ 不读 `.env`、❌ 不修改源文件、❌ 不写 `state.json` |
| 默认范围 | — | 默认 `status=human_approved`；`--include-drafts` 显式打开 |

实现细节落于以下新模块：

- `src/mindforge/cards.py` — `CardSummary` 白名单（17 字段）+ `iter_cards` / `extract_section` / `filter_cards`（AND 语义）
- `src/mindforge/reviewer.py` — `mark_card_review()` 唯一写入口；原子写；exit code 契约 0/2/3
- `src/mindforge/project_context.py` — 固定结构 markdown / json 渲染器
- `src/mindforge/config.py` — `ReviewConfig` / `ReviewIntervals`（remembered=14 / partial=7 / forgotten=1，可改）
- `src/mindforge/run_logger.py` — 白名单加 10 字段 + 7 个 M4 事件常量
- `src/mindforge/cli.py` — 新增 `recall` / `review due,mark` / `project list,context` 子命令

---

## 2. 自动 Smoke 结果

**临时目录**：`/var/folders/.../mf_smoke_*/`（每次随机；脚本保证 ≠ repo 根）
**Fixture**：复用 `tests/test_process_e2e.py::_build_vault_with_fake_llm` —
    fake LLM provider，零 HTTP，零 .env 依赖。
**安全审计**：smoke 后扫所有 stdout，验证不含真实凭据正则模式
（`sk-...` / `Bearer ...` / `*_API_KEY=` / `Authorization:` /
`raw_response":` / `completion":`）。

| # | 命令 | exit | 结果摘要 |
|---|---|---|---|
| 1 | `mindforge recall --track "Agent Runtime"` | 0 | `Recall · 1 项` |
| 2 | `mindforge recall --project "my-first-agent"` | 0 | `Recall · 1 项` |
| 3 | `mindforge review due` | 0 | `当前没有到期复习候选。`（卡片新建无 review_after） |
| 4 | `mindforge review mark --card <fixture> --result remembered` | 0 | `count: 0 → 1, next_review_after=2026-05-12` |
| 5 | `mindforge project context my-first-agent` | 0 | 固定结构 markdown，含 Source Excerpt / AI Summary / Reusable Prompts，**无** AI Inference / Human Note |
| 6 | `mindforge project list` | 0 | `Projects · 1 项 — my-first-agent (1 card)` |

✅ 6/6 通过；0 leak；repo 根目录未被污染。

---

## 3. 测试 / Lint / Diff

| 项 | 结果 |
|---|---|
| `pytest` | **142 passed**（M3 收口 123 → +19 M4 用例） |
| `ruff check src tests` | clean |
| `git diff --check` | clean |

新增 19 用例覆盖：
- cards 基础（iter / extract_section / filter AND 语义）
- recall（默认 human_approved / keyword 不搜 body / json schema 仅白名单 / 不修改文件）
- review mark（4 字段写入 / 不改 status / 不改正文 / yaml 间隔生效 / exit 2 / exit 3）
- review due（只读）
- project list / context（不含 ai_inference / human_note / `--no-prompts`）
- §8 安全反向断言（不发 HTTP / 不写 status=human_approved / 无 MINDFORGE_* env / runs jsonl 不出现 keyword 原文与 body）

---

## 4. 安全检查

| 项 | 状态 | 说明 |
|---|---|---|
| `.env` 是否被 M4 命令读取 | ❌ 不读 | M4 子命令未调 `load_dotenv`；smoke 在干净 env 下通过 |
| `.env` 是否被提交 | ❌ 未提交 | 见 `.gitignore`；`git status --short` 不含 `.env` |
| `.mindforge/` runs/state 是否被提交 | ❌ 未提交 | 见 `.gitignore`；smoke 期间产生于临时目录 |
| stdout 是否泄漏凭据 | ❌ 无 | 6 命令 stdout 通过 6 条正则审计 |
| stdout / runs jsonl 是否含 body 内容 | ❌ 无 | `recall keyword` 仅记 `keyword_hash`；body 段不进 jsonl |
| 是否调用真实 LLM | ❌ 未调用 | smoke 用 fake provider；测试拦截 `httpx.Client.post/send` |
| 是否处理真实 Cubox/Obsidian vault | ❌ 未处理 | smoke 在 `tempfile.mkdtemp()` 隔离目录 |
| 是否改写源文件（`00-Inbox/**`） | ❌ 未改写 | M4 命令仅写 Knowledge Card 4 字段（review mark） |

---

## 5. M4 明确不做（防 scope creep）

- ❌ embedding / RAG / 向量检索
- ❌ 自动复习调度（SM-2 / FSRS）
- ❌ Obsidian 插件 / 浏览器插件
- ❌ AI 自动 approve（`status: human_approved` 仍只能由 `mindforge approve` 写）
- ❌ 批量修改卡片（review mark 一次只动 1 张卡片的 4 个字段）
- ❌ 自动跨卡片建立双链
- ❌ 任何 M4 命令调 LLM

---

## 6. 已知小事项

- `mindforge review mark` 输出的 `next_review_after=YYYY-MM-DD` 字段名与协议 `review_after` 不严格一致 —— **仅 CLI 文案差异**，frontmatter 与 run jsonl 一律使用 `review_after`。后续若要统一文案可在 v0.2.x 微调。
- `project context` 当前**精确匹配** project 名（与 `projects[]` 元素逐一比较）。后续若需要别名 / 大小写不敏感可在 v0.2.x 加 `--fuzzy`。
- `iter_cards` 不递归 `*.conflict.md` / 隐藏文件；写文件冲突仍走 M3 既有约定。

---

## 7. 下一阶段建议

按优先级排序（建议**先停手复盘**，再决定走哪条）：

1. **M4.1（小修）** — 协议字段名与 CLI 文案对齐；`project context --fuzzy`；`recall --since/--until` 真实接入（当前已解析参数）。
2. **真实使用周** — 用 v0.2.0 在自己每周一次的复习节奏里跑 1–2 周，记录哪条命令最常用、哪条多余。
3. **M5 backlog 拆条** — 把 Obsidian 插件 / RAG / OCR / 自动调度逐条拆到 backlog，**不要**在 v0.2.x 期间引入。
4. **不建议**：在没用 1–2 周之前就上 RAG 或调度算法 —— 极易过度工程。

---

## 8. v0.2.0 边界回顾（一句话）

> v0.2.0 完成了**让长期记忆被人审过、被复习过、被项目召回**的最小闭环；
> AI 仍然只能写 `ai_draft`；人是唯一能把内容晋升 `human_approved` 的角色。
