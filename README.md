# MindForge

**本地优先的 AI 学习记忆工具。** 把本地文件/文件夹变成可审批的知识卡片，支持 Review、Library、Trash、Recall 和 Processing Workflow 可视化。

- 数据都在你的本地 vault
- AI 只生成草稿 (`ai_draft`)，你必须显式审批才能成为正式知识 (`human_approved`)
- API key 只存在本地 secret store 或环境变量，绝不进 Git、不进 YAML、不进 Web 前端
- Web 控制台 + CLI 双入口，同一套 service 层

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [Web 控制台](#web-控制台)
4. [配置模型](#配置模型)
5. [添加 Source 并生成 AI Draft](#添加-source-并生成-ai-draft)
6. [Review 与 Approve](#review-与-approve)
7. [Library（知识库）](#library知识库)
8. [Trash（回收站）](#trash回收站)
9. [Processing Workflow 与 Prompt](#processing-workflow-与-prompt)
10. [CLI 常用命令](#cli-常用命令)
11. [架构概览](#架构概览)
12. [配置文件与本地数据](#配置文件与本地数据)
13. [安全原则](#安全原则)
14. [当前限制](#当前限制)
15. [Roadmap](#roadmap)
16. [开发者](#开发者)

---

## Quick Start

```bash
# 1. 克隆项目
git clone <repo-url>
cd mindforge

# 2. 安装
pip install -e .

# 3. 初始化（在空目录或项目目录里运行）
mkdir -p /tmp/mindforge-first-run && cd /tmp/mindforge-first-run
mindforge init

# 4. 启动 Web 控制台
mindforge web
```

浏览器打开 `http://127.0.0.1:8765`。

First-run path details:
- `cd /tmp/mindforge-first-run` makes that directory the project root.
- `vault.root` 默认是相对 project root 的 `vault`，所以新项目 only
needs `00-Inbox/` plus the generated `configs/mindforge.yaml`.
- Vault resolution is `cwd-first / vault-first`: explicit `--vault`, cwd/ancestor vault, project-root-relative, then active-vault-relative.

Configure a real model in Web Setup. The YAML shape is `llm.models/default_model/routing`; advanced env deployments can use `MINDFORGE_LLM_API_KEY`. Model type is an API protocol type such as `openai_compatible`, `openai`, `anthropic`, or `anthropic_compatible`.

```bash
mindforge watch add /path/to/folder --every manual
mindforge approve list
mindforge approve 1 --confirm
mindforge recall --query "MindForge"
```

如果想先体验零配置 tour：

```bash
mindforge demo
```

---

## 核心概念

| 概念 | 说明 |
|------|------|
| **Vault** | 本地工作区，包含 Source（原始资料）、Knowledge Cards（知识卡片）、Projects 等 |
| **Source** | 原始输入文件（Markdown、TXT 等），放在 `00-Inbox/` 下 |
| **AI Draft** | AI 从 source 自动生成的知识草稿，状态为 `ai_draft` |
| **Approved Card** | 你显式审批后的正式知识卡片，状态为 `human_approved` |
| **Library** | 所有 approved card 的可浏览知识库 |
| **Trash** | 安全回收站——移入 Trash 只移除卡片，**不删除 source 文件** |
| **Processing Workflow** | 固定五段加工流程：初筛 → 提炼 → 关联建议 → 复习问题 → 行动项提取 |

**关键边界：AI 只生成草稿，审批是人的事。**

---

## Web 控制台

启动后打开 `http://127.0.0.1:8765`，可用页面：

| 页面 | 用途 |
|------|------|
| **Home** | 状态总览、下一步建议 |
| **Setup** | 配置模型、Processing Workflow 查看、添加 source |
| **Sources** | 管理 watched sources、Process now |
| **Review** | 查看 AI 草稿、编辑、审批 |
| **Library** | 浏览已审批知识卡片 |
| **Trash** | 查看和恢复已移除的卡片 |
| **Recall** | 本地词法检索（BM25） |

---

## 配置模型

### Web Setup（推荐）

1. 打开 **Setup** 页面
2. 点击 **\+ Add model**
3. 填写：
   - **Model id**: 模型别名，如 `main`、`claude`
   - **Type**: `anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`
   - **Base URL**: 模型 endpoint
   - **Model**: 模型名，如 `claude-3-5-haiku-latest`
   - **API key**: 输入你的 API key
4. 保存

API key 会存入本地 **secret store**（`.mindforge/secrets.json`，已 gitignore），不会写入 YAML。Web 和 CLI 只显示脱敏后的 key（如 `sk-****abcd`）。

### Default Model 与 Model Routing

- **Default model**: 所有 workflow step 默认使用的模型
- **Model routing**: 可选，每个 workflow step（Triage / Distill / Link Suggestion / Review Questions / Action Extraction）可指定不同模型

### 支持的模型类型

| Type | 适用场景 |
|------|---------|
| `openai` | OpenAI 官方原生 API（默认 base_url: https://api.openai.com/v1） |
| `openai_compatible` | 兼容 OpenAI 协议的 endpoint（Ollama、vLLM、DeepSeek、API 中转等） |
| `anthropic` | 原生 Anthropic API |
| `anthropic_compatible` | 兼容 Anthropic 协议的 endpoint（DashScope、OpenRouter 等） |

Local 模型（Ollama、LM Studio 等）通过 `openai_compatible` + `api_key_optional: true` 配置。

### 环境变量模式（Advanced）

如果不使用 secret store，也可以设置环境变量：

```bash
export MINDFORGE_LLM_API_KEY="<your-key>"
```

并在 YAML 中声明 `api_key_env: MINDFORGE_LLM_API_KEY`。**不建议普通用户使用此方式** —— secret store 更简单安全。

---

## 添加 Source 并生成 AI Draft

### Source 可以是什么

- 单个 Markdown / TXT 文件
- 整个文件夹（递归扫描子文件夹）
- 支持 Cubox Markdown、Plain Markdown、WebClip、ChatExport 等格式

### Web 方式

1. 打开 **Setup** 页面，在 "Add a file or folder" 区域输入路径
2. Frequency 选 **Manual**（手动触发）
3. 点击 **Add and process now** —— 这会调用真实 LLM 生成 `ai_draft`

### CLI 方式

```bash
# 添加并立即处理（注册为 watched source）
mindforge watch add /path/to/folder --every manual

# 一次性导入（不注册为 watched source）
mindforge import /path/to/file.md
```

### Frequency 说明

| Frequency | 行为 |
|-----------|------|
| `manual` | 不自动扫描，需手动 Process now |
| `hourly` / `daily` / `weekly` | 按周期自动扫描 |
| `every 1h` / `6h` / `12h` / `24h` | 精确间隔 |

### Source 变更语义

- Source 内容变化 → 可生成新 draft
- Source 被删除 → 在 diagnostics 中标记 Missing，**不删除已生成的 knowledge card**
- Stop watching → 只移除 registry 记录，不删除 source 和 cards

---

## Review 与 Approve

### Review（查看草稿）

Web: 打开 **Review** 页面，左侧列表选 card，右侧可阅读、编辑 body。

CLI:

```bash
mindforge approve list          # 列出待审批草稿
mindforge approve show --card <path>  # 查看草稿内容
```

### Approve（显式审批）

**审批必须显式确认。**

Web: Review 页面 → 确认 source 已 review → 点击 **Approve**。

CLI:

```bash
mindforge approve 1 --confirm   # 用短编号审批
```

审批后：
- Card 状态变为 `human_approved`
- 出现在 Library 中
- 可被 Search/Recall 检索
- Source 文件移动到 `00-Inbox/_processed/`（保留证据）

---

## Library（知识库）

Web: **Knowledge Library** 页面浏览所有 approved card。

CLI:

```bash
mindforge library list           # 列出知识库卡片
mindforge library show <ref>     # 查看单张卡片
mindforge library stats          # 统计摘要
```

每张卡片保留完整 provenance：source path、strategy id/version、prompt versions、model routing per step、run id。

---

## Trash（回收站）

Move to Trash 是安全移除：卡片文件移动到 `90-Archive/Trash/Knowledge-Cards/`，**source 文件不受影响**。

### Web

- Review / Library 中的卡片有 **Move to Trash** 按钮
- 点击后确认对话框说明"只移除卡片，不删除 source 文件"
- **Trash** 页面可查看、预览和 Restore

### CLI

```bash
# 移入 Trash
mindforge trash move <card-path> --confirm

# 查看 Trash
mindforge trash list
mindforge trash show <trash-path>

# 恢复
mindforge trash restore <trash-path> --confirm
```

永久删除当前未实现。Restore 后卡片回到 Review 或 Library，状态恢复为移入前的 `ai_draft` 或 `human_approved`。

---

## Processing Workflow 与 Prompt

Web Setup 的 **Processing workflow** 区域展示了当前的固定五段 **Knowledge Card Workflow**：

| Step | 中文 | 做什么 |
|------|------|--------|
| Triage | 初筛 | 评估 source 是否值得生成知识卡片，给出 track / value_score |
| Distill | 提炼 | 从 source 提取核心知识内容，生成卡片草稿主体 |
| Link Suggestion | 关联建议 | 建议可能相关的主题、项目或已有知识链接 |
| Review Questions | 复习问题 | 生成用于后续回忆和自测的问题 |
| Action Extraction | 行动项提取 | 提取可跟进的行动项或待办 |

每个 step 可以：
- 选择不同的模型
- **View prompt** —— 点击查看当前使用的 prompt 全文（只读）

### Prompt 查看

CLI:

```bash
mindforge prompts list            # 列出所有 prompt
mindforge prompts show triage@v1  # 查看 triage 的 v1 prompt
```

当前 prompt 是只读的。Prompt 版本可在 config 中配置（`prompts.triage_version: v1`），prompt override 和编辑功能是后续计划。

---

## CLI 常用命令

| 场景 | 命令 | 说明 |
|------|------|------|
| 启动 Web | `mindforge web` | 启动本地控制台 `http://127.0.0.1:8765` |
| 零配置 demo | `mindforge demo` | 60 秒安全 tour |
| 初始化 | `mindforge init` | 创建 vault 骨架 + config |
| 查看状态 | `mindforge status` | workspace / vault / draft / recall 汇总 |
| 诊断 | `mindforge doctor` | 环境 + 配置 + 风险快照 |
| 添加 source | `mindforge watch add <path>` | 注册 watched source 并立即处理 |
| 一次性导入 | `mindforge import <path>` | 处理当前内容，不注册为 watched |
| 查看 watched | `mindforge watch list` | 列出所有 watched sources |
| 扫描 | `mindforge watch scan --all` | 扫描 due sources |
| 停止 watching | `mindforge watch delete <ref>` | 只删 registry，不删 source/cards |
| 查看 drafts | `mindforge approve list` | 列出待审批 ai_draft |
| 显示 draft | `mindforge approve show --card <path>` | 查看草稿 metadata |
| 审批 | `mindforge approve 1 --confirm` | 显式审批（短编号） |
| 知识库列表 | `mindforge library list` | Library card metadata |
| 知识库详情 | `mindforge library show <ref>` | 查看单张卡片 |
| Trash 列表 | `mindforge trash list` | 查看已移除卡片 |
| Trash 移入 | `mindforge trash move <path> --confirm` | 安全移入 Trash |
| Trash 恢复 | `mindforge trash restore <path> --confirm` | 从 Trash 恢复 |
| 查看策略 | `mindforge strategies list` | 只读查看内置策略元数据 |
| 查看 prompt | `mindforge prompts show triage` | 只读查看 prompt 全文 |
| 检索 | `mindforge recall --query "关键词"` | 本地 BM25 词法检索 |
| 每日入口 | `mindforge today` | 只读汇总待办/复习/索引 |
| 版本信息 | `mindforge version` | 版本 + 配置摘要（不含 secret） |

---

## 架构概览

```
SourceAdapter                ← 文件类型适配（Markdown/TXT/CSV/...）
  → SourceDocument           ← 统一中间表示
  → Processing Pipeline      ← 固定五段 Knowledge Card Workflow
    ├── Triage               ← 初筛（value_score + track）
    ├── Distill              ← 提炼（card body）
    ├── Link Suggestion      ← 关联建议
    ├── Review Questions     ← 复习问题
    └── Action Extraction    ← 行动项
  → AI Draft (.md)           ← frontmatter + body，status = ai_draft
  → Human Approval           ← 显式 approve --confirm
  → Approved Card            ← status = human_approved
  → Library / Recall / Trash ← 后续消费
```

**分层边界**：

| 层 | 职责 | 不做什么 |
|----|------|---------|
| Web（React/FastAPI） | UI + API | 不直接操作文件，不碰 raw secret |
| CLI（Typer） | 命令入口 | 不绕过 service，不直接改 YAML |
| Service（Python） | 业务语义 | 审批、trash、library、strategy 等规则 |
| Provider（LLM） | 调用 LLM | 不在前端运行，不打印 raw key |
| Secret Store | 保存 API key | 已被 gitignore，不入 YAML/Web/CLI 输出 |

---

## 配置文件与本地数据

### 配置文件

- **`configs/mindforge.yaml`**: 非 secret 的用户配置（vault 路径、模型定义、prompt 版本等）。运行时会 merge 内置 defaults。
- **`configs/mindforge_example.yaml`**: 新用户参考配置模板，展示完整的 llm.models/routing/wiki 结构。不含 API key。
- **`.mindforge/secrets.json`**: Web 用户输入的 API key 本地存储。**已 gitignore**。
- **`.env`**: Legacy/Advanced 环境变量模式（不推荐普通用户使用）。**已 gitignore，不要提交**。

### 本地运行时数据

`.mindforge/` 目录（已 gitignore）：

| 文件/目录 | 用途 |
|-----------|------|
| `secrets.json` | API key 本地存储 |
| `state.json` | 处理状态 checkpoint |
| `watched_sources.json` | Watched source registry |
| `runs/` | 运行日志 |
| `telemetry.jsonl` | 本地使用统计（不上传） |

### 旧配置兼容

Legacy 配置（`llm.active_profile` / `llm.profiles`）仅用于兼容读取旧项目。新用户请勿使用；新写入始终使用 `llm.models` / `llm.default_model` / `llm.routing`。

---

## 安全原则

| 原则 | 实现 |
|------|------|
| API key 不进 Git | `.env` + `.mindforge/` 均已 gitignore |
| API key 不进 Web 前端 | Secret store 只在后端 runtime；API 只返回 masked 值 |
| API key 不进 README | ✅ |
| AI 不自动审批 | 所有 approve 路径必须显式 `--confirm` |
| Source 删除不删知识 | Stop watching + Move to Trash 都不动 source 文件 |
| Trash 是安全移除 | 不是永久删除；Restore 可用 |
| 本地优先 | 不联网、不上传 telemetry、纯本地 BM25 检索 |
| 不做 RAG/embedding | 当前检索是词法 BM25，不是向量搜索 |

---

## 当前限制

| 限制 | 说明 |
|------|------|
| **固定五段 workflow** | 不支持自定义 step 数量/顺序 |
| **Prompt 只读** | 可查看不可编辑（override 是后续计划） |
| **一个 production strategy** | `knowledge_card` 是唯一的 production-ready workflow |
| **无 permanent delete** | Trash 只做安全移除，永久删除未实现 |
| **无后台 daemon** | Watch frequency 依赖手动 `watch scan` 或 cron 触发 |
| **不做 RAG/embedding** | BM25 词法检索是当前唯一检索路径 |
| **不做 Obsidian plugin** | MindForge 是独立本地工具 |

---

## Roadmap

### 近期

- **Prompt override / restore default**: 允许用户 override prompt 并安全回退
- **Web Prompt 编辑查看增强**: prompt version diff、manifest 可视化
- **CLI/Web parity polish**: 补齐 CLI trash 和 watch frequency edit
- **README / docs polish**: 持续更新

### 中期

- **Workflow step atom registry**: 为自定义 workflow 做架构准备
- **内置 workflow 组合**: 允许在现有多套策略中选择
- **Wiki View**: 从 approved cards 自动生成可浏览的知识 wiki
- **Better recall/review**: recall 增强、复习调度改进
- **Structured source support**: 增强 CSV/JSON/PDF 等 adapter

---

## 开发者

### 项目结构

```
mindforge/
├── src/mindforge/          # 核心 Python 包（service、config、pipeline 等）
├── src/mindforge_web/      # FastAPI Web 后端（router、schema、facade）
├── web/                    # React/Vite 前端（TypeScript）
├── tests/                  # 测试
├── prompts/                # Prompt 模板（用户可见）
├── templates/              # Card 输出模板（Jinja2）
├── configs/                # 用户配置（mindforge.yaml 等）
└── docs/                   # 开发者文档
```

### 运行测试

```bash
ruff check .
python -m pytest
cd web && npm run build
```

### Service 层入口

| Service | 文件 |
|---------|------|
| Config | `src/mindforge/config.py` |
| Approval | `src/mindforge/approval_service.py` |
| Library | `src/mindforge/library_service.py` |
| Trash | `src/mindforge/trash_service.py` |
| Recall | `src/mindforge/recall_service.py` |
| Secret Store | `src/mindforge/secret_store.py` |
| Strategy Registry | `src/mindforge/strategies/registry.py` |
| Prompt Runtime | `src/mindforge/prompts_runtime.py` |
| Web Config Service | `src/mindforge_web/services/web_config_service.py` |
| Web Facade | `src/mindforge_web/services/web_facade.py` |

CLI 和 Web Router 是薄适配器，不承载业务逻辑。

### Developer Testing

This section is for tests, CI fixtures, and historical dogfooding evidence. It is not the recommended first-run path for normal users.

- Test doubles fake the LLM response, not the extraction strategy; they are not product providers or recommended extraction strategies.
- MindForge is local-first and single-user by default.
- `fake provider` and legacy `active_profile` appear only as test/dev compatibility language, not as the user setup path.
- A real provider is real provider opt-in, never implicit.
- Advanced / Troubleshooting may still mention scan/process for diagnostics; `watch/import/review/approve/library/trash/wiki` are the product surface.
- Standard Quality Gate: `ruff check`, `pytest`, and `git diff --check`.

First Status Commands:
- `mindforge status`
- `mindforge doctor`
- `mindforge commands`

Strategy discovery:
- `mindforge strategies list`
- `mindforge strategies show knowledge_card`
- `mindforge prompts list`
- `mindforge prompts show triage@v1`
- Strategy lifecycle statuses: implemented, preview, planned. A planned strategy is visible for roadmap clarity but is not executable.
- Custom strategy loading uses explicit path only: `--custom-path`. Loading is not execution, discovery is not execution, and preview is not implementation.
- Custom definitions are declarative preview definitions: no arbitrary python, no shell, no implicit scanning of home folders or private vaults.
- Preview packet is review-only, not ai_draft, not human_approved, and any future implementation still requires explicit approval.
- Preview packet is review-only and not `human_approved`.
- Preview to future implementation requires a reviewed built-in implementation path; no arbitrary python and no shell strategy are accepted.
- Validation error output is for reading a definition, not for executing it.

Card provenance and prompt visibility:
- Cards record source content hash and strategy/prompt/source/provider provenance.
- `strategy.active` chooses extraction strategy; `llm.default_model/routing` chooses model use.

Safe Real Dogfood and legacy readiness notes:
- Use only a disposable, non-sensitive vault copy: "disposable, non-sensitive vault copy".
- `mindforge dogfood quickstart`, `mindforge dogfood readiness --vault PATH`, `mindforge dogfood preflight /tmp/project-vault --declare-non-sensitive`.
- `mindforge cubox`, `mindforge obsidian`, `mindforge obsidian stage`.
- Limit examples: `--limit 5`, `--limit 20`.
- MindForge does not support full Cubox account sync; there is no `--all` ingestion.
- Rollback rule: use `git restore` for local experiment files and keep dogfood runs disposable.
- Real Provider Opt-In and real-opt-in require explicit user configuration; this is explicit opt-in, not default execution. 真实 LLM 只在你配置 `MINDFORGE_LLM_API_KEY` and intentionally start a real path; use `--allow-real` only for an intentional real smoke.
- This does not call a real LLM, does not call the real Cubox API, does not print `.env` secret values, does not automatically modify a real private vault, and does not auto-approve.
- No automatic approve.
- No `.env`.
- no `.env` is read, no real LLM, no real cubox, no write occurs into a real obsidian vault, no human_approved card is generated by automation, no custom strategy is executed, no tag, no force push, every dogfooding session must be a dry-run by default.
- Human decision gate, local-first privacy contract, fixtures for CI, Real ≠ Approved, Human Decision Gate Map.
- Proposal artifacts are review-only: preview packets, readiness checks, real smoke.
- Deferred gates use sample folder, no-persist, dry-run, diff preview, backup.

Obsidian boundary notes:
- No formal Obsidian note writes.
- No formal Obsidian notes are written.
- no formal obsidian notes are written.
- no Obsidian formal-note writes.
- No default real LLM path.
- No `.env`, real LLM, real Cubox API, or formal Obsidian write happens in dry-run readiness.
- No telemetry upload.
- Obsidian uses a staged workflow: staged export -> diff preview -> backup -> explicit confirmation.
- Obsidian scan uses include/exclude rules.
- No RAG / embedding.
- not RAG.
- not embedding.
- No Obsidian plugin.
- no Obsidian vault was written.
- no full sync into a private vault.
- `mindforge obsidian next --vault /path/to/project-vault`
- `mindforge obsidian doctor --vault /path/to/project-vault`
- `mindforge obsidian scan --vault /path/to/project-vault --limit 20`
- `mindforge obsidian links --vault /path/to/project-vault`
- `mindforge obsidian stage --vault /path/to/project-vault --source <note.md> --dry-run`
- `mindforge obsidian preflight --vault /path/to/project-vault --manifest`
- `<export>.manifest.json`

Future gates and release readiness:
- G1 Real Cubox ingestion
- G2 Real Obsidian formal-note write
- G3 Approval UX
- G4 Custom executable strategy runtime
- G5 RAG / embedding / semantic merge
- G6 Public release / git tag
- Real Cubox, Real Cubox ingestion, Real Obsidian, Custom executable strategy runtime, RAG / embedding / semantic merge, Public release.
- Closed stages: Web first slice, Real Data CLI Usability, Documentation cleanup.
- Not true / future-gated: Real LLM enabled by default; Real Cubox API calls enabled by default; Hidden automatic approval.

### 相关文档

- [DESIGN.md](DESIGN.md): Web 设计系统
- [docs/TESTING.md](docs/TESTING.md): 质量门和 smoke check
- [docs/LLM_PROVIDER_CONFIG.md](docs/LLM_PROVIDER_CONFIG.md): 真实 provider opt-in
- [docs/ROADMAP_COMPLETION_LEDGER.md](docs/ROADMAP_COMPLETION_LEDGER.md): 功能完成台账
