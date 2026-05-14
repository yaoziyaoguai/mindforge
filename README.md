# MindForge

**本地优先、LLM 优先的个人 AI 知识加工工具。** 把本地文件变成可审批的知识卡片，提供 Web 控制台 + CLI 双入口。

核心链路：

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                        ├── Library
                                                        ├── Recall (BM25)
                                                        └── Wiki (LLM synthesis)
```

- 数据都在本地 vault，不做 RAG、不做 embedding、不连向量数据库
- AI 只生成草稿 (`ai_draft`)，必须显式审批才能成为正式知识 (`human_approved`)
- API key 存本地 secret store (`.mindforge/secrets.json`)，不进 Git、不进 YAML、不进 Web 前端
- Web 控制台 (React) + CLI (Typer) 同一套 Python service 层

---

## 当前状态

- **Local MVP** — 接近首次 release
- CLI + Web 均可使用
- 适合非敏感资料小规模使用
- 暂不建议直接处理私人/工作敏感资料、大规模 vault

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge
git checkout feat-wiki-llm-synthesis

# 2. 安装
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .

# 3. 初始化本地 workspace
mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init

# 4. 查看 first-run checklist
mindforge start
mindforge status

# 5. 启动 Web 配置模型
mindforge web --open
```

`mindforge init` 创建 MindForge **workspace**：包含 vault 骨架和本地 runtime config。init 完成后会自动记住 workspace 路径（`~/.mindforge/current_workspace.json`），之后在任意目录运行 `mindforge status` / `mindforge start` 等命令都会自动找到它。用户只需理解 workspace 这一个概念，无需关心内部 config 文件路径。

首次运行后 `mindforge status` 查看 workspace / vault / draft 状态。

**必须：配置模型**

```bash
mindforge web --open
```

浏览器打开 `http://127.0.0.1:8765`。

1. 打开 **Setup** 页面 → **Add model**
2. 填写 model id（如 `main`）、type（`anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`）、base URL、模型名、API key
3. 保存

API key 由你在本地 Web 页面手动输入，存入 local secret store (`.mindforge/secrets.json`)。API key 不写 YAML。**不要把 key 写进 issue、prompt、README、logs 或 YAML。**

完整链路速览：`mindforge watch add` / `mindforge import` 添加 source → `mindforge runs list` / `mindforge runs show` 查看后台处理 → `mindforge approve list` / `mindforge approve 1 --confirm` 审阅审批 → `mindforge recall --query "MindForge"` 检索 → **Library** 和 **Wiki** 查阅已审批知识。

---

## 添加第一个 source

```bash
printf '# First note\n\nA short note for MindForge.\n' > vault/00-Inbox/first-note.md

mindforge watch add vault/00-Inbox/first-note.md
# 或一次性导入：
mindforge import vault/00-Inbox/first-note.md
```

source 放在 `vault/00-Inbox/` 下即可，无需预先创建 ManualNotes / WebClips / PDFs / Docs 等分类子目录。

### 路径规则

`vault/` 是本地知识库目录。本地 runtime config 已 gitignore，不提交。

**Web Add Source 必须绝对路径。** 浏览器环境无法解析相对路径：
- `~/Documents/note.md` → 自动展开为 `/Users/<name>/Documents/note.md`
- `note.md` → 返回 400，请用绝对路径
- 路径不存在 → 返回 400

**CLI Source Path 支持相对路径**，自动按 cwd → project-root → active-vault 解析为绝对路径，不存在时 exit_code=2 + 中文错误消息。

**明确不做：No RAG / embedding / no vector DB。** 当前检索是 BM25 词法匹配。

---

## 后台处理

`watch add` / `import` 注册 source、创建 durable run、启动后台处理，并立即返回 `run_id`：

```bash
mindforge runs list
mindforge runs show <run_id>
```

如果模型还没配好，run 会失败并提示去 Web Setup 添加 API key；补齐后在 Web Sources 中 Process now 或重新 `import`。

