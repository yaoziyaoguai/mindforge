# MindForge

**本地优先的 AI 学习记忆工具。** 把本地文件/文件夹变成可审批的知识卡片，提供 Web 控制台 + CLI 双入口。

核心链路：

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                          ├── Library
                                                          ├── Recall (BM25)
                                                          ├── Trash / Restore
                                                          └── Wiki (deterministic / LLM)
```

- 数据都在本地 vault，不做 RAG、不做 embedding、不连向量数据库
- AI 只生成草稿 (`ai_draft`)，必须显式审批才能成为正式知识 (`human_approved`)
- API key 存本地 secret store (`.mindforge/secrets.json`)，不进 Git、不进 YAML、不进 Web 前端
- Web 控制台 (React) + CLI (Typer) 同一套 Python service 层

---

## 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [Web 控制台](#web-控制台)
4. [配置模型](#配置模型)
5. [路径规则](#路径规则)
6. [添加 Source 并生成 AI Draft](#添加-source-并生成-ai-draft)
7. [Review 与 Approve](#review-与-approve)
8. [Library（知识库）](#library知识库)
9. [Trash（回收站）](#trash回收站)
10. [Wiki](#wiki)
11. [Processing Workflow](#processing-workflow)
12. [CLI 常用命令](#cli-常用命令)
13. [安全原则](#安全原则)
14. [当前限制与不做的事](#当前限制与不做的事)
15. [试用建议](#试用建议)
16. [开发者](#开发者)

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge

# 2. 安装
python -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. 启动 Web 控制台
mindforge web
```

浏览器打开 `http://127.0.0.1:8765`。

首次运行时，MindForge 会在本地创建 `configs/mindforge.yaml`。这是本机 runtime config，已被 gitignore，不要提交；提交用模板是 `configs/mindforge_example.yaml`。API key 不写 YAML，后续通过 Web Setup 写入本地 `local secret store`（`.mindforge/secrets.json`）。

**配置真实模型（必须）：**

1. 打开 **Setup** 页面 → **Add model**
2. 填写 model id（如 `main`）、type（anthropic/openai/anthropic_compatible/openai_compatible）、base url、模型名、API key
3. 保存

**添加第一个 source：**

1. 在 Setup 页的 "Add a file or folder" 输入框粘贴文件/文件夹的**绝对路径**
2. 推荐先用 1-2 个 Markdown 文件测试
3. 点击 **Add and process now** → 立即启动后台 processing run；完成后在 Sources 查看结果，生成的 draft 会出现在 Review

**Review → Approve：**

1. 打开 **Review** 页面，查看 AI 生成的知识草稿
2. 确认内容无误后点击 **Approve**
3. Approved card 进入 Library，可被 Recall 检索，也会参与后续手动 Wiki rebuild

CLI 快速体验：

```bash
mindforge watch add /path/to/folder --every manual
mindforge approve list
mindforge approve 1 --confirm
mindforge recall --query "MindForge"
```

### First-run 路径（Advanced）

如果需要在任意目录创建新项目：

```bash
mkdir -p /tmp/mindforge-first-run && cd /tmp/mindforge-first-run
mindforge init
```

- `cd /tmp/mindforge-first-run` 会让该目录成为 project root。
- `vault.root` 默认是相对 project root 的 `vault`，所以新项目只需要 `00-Inbox/` 和生成的 `configs/mindforge.yaml`。
- Vault resolution is `cwd-first / vault-first`: explicit `--vault`, cwd/ancestor vault, project-root-relative, then active-vault-relative.

Model type is an API protocol type such as `openai_compatible`, `openai`, `anthropic`, or `anthropic_compatible`.

---

## 核心概念

| 概念 | 说明 |
|------|------|
| **Vault** | 本地工作区，含 Source（原始资料）、Knowledge Cards（知识卡片）、Projects 等 |
| **Source** | 原始输入文件（Markdown、TXT），放在 `00-Inbox/` 下 |
| **AI Draft** | AI 从 source 自动生成的知识草稿，状态为 `ai_draft` |
| **Approved Card** | 你显式审批后的正式知识卡片，状态为 `human_approved` |
| **Library** | 所有 approved card 的可浏览知识库 |
| **Recall** | 本地 BM25 词法检索，查询 approved cards |
| **Trash** | 安全回收站——移入 Trash 只移除卡片，**不删除 source 文件**，支持 Restore |
| **Wiki** | 从所有 approved cards 自动生成的知识 wiki（deterministic 或 LLM synthesis） |
| **Processing Workflow** | 固定五段加工流程：初筛 → 提炼 → 关联建议 → 复习问题 → 行动项提取 |

