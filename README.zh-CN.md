# MindForge

**本地优先、LLM 优先的个人 AI 知识加工工具。**

把本地文件变成可审批的知识卡片，通过 LLM-first synthesis 将已审批知识组织成结构化 Wiki。提供 Web 控制台 + CLI 双入口。

数据都在本地 vault，不做 RAG、不做 embedding、不连向量数据库。AI 只生成草稿，必须显式审批才能成为正式知识。

---

## 核心链路

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                        ├── Library
                                                        ├── Recall (BM25)
                                                        └── Wiki (LLM synthesis)
```

---

## 当前状态

- **v0.1** — 当前稳定 release，local-first / LLM-first 主链路已完成
- CLI + Web 均可使用
- 适合非敏感资料小规模使用
- 暂不建议直接处理私人/工作敏感资料、大规模 vault
- **v0.2** — 主要功能开发已完成，当前处于发布前验收阶段

---

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge

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

### 可选依赖

基础安装可支持 Markdown、TXT、本地 HTML。如果需要 PDF / DOCX 支持，请安装对应可选依赖：

```bash
pip install "mindforge[pdf,docx]"
```

PDF 仅支持文本型 PDF，不做 OCR、不支持扫描件文字识别。DOCX 支持现代 `.docx` 格式；legacy `.doc` 暂不支持。详见 [Source 管理](docs/zh-CN/sources.md)。

完整链路速览：`mindforge watch add` / `mindforge import` 添加 source → `mindforge runs list` / `mindforge runs show` 查看后台处理 → `mindforge approve list` / `mindforge approve 1 --confirm` 审阅审批 → `mindforge recall --query "MindForge"` 检索 → `mindforge wiki rebuild` 基于 approved cards 生成 Wiki → **Library** 和 **Wiki** 查阅已审批知识。

---

## 添加第一个 source

```bash
printf '# First note\n\nA short note for MindForge.\n' > vault/00-Inbox/first-note.md