真实模型处理源文件可能需要几分钟，`running` 不一定是卡死。

---

## Review 与 Approve

**审批永远是显式确认。没有自动 approve。**

```bash
mindforge approve list                  # 列出待审批 ai_draft
mindforge approve show --card 1 --show-content  # 查看草稿内容（预览，不会自动审批）
mindforge approve 1 --confirm           # 显式审批，进入 human_approved
```

也可以在 Web **Review** 页面查看 AI 生成的草稿，确认后点击 **Approve**（需二次确认）。

`ai_draft` = AI 生成的草稿，仅供预览。
`human_approved` = 你显式审批后的正式知识，进入 Library，可被 Recall 检索，参与 Wiki 生成。

---

## Library / Recall / Wiki

```bash
mindforge library list         # 浏览已审批知识库
mindforge library show <ref>   # 查看单张卡片详情
mindforge recall --query "关键词"  # 本地 BM25 词法检索
```

**Wiki** 从所有 approved cards 生成 `30-Wiki/Main-Wiki.md`。

Wiki 是 **LLM-first synthesis**——调用 LLM 对 approved cards 做综合归纳和重写。Web **Wiki** 页面点击 **Rebuild Wiki**，或 CLI：

```bash
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show
```

Wiki 只从 approved cards 生成，不绕过 approval 读取 raw source。Wiki 不是 source of truth——approved cards 才是。LLM synthesis 必须由用户在 Wiki 页面或 CLI 手动触发，不会在 approve 路径自动调用真实模型。

Web **Wiki** 页面 **Advanced** 折叠区提供 deterministic template rebuild 作为 troubleshooting 回退。这不是推荐的 Wiki 生成路径，只在没有可用模型时应急使用。

---

## Web UI 概览

启动 `mindforge web --open` 后：

| 页面 | 用途 |
|------|------|
| **Home** | 状态总览、安全摘要、下一步建议 |
| **Setup** | 配置模型、查看 Processing Workflow、添加 source |
| **Sources** | 管理 watched sources、Process now、Import |
| **Review** | 查看 AI 草稿、审批或移入 Trash |
| **Library** | 浏览已审批知识卡片 |
| **Trash** | 安全回收站，支持 Restore |
| **Recall** | 本地 BM25 词法检索 |
| **Wiki** | LLM synthesis 生成 Wiki；Advanced → deterministic 回退 |

---

## Processing Workflow

固定五段 Knowledge Card Workflow，在 Web Setup 中可查看每个 step 的 prompt 和模型配置：

| Step | 做什么 |
|------|--------|
| Triage | 评估 source 价值，给出 track / value_score |
| Distill | 提取核心知识，生成卡片草稿主体 |
| Link Suggestion | 建议相关主题、项目或已有知识链接 |
| Review Questions | 生成复习和自测问题 |
| Action Extraction | 提取可跟进的行动项 |

每个 step 可指定不同模型（model routing）。

---

## 安全模型

| 原则 | 实现 |
|------|------|
| local-first | single-user，不联网、不上传 telemetry、纯本地 BM25 |
| API key 不进 Git | `.mindforge/`、`configs/mindforge.yaml` 已 gitignore；API key 只存 local secret store |
| API key 不进 Web 前端 | Secret store 只在后端 runtime，API 只返回 masked 值 |
| 不自动审批 | 所有 approve 路径必须显式确认 |
| Source 文件保护 | Stop watching + Move to Trash 都不动 source 文件 |
| Wiki 不从 raw source 生成 | 只从 approved cards |
| 真实模型必须显式配置 | 配置模型 + API key + 显式触发处理或 Wiki rebuild |

---

## CLI 参考

### 主路径命令

