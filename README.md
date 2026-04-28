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
| **M2.9** | v0.1 收口（卡片模板清理 + 安全 E2E 测试 + rc1 复盘） | 🟢 当前 / rc1 |
| M3 | Vault 输出与人工确认机制 | ⏳ 待启动 |
| M4 | 回顾、召回与项目记忆（v0.2/v0.3 候选） | ⏳ |
| M5 | 高级集成（Obsidian 插件 / OCR / RAG ...） | 🚫 v0.1 不做 |

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

## 当前状态：v0.1.0-rc1（本地）

- M0 → M2.9 全部已本地 commit，**未** push。
- v0.1 主链路完整：多源 → SourceDocument → 5 stage LLM pipeline →
  `ai_draft` Knowledge Card → state.json + runs/*.jsonl 证据链。
- 默认 `active_profile=fake`，clone 后跑 `mindforge process` 不会调用真实 LLM。
- `tests/test_process_e2e.py::test_v0_1_stop_rule_safety_guarantees` 是 rc1
  的核心安全契约：零 env / 拦截 HTTP / 字段白名单 / source 不被改写。
- M2.8 已用 `anthropic_coding_plan` profile 在 `/tmp` 沙箱完成单文件真实
  smoke；详见 [`docs/LLM_PROVIDER_CONFIG.md`](docs/LLM_PROVIDER_CONFIG.md) §6.4。
- v0.1 收口复盘见 [`docs/V0_1_RC1_REVIEW.md`](docs/V0_1_RC1_REVIEW.md)。
- 进入 M3（人工 `human_approved` 反向同步）需用户**显式**确认；先设计协议再写代码。