**关键边界：AI 只生成草稿，审批永远是人的事。**

---

## Web 控制台

启动 `mindforge web` 后打开 `http://127.0.0.1:8765`：

| 页面 | 用途 |
|------|------|
| **Home** | 状态总览、安全摘要、下一步建议 |
| **Setup** | 配置模型、查看 Processing Workflow、添加 source |
| **Sources** | 管理 watched sources、Process now、Import |
| **Review** | 查看 AI 草稿、编辑 body、审批或移入 Trash |
| **Library** | 浏览已审批知识卡片、编辑 body、移入 Trash |
| **Trash** | 查看已移除卡片、预览、Restore |
| **Recall** | 本地 BM25 词法检索 |
| **Wiki** | 查看 Main Wiki、rebuild（deterministic / LLM synthesis） |

---

## 配置模型

### Web Setup（推荐主路径）

1. 打开 **Setup** 页面
2. 点击 **+ Add model**
3. 填写：
   - **Model id**: 别名，如 `main`、`claude`
   - **Type**: API 协议类型（见下表）
   - **Base URL**: 模型 endpoint
   - **Model**: 模型名，如 `claude-sonnet-4-6`
   - **API key**: 你的 API key
4. 保存

API key 存入本地 **secret store** (`.mindforge/secrets.json`)，Web/CLI 只显示脱敏值 (`sk-****abcd`)。

### 支持的模型类型

| Type | 适用场景 |
|------|---------|
| `anthropic` | 原生 Anthropic API |
| `anthropic_compatible` | 兼容 Anthropic 协议的 endpoint（DashScope、OpenRouter 等） |
| `openai` | OpenAI 官方 API（默认 base_url: `https://api.openai.com/v1`） |
| `openai_compatible` | 兼容 OpenAI 协议的 endpoint（Ollama、vLLM、DeepSeek、API 中转等） |

`type` 是 **API 协议类型**，不是模型品牌。本地模型（Ollama、LM Studio）通过 `openai_compatible` + local base URL 配置。

### Default Model 与 Routing

- **Default model**: 所有 workflow step 默认使用的模型（引用 `llm.models` 中的 model id）
- **Model routing**: 可选，每个 step（Triage / Distill / Link Suggestion / Review Questions / Action Extraction）可指定不同模型
- **Wiki model**: Wiki LLM synthesis 使用的模型，引用 `llm.models` 中的 model id

---

## 路径规则

### Workspace Root

工作区根自动发现，按优先级匹配：

1. `configs/mindforge.yaml` —— `mindforge init` 的产物
2. `.mindforge/` 目录（排除 vault 内部）
3. `vault/` 目录
4. `pyproject.toml` + `src/mindforge` —— 开发者 clone 的源码仓库

`mindforge web --workspace /path/to/workspace` 可显式指定工作区，自动推导 config 和 vault 路径。

### 路径语义

| 路径 | 说明 | Git |
|------|------|-----|
| `configs/mindforge.yaml` | 本地运行时配置，Web Setup 写入 | **不提交** |
| `configs/mindforge_example.yaml` | 新用户参考模板 | 提交 |
| `.mindforge/secrets.json` | API key 本地存储 | **不提交** |
| `.mindforge/` | 运行时状态（state、runs、telemetry） | **不提交** |
| `vault/` | 本地知识库（默认 vault root） | **不提交** |
| `vault_template/` | Vault 模板（README + .gitkeep） | 提交 |

### Web Add Source

**必须绝对路径。** 浏览器环境无法解析相对路径。

- `~/Documents/note.md` → 自动展开为 `/Users/<name>/Documents/note.md`
- `note.md` → 返回 400，请用绝对路径
- 路径不存在 → 返回 400

**macOS 提示：** Finder 中选中文件，按住 Option (⌥)，右键选择 "Copy ... as Pathname"（⌥⌘C），粘贴到 Web 输入框。

### CLI Source Path

- 支持相对路径，自动按 cwd → project-root → active-vault 解析为绝对路径
- 不存在时 exit_code=2 + 中文错误消息，不打印 traceback
- Registry 保存解析后的绝对路径

---

## 添加 Source 并生成 AI Draft

### Web 方式