| 命令 | 说明 |
|------|------|
| `mindforge init` | 初始化本地 workspace |
| `mindforge start` | 查看 first-run checklist |
| `mindforge status` | workspace / vault / draft 状态 |
| `mindforge web` | 启动 Web 控制台 |
| `mindforge import <path>` | 一次性导入 source 并处理 |
| `mindforge watch add <path>` | 注册 source 并处理 |
| `mindforge runs list` | 查看 processing run 列表 |
| `mindforge runs show <run_id>` | 查看 run 详情 |
| `mindforge approve list` | 列出待审批 ai_draft |
| `mindforge approve show <ref>` | 查看草稿内容 |
| `mindforge approve <ref> --confirm` | 显式审批 |
| `mindforge library list` | 浏览知识库 |
| `mindforge recall --query "关键词"` | BM25 检索 |
| `mindforge wiki status` | 查看 Wiki 状态 |
| `mindforge wiki rebuild` | 重建 Wiki |
| `mindforge version` | 版本 + 配置摘要 |

### Troubleshooting

| 命令 | 说明 |
|------|------|
| `mindforge doctor` | 环境 + 配置 + 风险诊断（troubleshooting 入口，不是 first-run 主路径） |

---

## Troubleshooting

| 现象 | 检查 |
|------|------|
| 模型无法生成 draft | Web Setup 中为该 model 添加 API key |
| run skipped by triage | source 内容被 triage 判定为低价值，检查 `runs show` |
| running 持续几分钟 | 真实模型处理需要时间；检查 `runs show` 看当前 step |
| provider timed out | 检查 endpoint / network / proxy；长文档可先拆分 source，或在配置中调高 `timeout_seconds` 后重新 import |
| already processed / already approved | source 已处理过，不会重复生成 draft |
| approve number ref expired | 审批后编号失效，重新 `approve list` |
| Web port already in use | 检查是否已有 `mindforge web` 进程运行，或使用 `mindforge web --port 8766 --open` |
| stale web process / wrong venv | 确认 venv 已激活且 `pip install -e .` 成功 |
| `mindforge: command not found` | `source .venv/bin/activate && pip install -e .` |

**不要将 API key 粘贴到聊天、issue、logs 或 README 中。**

## 当前范围与已知限制

第一版聚焦本地、单用户、显式审批的知识加工闭环：

- 已支持：Web Setup 配置真实模型、`import` / `watch add` 处理本地 source、生成 `ai_draft`、显式 approve、Library / BM25 Recall / LLM-first Wiki。
- 暂不支持：RAG、embedding、向量数据库、semantic merge、Obsidian plugin、自动审批、自动修改真实私人 vault。
- 长文档或大目录建议先用非敏感资料小批量验证；如果 provider timed out，可拆分 source 或调高 `timeout_seconds` 后重新 import。
- deterministic / template rebuild 只属于 Advanced / Troubleshooting 回退，不是普通用户主路径。
- Custom strategy 当前是 declarative preview / review-only：preview packet 不是 ai_draft，不是 `human_approved`；preview to future implementation 需要 reviewed built-in implementation path、no arbitrary python、no shell，并仍然要求 explicit approval。

未来工作会按单项设计和测试推进，不在第一版文档中展开 RFC/SDD。

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
├── configs/                # 用户配置模板
└── docs/                   # 开发者文档
```

CLI 和 Web Router 是薄适配器，业务逻辑在 service 层。

### Developer Testing

This section is for tests, CI fixtures, and compatibility evidence. It is not the recommended first-run path for normal users. Advanced / Troubleshooting may still mention scan/process for diagnostics.

- Test doubles replace model responses only inside tests; they are not product providers or recommended extraction strategies.
- SourceAdapter layer normalizes diverse formats into a unified pipeline.
- BM25 is the current retrieval path (no embedding / no vector DB).
- Custom strategy loading uses `explicit path` only: `--custom-path`. Loading is not execution, discovery is not execution, preview is not implementation. Preview packet is review-only, not human_approved. Preview to future implementation requires a reviewed built-in implementation path. Validation error output is for reading a definition, not for executing it. No implicit scanning of home folders or private vaults, no arbitrary python, no shell. Use `mindforge strategies list` to discover strategies; `knowledge_card` is the default strategy. `strategy.active` chooses extraction strategy. Strategy lifecycle statuses: implemented, preview, planned. The default strategy is status='implemented'. Use `mindforge strategies show knowledge_card` to inspect it. Use `mindforge prompts list` to browse prompts, `mindforge prompts show triage@v1` to read one.

### 质量门

```bash
git diff --check
python -m ruff check .
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
| Web Facade | `src/mindforge_web/services/web_facade.py` |

