# MindForge v0.1.0-rc1 收口复盘

> 本文是 v0.1 主线路（M0 → M2.9）的**项目状态机最终一格**：
> 标记 v0.1 已完成什么 / 不做什么 / 验收证据是什么 / 进入 M3 之前必须满足什么。
>
> 一旦本文档与对应的 `v0.1.0-rc1` tag 同时存在，v0.1 即冻结：除非显式
> 进入 M3，否则不得继续往主线添加新功能（任何"再加一个 source"、"再调一个
> prompt"都属于 backlog，不属于 rc1 范围）。

---

## 1. v0.1 已完成能力

| 能力域 | 完成项 | 关键文件 |
|---|---|---|
| Source Ingestion | 多源派发框架（按 inbox 子目录 → adapter） | `src/mindforge/sources/{base,registry,scanner.py?}` |
| SourceDocument 协议 | 统一 `source_id` / `source_type` / `adapter_name` / `content_hash` | `src/mindforge/sources/base.py` |
| Cubox / Plain Markdown | ✅ 实现；其余 adapter 仅 stub 占位 | `src/mindforge/sources/{cubox_markdown,plain_markdown}.py` |
| Stage Pipeline | triage / distill / link_suggestion / review_questions / action_extraction 五段式 | `src/mindforge/processors/pipeline.py` |
| LLM Provider 抽象 | `fake` / `openai_compatible` / `anthropic_compatible` 三种 type | `src/mindforge/llm/{base,fake,openai_compatible,anthropic_compatible}.py` |
| Profile + Stage Routing | `active_profile` × `stage → model_alias` 静态映射 | `configs/mindforge.yaml`, `src/mindforge/llm/client.py` |
| Lazy Provider Build | 只实例化当前 profile 引用到的 alias | `src/mindforge/llm/factory.py` |
| Knowledge Card 输出 | 默认 `status: ai_draft`；frontmatter 含 source / 加工证据链 / stage_models | `templates/knowledge_card.md.j2`, `src/mindforge/writer.py` |
| state.json checkpoint | 仅安全摘要（路由元数据 + content_hash） | `src/mindforge/checkpoint.py` |
| runs/*.jsonl observer | 字段白名单（M1.5 RunLogger preflight） | `src/mindforge/run_logger.py` |
| `.env` 自动加载 | 静默、零依赖、env > dotfile、once-only | `src/mindforge/env_loader.py` |
| CLI | `scan` / `status` / `process` / `process --profile/--dry-run/--file/--limit` / `llm ping` | `src/mindforge/cli.py` |
| 反泄漏约束 | 默认 fake profile + 字段白名单 + ProviderError 截断 + .env gitignore | `src/mindforge/run_logger.py`, `.gitignore` |
| 真实 provider smoke | 用 `anthropic_coding_plan` 在 /tmp 沙箱 vault 完成单文件端到端 | `docs/LLM_PROVIDER_CONFIG.md` §6.4 |

---

## 2. v0.1 明确不做（已写入 v0.1 边界）

- ❌ M3 `human_approved` 反向同步（人工把卡片 status 改后，state.json 自动跟随）
- ❌ Embedding / RAG / 向量检索
- ❌ Obsidian 插件 / 浏览器插件
- ❌ 自动复习调度（SM-2 / FSRS）
- ❌ 多模型 fallback / 投票 / 按 value_score 动态切换 / token-aware routing
- ❌ 批量真实资料处理（v0.1 真实 smoke 只跑过 1 份非敏感测试材料）
- ❌ 自动改写 / 删除 / 重命名 inbox 原始 source
- ❌ PDF / Docx 真实解析（adapter 仅 stub 占位）
- ❌ WebClip / ChatExport 真实解析（adapter 仅 stub 占位）
- ❌ 知识图谱 UI / 卡片浏览器 / GUI
- ❌ Token / 成本统计仪表盘（runs/*.jsonl 已记录 tokens_in/out，但不做聚合 UI）

---

## 3. v0.1 验收证据

### 3.1 自动化质量门

| 检查 | 结果 |
|---|---|
| `ruff check src tests` | ✅ All checks passed |
| `pytest -q`（106 用例） | ✅ 全部通过 |
| `git status` | ✅ working tree clean |
| `git diff --check` | ✅ 无空白错误 |

### 3.2 端到端集成测试覆盖

`tests/test_process_e2e.py::test_v0_1_stop_rule_safety_guarantees` 是 rc1
的核心质量门，覆盖：

- 零 `MINDFORGE_*` env 下完整跑通 `scan → process → status`
- 拦截 `httpx.Client.post`，证明 fake provider 完全离线
- source 文件 byte 级未改写
- 卡片 `status: ai_draft`、frontmatter 16 个关键字段齐全、可被 YAML 解析
- `state.json` 不含 `api_key` / `Authorization` / `raw_text` 等敏感字段
- `runs/*.jsonl` 中每条 `llm_call` 字段严格在白名单内（15 字段）

### 3.3 真实 provider smoke（M2.8）

详见 `docs/LLM_PROVIDER_CONFIG.md` §6.4：

- 沙箱在 `/tmp/mindforge-smoke-m28/`（非真实 vault）
- 三步链路全 ok（`llm ping` → `process --dry-run` → `process` 落卡）
- runs jsonl 全字段白名单内、无敏感泄漏
- 卡片 frontmatter 完整、value_score=9、stage_models 5 段全记录

### 3.4 Git / 安全卫生

- ✅ `.env` 在 `.gitignore`，`git ls-files` 确认未追踪
- ✅ `.mindforge/`、`runs/`、`*.log` 在 `.gitignore`，本地产物零提交
- ✅ commit message / 文档 / 测试 fixture 中无任何真实 api_key 字符串
- ✅ 默认 `active_profile=fake`，clone 后跑 `mindforge process` 不会调用真实 LLM

---

## 4. 进入 M3 的条件（**必须**显式确认）

M3 的核心是 **`human_approved` 反向同步**：人工把 Card frontmatter 的
`status` 改成 `human_approved`，下一次 `mindforge scan` / `status` 应能
识别并把该状态回写到 `state.json`。

进入 M3 之前必须满足：

1. ✅ v0.1.0-rc1 tag 已打、本文档已存在；
2. ⏳ **用户显式确认**进入 M3（"approve M2.9 → M3"）；
3. ⏳ **先设计 approve 协议，再实现**——先在 `docs/MINDFORGE_PROTOCOL.md` 写
   `human_approved` 的状态转移、字段约束、冲突处理（卡片被改名 / 被删除 /
   `status` 写错），再开 src 改动；
4. ⏳ **`human_approved` 必须是显式人工动作**——绝不允许 AI 自动批准、
   绝不允许 prompt 注入"建议晋升"导致默认晋升、绝不允许阈值自动晋升；
5. ⏳ M3 单测必须包含"AI 不可自动晋升"的反向断言。

---

## 5. 已知限制（非缺陷，是 v0.1 的边界）

- **PDF / Docx adapter 仅 stub**：v0.1 不做 OCR、不做表格抽取，相关 inbox 子目录可保留以约束未来扩展；
- **WebClip / ChatExport adapter 仅 stub**：未来 Obsidian Web Clipper / 对话导出可作为新 source_type 加入，但**不进** v0.1；
- **真实 provider smoke 仅覆盖非敏感测试输入**：v0.1 不承诺批量处理真实
  Cubox 收藏、不承诺工作文档安全边界（那是 M3+ 的反垃圾 / value_score
  策略要解决的事）；
- **不做成本 / token 统计聚合**：runs jsonl 已记录每 call 的 tokens_in / tokens_out，但 v0.1 不出周报、不出仪表盘；
- **不做复杂 provider fallback**：失败就是失败，落 `failed` 状态，由人决定下一步。这是 v0.1"执行层面克制"的一部分。

---

## 6. v0.1 路线图回顾（M0 → M2.9）

| Milestone | 主题 | 状态 | 关键交付 |
|---|---|---|---|
| M0 | 项目契约冻结 | ✅ | ROADMAP / PROTOCOL / V0_1_SCOPE / yaml 草案 |
| M1 | Source Ingestion MVP | ✅ | scanner / cubox+plain adapter / state.json |
| M1.5 | RunLogger preflight | ✅ | runs/*.jsonl 字段白名单 |
| M2 | LLM Processing MVP | ✅ | 5 stage pipeline + fake provider |
| M2.5 | Anthropic-compatible 加固 | ✅ | provider type 派发 + 安全默认 fake profile |
| M2.7 | `.env` 自动加载 + 新 CLI | ✅ | `env_loader.py` / `--profile` / `--dry-run` / `llm ping` |
| M2.8 | 真实 provider smoke 收口 | ✅ | lazy provider build + /tmp 沙箱 smoke 流程 |
| M2.9 | rc1 收口 | ✅ | 卡片模板清理 + 安全 E2E 测试 + 本文档 + tag |

→ M3 起再开新 Milestone。

---

## 7. 下一步建议（**仅供讨论，不在 rc1 范围**）

按 v0.1 边界，rc1 之后的合理下一步是 **设计 M3 的 `human_approved` 协议**
（先文档、再代码）。在协议未冻结前，建议：

- **不要** 立刻开发 M3 src 改动；
- **不要** 用真实 provider 批量处理 Cubox 收藏（那是 M3 验收完成之后的事）；
- **可以** 在本机用 fake profile 反复练手，熟悉 `scan / process / status` 的输出节奏；
- **可以** 收集一份"我希望未来卡片包含哪些字段、跳过哪些情况"的 backlog，作为 M3 协议设计的输入。

是否进入 M3 由人决定，不由 AI 决定。