1. 打开 **Setup** 页面
2. 在 "Add a file or folder" 区域粘贴绝对路径
3. 点击 **Add and process now** → 后台启动 processing run，不阻塞页面
4. 在 **Sources** 查看 run status：`running` / `succeeded` / `skipped` / `failed`
5. 如果生成 `ai_draft`，打开 **Review** 审批；如果被 triage skipped 或失败，Sources 会显示原因

### CLI 方式

```bash
mindforge watch add /path/to/folder --every manual   # CLI 注册 + 同步处理
mindforge import /path/to/file.md                    # 一次性导入，不注册
```

### Frequency

| Frequency | 行为 |
|-----------|------|
| `manual` | 不自动扫描，需手动 Process now |
| `hourly` / `daily` / `weekly` | 按周期自动扫描 |
| `every 1h` / `6h` / `12h` / `24h` | 精确间隔 |

---

## Review 与 Approve

**审批永远是显式确认。没有自动 approve。**

### Review

Web: **Review** 页面 → 左侧列表选 card → 右侧可阅读、编辑 body。

CLI:

```bash
mindforge approve list                 # 列出待审批草稿
mindforge approve show --card <path>   # 查看草稿内容
```

### Approve

Web: Review 页面 → 确认内容 → 点击 **Approve**。

CLI:

```bash
mindforge approve 1 --confirm          # 短编号审批
```

审批后：card 状态 → `human_approved`，进入 Library，可被 Recall 检索，并参与后续 Wiki rebuild。

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

安全移除：卡片文件移动到 `90-Archive/Trash/Knowledge-Cards/`，**source 文件不受影响**。

CLI:

```bash
mindforge trash move <card-path> --confirm     # 移入 Trash
mindforge trash list                           # 查看
mindforge trash show <trash-path>              # 详情
mindforge trash restore <trash-path> --confirm # 恢复
```

Restore 后状态恢复为移入前的 `ai_draft` 或 `human_approved`。

---

## Wiki

从所有 `human_approved` cards 重建生成 `30-Wiki/Main-Wiki.md`。

| Mode | 行为 |
|------|------|
| `deterministic` | 无需 LLM，按模板拼接所有 approved cards |
| `llm` | 调用 LLM 对 approved cards 做综合归纳和重写 |

**Wiki 只从 approved cards 生成，不绕过 approval 读取 raw source。Wiki 不是 source of truth——approved cards 才是。**

默认 `wiki.auto_rebuild_on_approve` 为 `false`。如果显式开启，approve 后也只会运行 deterministic rebuild；LLM synthesis 必须由用户在 Wiki 页面或 CLI 手动触发，不会在 approve 路径自动调用真实模型。

CLI:

```bash
mindforge wiki status             # 查看 Wiki 状态
mindforge wiki rebuild            # 按当前 mode 重建
mindforge wiki show               # 查看 Wiki 内容
```

Web: **Wiki** 页面查看、rebuild（deterministic 或 LLM synthesis 按钮）。

---

## Processing Workflow

固定五段 Knowledge Card Workflow，在 Web Setup 中可查看：

| Step | 做什么 |
|------|--------|
| Triage | 评估 source 价值，给出 track / value_score |
| Distill | 提取核心知识，生成卡片草稿主体 |
| Link Suggestion | 建议相关主题、项目或已有知识链接 |
| Review Questions | 生成复习和自测问题 |
| Action Extraction | 提取可跟进的行动项 |

每个 step 可指定不同模型（model routing）。点击 **View prompt** 查看 prompt 全文（当前只读）。

---

## CLI 常用命令

| 场景 | 命令 | 说明 |
|------|------|------|
| 启动 Web | `mindforge web` | 本地控制台 |
| 指定工作区 | `mindforge web --workspace <path>` | 推导 config/vault |
| 状态 | `mindforge status` | workspace / vault / draft / recall |
| 诊断 | `mindforge doctor` | 环境 + 配置 + 风险 |
| 添加 source | `mindforge watch add <path>` | 注册 + 处理 |
| 一次性导入 | `mindforge import <path>` | 不注册 |
| 查看 drafts | `mindforge approve list` | 待审批 ai_draft |
| 审批 | `mindforge approve 1 --confirm` | 显式审批 |
| 知识库 | `mindforge library list` | approved cards |
| 知识库详情 | `mindforge library show <ref>` | 单张卡片 |
| Trash 移入 | `mindforge trash move <path> --confirm` | 安全移除 |
| Trash 列表 | `mindforge trash list` | 查看 Trash |
| Trash 详情 | `mindforge trash show <path>` | 预览 Trash 卡片 |
| Trash 恢复 | `mindforge trash restore <path> --confirm` | 恢复 |
| Wiki 状态 | `mindforge wiki status` | 查看 Wiki |
| Wiki 重建 | `mindforge wiki rebuild` | 重建 Wiki |
| Wiki 查看 | `mindforge wiki show` | 只读查看 Wiki |
| Prompt 列表 | `mindforge prompts list` | 查看内置 prompt |
| 查看 prompt | `mindforge prompts show triage` | 只读查看 |
| 查看策略 | `mindforge strategies list` | 内置策略 |
| 检索 | `mindforge recall --query "关键词"` | BM25 |
| 版本 | `mindforge version` | 版本 + 配置摘要 |

