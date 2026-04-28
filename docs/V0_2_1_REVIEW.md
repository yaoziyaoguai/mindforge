# MindForge v0.2.1 · M4.1 复盘

> 范围：v0.2.0 之后的**真实使用效率增强**。
> 上一轮：[V0_2_0_REVIEW.md](./V0_2_0_REVIEW.md)
> 下一轮 backlog：[M5_BACKLOG.md](./M5_BACKLOG.md)

---

## 1. M4.1 增量能力清单

### 1.1 recall

| 能力 | 详情 |
|---|---|
| 多 token AND keyword | `--keyword "agent runtime"` 拆 token 后**全部**命中才算匹配 |
| 大小写不敏感 | 全部 token 与 haystack 都 `.lower()` 比较 |
| 仍**不**搜 body / source / human_note | `_keyword_match` 仅扫 frontmatter 白名单 + 文件名 |
| `--sort` | `default \| review_after \| updated_at \| title \| value_score` |
| `--format` | `compact (默认) \| table \| markdown \| json` |
| markdown 输出 | 适合直接粘贴到 Claude / Copilot；含 `path=...` 便于跟读 |
| 默认仍 `human_approved` | `--include-drafts` 显式打开 |
| `--sort bogus` | exit 2 |

### 1.2 project context

| 能力 | 详情 |
|---|---|
| `--output FILE` | 写文件而不是 stdout；父目录不存在 → exit 2 |
| `--limit N` | 渲染前截断卡片数 |
| `--include-actions / --no-actions` | 默认开 |
| `--include-review-due / --no-review-due` | 默认开 |
| `--include-next-step-prompt / --no-next-step-prompt` | 默认开；**固定模板**，**不**调 LLM |
| `--include-drafts` | 默认关 |
| 不变 | 不含 AI Inference / Human Note / source 原文 |

### 1.3 安全边界（M4.1 仍是"安全召回层"，不是 RAG/LLM）

- ❌ 不调用 LLM（含 fake / 真实）
- ❌ 不读 `.env`
- ❌ 不修改 `00-Inbox/**` 源文件
- ❌ 不写 `state.json`
- ❌ 不索引 / embedding / 向量化
- ✅ 仅读 `20-Knowledge-Cards/**.md` frontmatter + 段落抽取
- ✅ `runs jsonl` 仍只记 `keyword_provided` + `keyword_hash`

---

## 2. Smoke 结果（隔离临时目录 + fake fixture）

| # | 命令 | exit | 备注 |
|---|---|---|---|
| 1 | `recall --keyword "agent runtime"` | 0 | 多 token AND |
| 2 | `recall --sort review_after` | 0 | due 在前 |
| 3 | `recall --sort title` | 0 | 字母升序 |
| 4 | `recall --format markdown` | 0 | `# Recall · ...` 头 |
| 5 | `recall --format table` | 0 | rich Table |
| 6 | `project context my-first-agent` | 0 | 默认全段 |
| 7 | `project context --no-actions --no-review-due` | 0 | 段落消失 |
| 8 | `project context --limit 1` | 0 | 截断生效 |
| 9 | `project context --output ctx_pack.md` | 0 | 1875 字节落盘，stdout 仅一行确认 |

✅ 9/9 通过；6 条凭据正则审计 0 hit；repo 根未污染。

---

## 3. 测试 / Lint / Diff

| 项 | 结果 |
|---|---|
| `pytest` | **161 passed**（v0.2.0 142 → +19 M4.1 用例） |
| `ruff check src tests` | clean |
| `git diff --check` | clean |

新增覆盖：
- recall multi-token AND / case-insensitive / 不搜 body
- recall 4 个 sort key + invalid 退出 2
- recall 4 种 format（compact / markdown / table / json）
- recall 默认仅 human_approved + `--include-drafts` 切换
- recall 不发 HTTP（拦截 httpx）
- project context `--output` 写文件 / 父目录缺失 exit 2 / `--limit` 截断
- project context `--no-actions` / `--no-review-due` / `--no-next-step-prompt` 段落隐藏
- project context 通过 `--output` 路径仍不泄漏 AI Inference / Human Note

---

## 4. M4.1 明确不做（仍坚守 v0.1 立柱）

- ❌ embedding / RAG / 向量检索
- ❌ 自动复习调度
- ❌ Obsidian 插件
- ❌ AI 自动 approve
- ❌ 批量修改卡片
- ❌ 改写源文件
- ❌ 跨 project 的自动双链生成

→ 全部归到 [M5_BACKLOG.md](./M5_BACKLOG.md)，按优先级排队，不在 v0.2.x 内做。

---

## 5. 下一步建议

按优先级排（建议**先停手、先用**）：

1. **真实使用 1–2 周** — 跑 `mindforge project context my-first-agent --output` 喂给 Claude Code / Copilot，看 prompt pack 是否好用，记录痛点。
2. 如果痛点集中在"项目笔记如何接收 context pack" → 进入 [**M5.3** Better project context](./M5_BACKLOG.md#m53--better-project-context--prompt-pack)。
3. 如果痛点集中在"PDF / docx 读不到" → 进入 [**M5.1** PDF / Docx adapter](./M5_BACKLOG.md#m51--pdf--docx-adapterv03x-候选)。
4. 如果想看自己用了哪些命令、哪些卡片被反复召回 → 进入 [**M5.7** Telemetry](./M5_BACKLOG.md#m57--real-usage-telemetry-without-content-leakage)。
5. **不**建议优先级：M5.4（RAG）/ M5.5（Obsidian 插件） — 极易过度工程，先把 keyword + CLI 用满。