mindforge watch add vault/00-Inbox/first-note.md
# 或一次性导入：
mindforge import vault/00-Inbox/first-note.md
```

source 放在 `vault/00-Inbox/` 下即可，无需预先创建 ManualNotes / WebClips / PDFs / Docs 等分类子目录。

### 支持的 Source 格式

| 格式 | 状态 | 说明 | 依赖 |
|------|------|------|------|
| Markdown | 已支持 | 完整支持 | 基础安装 |
| TXT | 已支持 | 纯文本 | 基础安装 |
| HTML | 已支持 | 仅本地文件，不做 URL 抓取 | 基础安装 |
| PDF（文本型） | 已支持 | 仅提取文本层文字，不做 OCR、不支持扫描件 | `pypdf`（可选） |
| DOCX | 已支持 | 现代 `.docx` 格式 | `python-docx`（可选） |
| DOC（旧版） | 不支持 | Research gate，当前版本不计划支持 | — |

可选依赖安装：`pip install "mindforge[pdf,docx]"`

### 路径规则

`vault/` 是本地知识库目录。本地 runtime config 已 gitignore，不提交。

**Web Add Source 必须绝对路径。** 浏览器环境无法解析相对路径：
- `~/Documents/note.md` → 自动展开为 `/Users/<name>/Documents/note.md`
- `note.md` → 返回 400，请用绝对路径
- 路径不存在 → 返回 400

**CLI Source Path 支持相对路径**，自动按 cwd → project-root → active-vault 解析为绝对路径，不存在时 exit_code=2 + 中文错误消息。

**明确不做：not RAG / not embedding / no vector DB。** 当前检索是 BM25 词法匹配。

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

**Wiki** 是已支持能力：从所有 `human_approved` cards 生成结构化 topic pages，帮助把 approved cards 组织成 Wiki。

Wiki 是 **LLM-first synthesis**——调用 LLM 对 approved cards 做综合归纳和重写。Web **Wiki** 页面点击 **Generate Wiki**，或 CLI：

```bash
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show
```

Wiki 只从 approved cards 生成，不绕过 approval 读取 raw source。Wiki 不是 source of truth——approved cards 才是。LLM synthesis 必须由用户在 Wiki 页面或 CLI 手动触发，不会在 approve 路径自动调用真实模型。

Web **Wiki** 页面 **Advanced** 折叠区提供 Safe fallback rebuild 作为 troubleshooting 回退。这不是推荐的 Wiki 生成路径，只在没有可用模型时应急使用。

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
| **Wiki** | LLM synthesis 生成 Wiki |

---

## 安全模型

| 原则 | 实现 |
|------|------|
| local-first | single-user，不联网、不上传 telemetry、纯本地 BM25 |
| API key 不进 Git | `.mindforge/`、`configs/mindforge.yaml` 已 gitignore；API key 只存 local secret store |
| API key 不进 Web 前端 | Secret store 只在后端 runtime，API 只返回 masked 值 |
| 不自动审批 | 所有 approve 路径必须显式确认 |
| Source 文件保护 | Stop watching + Move to Trash 都不动 source 文件 |
| Wiki 不从 raw source 生成 | 不从未审批内容生成 Wiki；未审核 `ai_draft` 不进入 Wiki；内容必须先显式 approve 成 `human_approved` |
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
| `mindforge doctor` | 环境 + 配置 + 风险诊断（troubleshooting 入口） |

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
- Custom strategy 当前是 declarative preview / review-only：preview packet is review-only, not ai_draft, not human_approved；no arbitrary python，no shell；preview to future implementation 需要 reviewed built-in implementation path，并仍然要求 explicit approval 和 explicit opt-in。
- 暂不支持：RAG、embedding、向量数据库、semantic merge、Obsidian plugin、自动审批、自动修改真实私人 vault。
- 长文档或大目录建议先用非敏感资料小批量验证；如果 provider timed out，可拆分 source 或调高 `timeout_seconds` 后重新 import。
- deterministic / template rebuild 只属于 Advanced / Troubleshooting 回退，不是普通用户主路径。

---

## 安全契约

核心安全边界的完整声明见 [Product Contracts](docs/internal/product-contracts.md)。摘要：

- AI 草稿绝不自动提升为正式知识。每条审批都要求显式确认。
- 真实模型调用必须 opt-in：配置模型 + API key + 显式触发处理。
- API key 只存 local secret store，不进 Git、不进 YAML、不进前端。
- 不做 Obsidian plugin，不写正式 Obsidian note。
- 不做 RAG / embedding / 向量数据库，当前检索是 BM25 词法匹配。
- Custom strategy 当前是 declarative preview only，不可执行。
- 提案产物（preview packet 等）仅供审阅，不产生 ai_draft 或 human_approved。
- 测试替身只在 CI fixtures 中使用，不是产品 provider。

---

## 文档导航

| 文档 | 说明 |
|------|------|
| [快速入门](docs/zh-CN/getting-started.md) | 详细安装与初始化指南 |
| [用户指南](docs/zh-CN/user-guide.md) | 完整功能说明 |
| [模型配置](docs/zh-CN/model-setup.md) | LLM provider 配置详解 |
| [Source 管理](docs/zh-CN/sources.md) | 添加和管理知识来源 |
| [审阅与审批](docs/zh-CN/review-and-approval.md) | AI 草稿审阅与审批流程 |
| [Library / Recall / Wiki](docs/zh-CN/library-recall-wiki.md) | 知识浏览、检索与综合 |
| [Web Wiki](docs/zh-CN/web-wiki.md) | Web Wiki 页面使用指南 |
| [配置参考](docs/zh-CN/configuration.md) | 完整配置参考 |
| [Troubleshooting](docs/zh-CN/troubleshooting.md) | 常见问题诊断 |
| [FAQ](docs/zh-CN/faq.md) | 常见问题解答 |
| [发布说明](docs/RELEASE_NOTES.md) | 第一版发布记录 |
| [English Docs](docs/en/) | English documentation |
| [开发者文档](docs/dev/) | 架构、测试、贡献指南 |
| [设计文档](docs/design/) | RFC、SDD、路线图 |

---

## License

MIT