---

## 安全原则

| 原则 | 实现 |
|------|------|
| API key 不进 Git | `.mindforge/`、`configs/mindforge.yaml` 已 gitignore；API key 不写 YAML |
| API key 不进 Web 前端 | Secret store 只在后端 runtime，API 只返回 masked 值 |
| 不自动审批 | 所有 approve 路径必须显式 `--confirm`（explicit approval required） |
| Source 删除不删知识 | Stop watching + Move to Trash 都不动 source |
| Trash 安全移除 | 不是永久删除，Restore 可用 |
| Wiki 不从 raw source 生成 | 只从 approved cards |
| 本地优先（local-first） | single-user，不联网、不上传 telemetry、纯本地 BM25 |
| 真实模型必须显式配置 | 配置真实模型 + API key + 显式触发处理或 Wiki LLM synthesis |

---

## 当前限制与不做的事

**当前限制：**

| 限制 | 说明 |
|------|------|
| 固定五段 workflow | 不支持自定义 step 数量/顺序 |
| Prompt 只读 | 可查看不可编辑 |
| 无 permanent delete | Trash 只做安全移除 |
| 无后台 daemon | Watch frequency 依赖手动触发或 cron |
| 无 Obsidian plugin | MindForge 是独立工具 |

**明确不做：**

- **not RAG / not embedding / no vector DB** —— 当前检索是 BM25 词法匹配。No RAG / embedding。
- **不做真实 Obsidian vault 写入** —— MindForge 独立管理 vault；no Obsidian plugin
- **不自动 approve** —— 自动化只生成 ai_draft；human_approved 必须显式确认
- **不把 raw source 绕过 approval 写入 Wiki** —— Wiki 只引用 approved cards
- **不做 SaaS / 不上传** —— local-first，single-user 本地工具；只有在你配置模型并显式处理 source / rebuild LLM wiki 时才调用 provider

**能力边界（what MindForge does not do）：**

- does not call a real LLM（无显式 opt-in 时）
- does not automatically modify a real private vault
- does not auto-approve
- no tag, no force push
- Real LLM enabled by default: No. Hidden automatic approval: No.
- 真实 LLM 只在你通过 Web Setup 配置模型和 API key 后，显式触发 source processing 或 Wiki LLM rebuild 时启用

**Future gates（后续版本规划，当前不做）：**

- G1 External account ingestion
- G2 Real Obsidian formal-note write
- G3 Approval UX
- G4 Custom executable strategy runtime
- G5 RAG / embedding / semantic merge
- G6 Public release / git tag

**v0.13 stage closure：** Web first slice, Real Data CLI Usability, Documentation cleanup。

---

## 试用建议

如果你准备在自己的真实数据上试用：

1. **先小规模**：选 1-2 个非敏感的 Markdown 文件开始
2. **确认模型配置**：Setup → Add model，确认 API key 生效
3. **验证全链路**：Source → Draft → Approve → Library → Wiki → Recall
4. **确认正常后再扩大**：不要一开始就扫大目录
5. **安全回退**：`git restore` 可回退本地实验文件

---

## 开发者

### 项目结构

```
mindforge/
├── src/mindforge/          # Python 核心（service、config、pipeline）
├── src/mindforge_web/      # FastAPI Web 后端（router、schema、facade）
├── web/                    # React/Vite 前端（TypeScript）
├── tests/                  # pytest 测试
├── prompts/                # Prompt 模板
├── configs/                # 用户配置模板（mindforge_example.yaml）
└── docs/                   # 开发者文档
```

CLI 和 Web Router 是薄适配器，业务逻辑在 service 层。

### 运行测试

Standard Quality Gate（提交前必过）：

