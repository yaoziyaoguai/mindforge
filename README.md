# MindForge

> 个人 AI 学习记忆库 — 把碎片资料加工成"可复用的长期知识"，而不是再造一个笔记工具。

MindForge 是一个**多源接入的 AI 知识加工管线**（Source Ingestion → Triage → Distill → Link → Apply → Review → Memory），它把来自 Cubox、PDF、Docx、网页剪藏、AI 对话导出、手写笔记等不同来源的素材，统一加工成结构化的 Knowledge Card，沉淀到本地 Obsidian Vault 里，并保留完整的证据链与可回放的 LLM 调用记录。

> 当前阶段：**Milestone 0 — 项目契约冻结**。本仓库目前**只交付契约文档与配置/Prompt/模板草案**，没有任何业务代码。
> 详见：[`docs/ROADMAP.md`](docs/ROADMAP.md)、[`docs/MINDFORGE_PROTOCOL.md`](docs/MINDFORGE_PROTOCOL.md)、[`docs/V0_1_SCOPE.md`](docs/V0_1_SCOPE.md)

---

## MindForge 是什么

- 一个**本地优先**的知识加工管线，串起"收藏 → 阅读 → AI 加工 → 长期记忆 → 项目复用"。
- 一个**多源接入**的 ingestion 框架：每种输入源都是一个 `SourceAdapter`，最终产出统一的 `SourceDocument`。
- 一个**可观察、可回放**的 LLM Pipeline：每次调用都记录 stage / model / prompt 版本 / 输入 hash，写到 `.mindforge/runs/*.jsonl`。
- 一个**强人审核**的知识库：所有 AI 产出默认 `status: ai_draft`，必须人工把 status 改为 `human_approved` 才进入长期记忆。

## MindForge 不是什么

- ❌ 不是 Obsidian 插件（v0.1 不做插件）。
- ❌ 不是 Cubox 同步工具（Cubox 只是众多输入源之一）。
- ❌ 不是云端 SaaS（数据在本地 Vault 与 `.mindforge/`）。
- ❌ 不是 RAG / 向量检索系统（v0.1 不做 embedding）。
- ❌ 不是自动复习调度器（v0.1 只生成复习题，不做 SM-2/FSRS）。

完整 in/out scope 见 [`docs/V0_1_SCOPE.md`](docs/V0_1_SCOPE.md)。

---

## 架构一图流

```
   Inbox (00-Inbox/Cubox, PDFs, Docs, WebClips, ChatExports, ManualNotes)
        │
        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ SourceAdapter（每源一个） → 统一输出 SourceDocument        │
  │   CuboxMarkdownAdapter, PlainMarkdownAdapter, ...           │
  └──────────────────────────┬──────────────────────────────────┘
                             ▼
   Scanner ▶ Triager ▶ Distiller ▶ Linker ▶ Writer ▶ Checkpointer
                             │
                             ▼
                ┌────────────────────────────────────┐
                │  LLMClient (profile + stage routing)│
                │  resolve_model_for_stage(stage)     │
                │  generate(stage, prompt, vars, ...) │
                └────────────────────────────────────┘
                             │
                             ▼
       20-Knowledge-Cards/<track>/*.md  (status: ai_draft → human_approved)
       .mindforge/state.json + runs/*.jsonl
```

## Roadmap（按 Milestone 推进）

| Milestone | 主题 | 状态 |
|---|---|---|
| M0 | 项目契约冻结 | ✅ 完成 |
| M1 | Source Ingestion MVP（不调 LLM） | ✅ 完成 |
| M1.5 | RunLogger preflight | ✅ 完成 |
| **M2** | LLM Processing MVP（5 个 stage） | ✅ 完成 |
| **M2.5** | Anthropic-compatible provider 接入 + 加固 | ✅ 完成 |
| **M2.7** | `.env` 自动加载 + `--profile` / `--dry-run` / `llm ping` | ✅ 完成 |
| **M2.8** | 真实 provider smoke 收口（lazy provider build + 单文件落卡验证） | ✅ 完成 |
| **M2.9** | v0.1 收口（卡片模板清理 + 安全 E2E 测试 + rc1 复盘） | ✅ rc1 |
| **M3** | Vault 输出与人工确认机制（writer + reconciler） | ✅ v0.1.0-rc2 |
| **M4** | 回顾 / 召回 / 项目记忆（review due + recall + project context） | ✅ v0.2.0 |
| **M4.1** | recall 排序/格式 + project context output/include flags | ✅ v0.2.1 |
| **M5.3** | project context 产品化（target / project profile / suggested prompt） | ✅ v0.2.2 |
| M5 | 高级集成（Obsidian 插件 / OCR / RAG / 调度）— [backlog 拆解](docs/M5_BACKLOG.md) | 🚫 明确推迟 |