### 安全契约

- Programming model: single-user, local-first.
- Custom strategy 是 declarative preview 定义，不是可执行代码。
- Cards record strategy/prompt/source/provider provenance, including source content hash.
- 真实 LLM 只在你配置模型和 API key 后，显式触发 source processing 或 Wiki LLM rebuild 时启用。
- 没有自动 approve：自动化只生成 ai_draft，human_approved 必须显式确认。
- 不支持 not RAG / not embedding / no vector DB / semantic merge。
- 不做 SaaS / 不上传。

### Obsidian 边界声明（future-gated）

- No formal Obsidian notes are written. No Obsidian plugin.
- Obsidian staged workflow 是开发/维护边界，不是第一版普通用户主路径：staged export → diff preview → backup → explicit confirmation.
- Supports include/exclude patterns for staged exports.
- 只读/预检命令示例：`mindforge obsidian next --vault /path/to/project-vault`, `mindforge obsidian doctor --vault /path/to/project-vault`, `mindforge obsidian scan --vault /path/to/project-vault --limit 20`, `mindforge obsidian links --vault /path/to/project-vault`, `mindforge obsidian stage --vault /path/to/project-vault --source <note.md> --dry-run`, `mindforge obsidian preflight --vault /path/to/project-vault --manifest`.
- `<export>.manifest.json` is the staged export manifest format.
- No formal Obsidian note writes.
- No secret file or real model call is used without explicit opt-in.
- Use local source files or folders that you are comfortable processing; start with non-sensitive material.
- Keep API keys in the local secret store managed by Web Setup; do not put keys in YAML or docs.
- No default real LLM path. No telemetry upload.
- Human decision gate, local-first privacy contract, fixtures for CI, Real ≠ Approved, Human Decision Gate Map.
- Preview packet is review-only, not ai_draft, not `human_approved`, and any future implementation still requires explicit approval.
- Proposal artifacts are review-only: preview packets, readiness checks, real smoke.
- Deferred gates use sample folder, no-persist, dry-run, diff preview, backup.
- A real provider is real provider opt-in, never implicit.

### 相关文档

- [docs/RELEASE_NOTES.md](docs/RELEASE_NOTES.md): 第一版发布说明
- [DESIGN.md](DESIGN.md): Web 设计系统
- [docs/LLM_PROVIDER_CONFIG.md](docs/LLM_PROVIDER_CONFIG.md): LLM provider 配置详情
- [docs/TESTING.md](docs/TESTING.md): 测试指南
- [docs/ROADMAP_COMPLETION_LEDGER.md](docs/ROADMAP_COMPLETION_LEDGER.md): 维护者功能完成台账（不是 first-run 文档）

---

## Future Work

当前阶段：**first local MVP 接近首次 release**。第一版只承诺上面已列出的本地 LLM-first 知识闭环。

Future gates（当前不做，打开前需要单独设计、测试和人工授权）：
- G1 External account ingestion
- G2 Real Obsidian formal-note write
- G3 Approval UX
- G4 Custom executable strategy runtime
- G5 RAG / embedding / semantic merge
- G6 Public release / git tag

能力边界：MindForge does not call a real LLM without explicit opt-in, does not automatically modify a real private vault, and does not auto-approve. No tag, no force push, and public release / git tag requires a separate named release authorization. Real model calls require explicit model configuration and an explicit processing action.

不承诺未实现能力。

---

## License

MIT