```bash
ruff check .
python -m pytest
cd web && npm run build
```

First Status Commands（新用户首选检查命令）：`mindforge status`, `mindforge doctor`。

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
| Web Facade | `src/mindforge_web/services/web_facade.py` |
| Web Config Service | `src/mindforge_web/services/web_config_service.py` |

### Developer Testing

This section is for tests, CI fixtures, and compatibility evidence. It is not the recommended first-run path for normal users.

- Test doubles replace model responses only inside tests; they are not product providers or recommended extraction strategies.
- MindForge is local-first and single-user by default.
- Legacy routing fields may appear in low-level compatibility tests, not as the user setup path.
- A real provider is real provider opt-in, never implicit.
- Advanced / Troubleshooting may still mention scan/process for diagnostics; `watch/import/review/approve/library/trash/wiki` are the product surface.

### 安全契约（Custom Strategy / Preview）

Custom strategy 是 declarative 的 preview 定义，不是可执行代码：

- Custom strategy loading uses `explicit path` only: `--custom-path`. Loading is not execution, discovery is not execution, and preview is not implementation.
- Custom definitions are declarative: no arbitrary python, no shell, no implicit scanning of home folders or private vaults.
- Preview packet is review-only, not ai_draft, not human_approved (not `human_approved`), and any future implementation still requires explicit approval.
- Preview to future implementation requires a reviewed built-in implementation path.
- Validation error output is for reading a definition, not for executing it.
- Strategy lifecycle statuses: implemented, preview, planned. A planned strategy is visible for roadmap clarity but is not executable.

Card provenance and prompt visibility:

- Cards record source content hash and strategy/prompt/source/provider provenance.
- `strategy.active` chooses extraction strategy; `llm.default_model/routing` chooses model use.
- Use `mindforge strategies show knowledge_card` to inspect the default knowledge_card strategy.
- Prompt visibility: `mindforge prompts list`, `mindforge prompts show triage@v1`.

Local workflow safety notes:

- Use local source files or folders that you are comfortable processing; start with non-sensitive material.
- Keep API keys in the local secret store managed by Web Setup; do not put keys in YAML or docs.
- Real model calls require explicit model configuration and an explicit processing action.
- No automatic approve: automation can create AI Drafts, but only explicit human approval moves content into Library / Wiki.
- Obsidian-related commands remain staged/read-only unless a command explicitly says it writes a staged export for manual inspection.
- Future gates remain closed unless explicitly shipped: formal Obsidian note write; custom executable strategy runtime; RAG / embedding / semantic merge; public release / git tag.
- Human decision gate, local-first privacy contract, fixtures for CI, Real ≠ Approved, Human Decision Gate Map.
- Proposal artifacts are review-only: preview packets, readiness checks, real smoke.
- Deferred gates use sample folder, no-persist, dry-run, diff preview, backup.

Obsidian boundary notes:

- no Obsidian vault was written. No formal Obsidian notes are written. No formal Obsidian note writes. No Obsidian plugin.
- No secret file or real model call is used without explicit opt-in.
- No default real LLM path. No telemetry upload.
- Obsidian uses a staged workflow: staged export -> diff preview -> backup -> explicit confirmation. Supports include/exclude patterns.
- `mindforge obsidian next --vault /path/to/project-vault`, `mindforge obsidian doctor --vault /path/to/project-vault`, `mindforge obsidian scan --vault /path/to/project-vault --limit 20`, `mindforge obsidian links --vault /path/to/project-vault`, `mindforge obsidian stage --vault /path/to/project-vault --source <note.md> --dry-run`, `mindforge obsidian preflight --vault /path/to/project-vault --manifest`.
- `<export>.manifest.json` is the staged export manifest format.

Supported source format adapters: Markdown, TXT, CSV, Cubox Markdown, WebClip, ChatExport. The SourceAdapter layer normalizes diverse formats into a unified pipeline. BM25 is the current retrieval path (no embedding / no vector DB).

### 相关文档

- [DESIGN.md](DESIGN.md): Web 设计系统
- [docs/TESTING.md](docs/TESTING.md): 质量门和 smoke check
- [docs/LLM_PROVIDER_CONFIG.md](docs/LLM_PROVIDER_CONFIG.md): LLM provider 配置详情
- [docs/ROADMAP_COMPLETION_LEDGER.md](docs/ROADMAP_COMPLETION_LEDGER.md): 功能完成台账

---

## License

MIT