每个 Milestone 的 **目标 / 交付物 / 验收标准 / 不做什么 / 停止规则 / 进入下一阶段条件** 都在 [`docs/ROADMAP.md`](docs/ROADMAP.md)。

## 快速导览

- 想知道**协议与数据契约** → [`docs/MINDFORGE_PROTOCOL.md`](docs/MINDFORGE_PROTOCOL.md)
- 想知道**v0.1 边界** → [`docs/V0_1_SCOPE.md`](docs/V0_1_SCOPE.md)
- 想知道**配置长什么样** → [`configs/mindforge.yaml`](configs/mindforge.yaml)、[`configs/learning_tracks.yaml`](configs/learning_tracks.yaml)、[`configs/llm.example.yaml`](configs/llm.example.yaml)
- 想知道**Prompt 长什么样** → [`prompts/`](prompts/)
- 想知道**Knowledge Card 长什么样** → [`templates/knowledge_card.md.j2`](templates/knowledge_card.md.j2)
- 想知道**Vault 目录怎么组织** → [`vault_template/`](vault_template/)

---

## LLM Provider 配置

MindForge 支持三类 provider，由 `configs/mindforge.yaml` 中模型的 `type`
字段派发：

- `fake`：默认安全路径，离线、确定性 schema 输出（用于测试 / CI / 开发）。
- `openai_compatible`：OpenAI / Ollama / LM Studio / vLLM 等。
- `anthropic_compatible`：Anthropic Claude / 阿里云 DashScope **Coding Plan**
  等以 Anthropic Messages API 协议暴露的服务。

**默认 `active_profile` 是 `fake`，绝不会调用真实模型**。切换到真实路径无需改 yaml：

```bash
# 1. 把 .env.example 复制为 .env，填入 base_url / api_key
cp .env.example .env

# 2. 校验 env 是否齐备（不发 HTTP，不消耗配额）
mindforge llm ping --profile anthropic_coding_plan

# 3. dry-run 跑 5 stage 但不写卡片、不写 state
mindforge process --profile anthropic_coding_plan --limit 1 --dry-run

# 4. 正式落地一张卡片
mindforge process --profile anthropic_coding_plan --limit 1
```

`.env` 由 `src/mindforge/env_loader.py` 在 CLI 入口处**静默**加载（永不打印 value）；
shell `export` 的环境变量优先于 `.env`。详细配置、安全约束、smoke test 流程见
[`docs/LLM_PROVIDER_CONFIG.md`](docs/LLM_PROVIDER_CONFIG.md)。

`.env` 已加入 `.gitignore`，**不会**被提交。

---

## 当前状态：v0.4.0（本地，review scheduling MVP）

- M0 → M5.5 + M5.6 全部本地 commit；v0.3.1 在 v0.3.0 BM25 之上把字段权重迁到 `mindforge.yaml` 并新增 hybrid 三路本地融合排序，详见 [`docs/V0_3_1_REVIEW.md`](docs/V0_3_1_REVIEW.md) / [`docs/M5_4_LEXICAL_RECALL_PROTOCOL.md`](docs/M5_4_LEXICAL_RECALL_PROTOCOL.md) §12。**未** push。
- v0.1 主链路完整：多源 → SourceDocument → 5 stage LLM pipeline →
  `ai_draft` Knowledge Card → state.json + runs/*.jsonl 证据链。
- v0.2.0（M4）新增：`mindforge review due` / `mindforge recall` / `mindforge project context`，全部**只读卡片 frontmatter 白名单**，不调 LLM、不读 .env、不索引。
- v0.2.1（M4.1）增量：
  - `recall`：多 token AND keyword、`--sort {default|review_after|updated_at|title|value_score}`、`--format {compact|table|markdown|json}`。
  - `project context`：`--output FILE`、`--include-actions/--no-actions`、`--include-review-due/--no-review-due`、`--include-next-step-prompt/--no-next-step-prompt`（next-step prompt 是**固定模板**，**不**调 LLM）。
- v0.2.2（M5.3）增量：**Better project context**（详见 [`docs/V0_2_2_REVIEW.md`](docs/V0_2_2_REVIEW.md)、协议见 [`docs/M5_3_PROJECT_CONTEXT_PROTOCOL.md`](docs/M5_3_PROJECT_CONTEXT_PROTOCOL.md)）：
  - `project context`：`--target {claude-code|copilot|codex|generic}`，按目标助手生成不同风格的 suggested prompt（**固定模板，不调 LLM**）。
  - 项目级 profile：`30-Projects/<name>.md` frontmatter 的 `description / default_target / principles / known_risks / preferred_workflow` 优先级最高；项目笔记**正文永不被读取**。
  - 数据源混合：项目 profile 优先 / Knowledge Cards 作为 supplementary，缺失自动降级。
  - JSON 输出升到 `version: 2`（旧字段不变，新字段 forward-compatible）。
  - markdown 始终输出 `## Excluded Content (safety guarantee)` 段，明示安全边界。
  - 项目 profile 示例见 [`vault_template/30-Projects/my-first-agent.md`](vault_template/30-Projects/my-first-agent.md)。
- v0.2.3 增量（M5.3 收尾 + M5.7，详见 [`docs/V0_2_3_REVIEW.md`](docs/V0_2_3_REVIEW.md)）：
  - **多 project 联合上下文**：`mindforge project context a b [c ...]`，输出 11 段固定结构（profiles / cross-project tracks / 不自动裁决的 cross-project principles & risks / 去重的 project-specific cards / shared actions / review due / multi-project suggested prompt / excluded content）；JSON 输出 `mode: "multi_project"`；缺 profile 的项目独立降级。
  - **30-Projects evidence block 幂等追加**：`mindforge project update-evidence <name> [--dry-run] [--include-drafts]`，把已确认卡片的安全摘要写入 `30-Projects/<name>.md` 的 `<!-- MINDFORGE:EVIDENCE:START/END -->` 受控区块；多次运行幂等；不写 raw_text / prompt / completion / secret；不修改 Knowledge Cards；profile 不存在时拒绝执行（不自动创建）。
  - **本地 only telemetry**（[`docs/M5_7_TELEMETRY_PROTOCOL.md`](docs/M5_7_TELEMETRY_PROTOCOL.md)）：默认开、永久 `local_only`，写入 `<state.workdir>/telemetry.jsonl`（已加入 `.gitignore`），字段白名单 10 项（event_name / command / success / duration_ms / result_count / project_count / card_count / error_code / timestamp / mindforge_version），**严禁** raw / card body / prompt / completion / api_key / 项目名 / 关键词；新增 `mindforge telemetry status` / `telemetry summary`；`enabled: false` 零开销。
- v0.2.4 增量（M5.2 + CLI polish #1，详见 [`docs/V0_2_4_REVIEW.md`](docs/V0_2_4_REVIEW.md)）：
  - **WebClipMarkdownAdapter**：真实 adapter 落地，吃 `00-Inbox/WebClips/*.md`（Obsidian Web Clipper / MarkDownload / SingleFile 风格）；title 三级 fallback（frontmatter > 首个 H1 > 文件名）；frontmatter 字段别名兼容中英常见键。
  - **ChatExportAdapter**：真实 adapter 落地，吃 `00-Inbox/ChatExports/*.md`（ChatGPT / Claude / Copilot 导出）；H2 + 加粗双风格 role 检测启发式；识别失败降级为 `degraded_plain_text` 不报错。详见 [`docs/M5_2_WEBCLIP_CHATEXPORT_PROTOCOL.md`](docs/M5_2_WEBCLIP_CHATEXPORT_PROTOCOL.md)。
  - **CLI polish #1**：新增 `mindforge version`（仅元数据，不漏 secret）；新增全局 `--debug`（默认抑制 traceback）；缺 config 时给出友好提示而非裸抛。
- v0.2.5 增量（M5.5 + M5.1 真实最小实装 + CLI polish #2，详见 [`docs/V0_2_FINAL_REVIEW.md`](docs/V0_2_FINAL_REVIEW.md)）：
  - **M5.5 Vault 友好度**：`mindforge vault index` / `vault links` / `vault refresh`；自动维护 `_index.md` / `_link_candidates.md`；**绝不**修改 Knowledge Card 正文；评分仅依赖 frontmatter 安全字段（track / projects / tags / source_type / title token）；遇到人手维护的 `_index.md` 自动降级写到 `_index.mindforge.md`。
  - **M5.1 PDF/Docx adapter（最小真实实装）**：lazy import `pypdf` / `python-docx`；未安装时给出 `OptionalDependencyError("pip install mindforge[pdf]")`；PDF 扫描件无文本层 → `PdfNoTextError`，**不**做 OCR、**不**降级为空卡片。通过 `[project.optional-dependencies]` 暴露 `pdf` / `docx` / `docs` extras，默认 OFF。
  - **CLI polish #2**：全局 `--vault PATH` 临时覆盖 `vault.root`（不改 yaml）；`mindforge doctor` 健康检查（Python / 平台 / 配置 / vault 目录 / optional deps / `.env` 是否在 `.gitignore` / git status 敏感产物嗅探）；**不**读 `.env` 内容。
  - **新文档**：[`docs/CLI_COMPLETION.md`](docs/CLI_COMPLETION.md)、[`docs/V0_2_FINAL_REVIEW.md`](docs/V0_2_FINAL_REVIEW.md)。
- v0.2.6 增量（init + approval workflow + doctor 增强，详见 [`docs/V0_2_6_REVIEW.md`](docs/V0_2_6_REVIEW.md)）：
  - **`mindforge init`**：一键铺 vault 骨架 + configs + `.env.example`；自动改写新 yaml 中的 `vault.root`；幂等；`--dry-run` 预览；`--force` 仅覆写 MindForge 自带模板，**绝不**碰用户数据。
  - **Approve workflow**：保留 `approve --card`；新增 `approve --source-id`、`approve --all [--dry-run|--confirm] [--limit N]`、`approve list [--status … --project … --track … --format table|json]`（仅安全字段；不读卡片正文）。
  - **Doctor 增强**：actionable hints — vault 缺目录建议 `mindforge init`、ai_draft 堆积建议 `approve list`、active_profile 配置错误显式提示等；仍**不**读 .env 内容。
  - **新文档**：[`docs/ONBOARDING_SMOKE.md`](docs/ONBOARDING_SMOKE.md)、[`docs/V0_2_6_REVIEW.md`](docs/V0_2_6_REVIEW.md)。
- v0.3.0 增量（BM25 本地词法检索，详见 [`docs/V0_3_0_REVIEW.md`](docs/V0_3_0_REVIEW.md) / [`docs/M5_4_LEXICAL_RECALL_PROTOCOL.md`](docs/M5_4_LEXICAL_RECALL_PROTOCOL.md)）：
  - **`mindforge recall --query "…" [--explain]`**：BM25 评分排序，字段加权（title=5 / track=4 / projects=4 / tags=3 / body_summary=1 …），`--explain` 给字段贡献分。
  - **`mindforge index rebuild` / `mindforge index status`**：本地索引落 `.mindforge/index/bm25.json`（被 .gitignore 挡），原子写，含 fresh / stale 检测。
  - **安全核心**：**只**索引 Knowledge Card 的 frontmatter 安全字段 + 白名单 body section（`## AI Summary` / `## Action Items` / `## Principles` / `## Known Risks`）；**绝不**索引 `## Source Excerpt` / `## Human Note` / raw source / prompts / completions / runs / state.json / .env / API key。
  - **仍然不做**：RAG / embedding / 向量库 / 远程调用 / LLM 调用。BM25 是纯本地词法检索。
- v0.3.1 增量（BM25 配置化 + hybrid 排序，详见 [`docs/V0_3_1_REVIEW.md`](docs/V0_3_1_REVIEW.md) / [`docs/M5_4_LEXICAL_RECALL_PROTOCOL.md`](docs/M5_4_LEXICAL_RECALL_PROTOCOL.md) §12）：
  - **`configs/mindforge.yaml.search`**：BM25 字段权重 / `k1` / `b` / hybrid 三路权重全可调，校验严格（负数 / b∉[0,1] 直接 fail-fast）。
  - **`mindforge recall --ranking hybrid [--explain]`**：BM25 + value_score + review_due 三路本地融合；`--explain` 打印每条命中的三路分量与 `final_score`。
  - **`config_hash`**：索引内嵌配置指纹；`mindforge index status` / `mindforge doctor` 自动检测"配置漂移"并提示 `mindforge index rebuild`。recall 路径若发现漂移，自动用当前配置内存重建（绝不静默用旧权重打分）。
  - **仍然不做**：RAG / embedding / LLM 调用 / 远程上传。hybrid 是纯本地规则。
- v0.3.2 增量（recall UX polish + index info JSON，详见 [`docs/V0_3_2_REVIEW.md`](docs/V0_3_2_REVIEW.md)）：
  - **`recall --weight-bm25/--weight-value-score/--weight-review-due`**：本次运行覆盖 hybrid 权重，**不**写回 yaml；非法权重（负数 / 全 0）fail-fast。
  - **`recall --explain --format json`**：新增 `weight_source` / `active_weights` / `index_stale` / per-item `why_this_matched` / `matched_terms` / `matched_fields` / `ranking_mode`，便于脚本与回归。
  - **`mindforge index info [--json]`** + **`mindforge index status --json`**：稳定 schema (version=1)，给 doctor/外部脚本消费。
  - **doctor 增强**：仅有 ai_draft 时提示 `recall --include-drafts`。
- v0.4.0 增量（review scheduling MVP，详见 [`docs/V0_4_0_REVIEW.md`](docs/V0_4_0_REVIEW.md) / [`docs/V0_4_REVIEW_SCHEDULING_PROTOCOL.md`](docs/V0_4_REVIEW_SCHEDULING_PROTOCOL.md)）：
  - **`mindforge review schedule`**：未来 N 天复习计划，按日期分组，markdown / json；过期归"今天"；`--include-missing-review-after` 可纳入新卡。
  - **`mindforge review backlog`**：overdue / today / upcoming / missing 四桶。
  - **`mindforge review stats [--json]`**：聚合统计（result_breakdown / 平均 review 次数）。
  - **`review mark --dry-run --note "..."`**：预览不写文件；可选**单行 ≤200 字符**备注，写入 frontmatter `last_review_note`，**绝不**进 body。
  - **仍然不做**：SM-2 / FSRS / 后台调度 / 系统通知 / LLM。
- 默认 `active_profile=fake`，clone 后跑 `mindforge process` 不会调用真实 LLM。
- `tests/test_process_e2e.py::test_v0_1_stop_rule_safety_guarantees` 是 rc1
  的核心安全契约：零 env / 拦截 HTTP / 字段白名单 / source 不被改写。
- M2.8 已用 `anthropic_coding_plan` profile 在 `/tmp` 沙箱完成单文件真实
  smoke；详见 [`docs/LLM_PROVIDER_CONFIG.md`](docs/LLM_PROVIDER_CONFIG.md) §6.4。
- 复盘：[`V0_1_RC1`](docs/V0_1_RC1_REVIEW.md) → [`V0_2_0`](docs/V0_2_0_REVIEW.md) → [`V0_2_1`](docs/V0_2_1_REVIEW.md) → [`V0_2_2`](docs/V0_2_2_REVIEW.md) → [`V0_2_3`](docs/V0_2_3_REVIEW.md) → [`V0_2_4`](docs/V0_2_4_REVIEW.md) → [`V0_2_FINAL` (v0.2.5)](docs/V0_2_FINAL_REVIEW.md) → [`V0_2_6`](docs/V0_2_6_REVIEW.md) → [`V0_3_0`](docs/V0_3_0_REVIEW.md) → [`V0_3_1`](docs/V0_3_1_REVIEW.md) → [`V0_3_2`](docs/V0_3_2_REVIEW.md) → [`V0_4_0`](docs/V0_4_0_REVIEW.md)。
- 下一步候选见 [`docs/M5_BACKLOG.md`](docs/M5_BACKLOG.md)；建议先用满 1–2 周再决定。
