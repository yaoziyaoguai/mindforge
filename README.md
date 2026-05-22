# MindForge

[中文] | [English](README.en.md)

MindForge 是一个本地优先的个人 AI 知识库工具，帮助你把 Markdown、TXT、HTML、PDF、DOCX 等本地资料转成待审核知识卡片，经人工确认后进入知识库，并生成个人 Wiki。

它适合想把零散资料沉淀成可回顾、可检索、可追溯知识库的个人用户。MindForge 提供 Web 控制台和 CLI 双入口；AI 只生成 `ai_draft` 草稿，正式知识必须由你显式 approve 成 `human_approved`。

```
Source → AI Draft → Human Review → Explicit Approve → Approved Card
                                                        ├── Library
                                                        ├── Recall (BM25)
                                                        └── Wiki (LLM synthesis)
```

## 这是什么

MindForge 的核心链路是 **Knowledge Card Workflow**：

1. 导入或监听本地 source 文件。
2. 使用你在 Web Setup 中配置的模型生成 `ai_draft` 知识卡片草稿。
3. 在 Review 中人工审阅并显式确认。
4. 审批后的 `human_approved` 卡片进入 Library，可被 Recall 检索，并参与 Wiki rebuild。

MindForge 不是 RAG 平台，不做 embedding，不连接向量数据库，也不会把未审批内容自动写入知识库。

## 适合什么场景

- 把阅读笔记、研究材料、项目记录、课程资料整理成可审批的知识卡片。
- 用本地 BM25 检索已审批知识，而不是把原始资料直接交给黑盒检索。
- 从已审批卡片生成个人 Wiki，帮助自己回顾主题、脉络和引用来源。
- 小规模、非敏感资料的个人知识加工闭环。

暂不建议直接处理私人敏感资料、公司机密资料或大规模 vault。

## 当前能力

- **Source import/watch**：通过 `mindforge import <path>` 一次性导入，或 `mindforge watch add <path>` 注册本地 source。
- **AI draft card**：五段流程 Triage → Distill → Link Suggestion → Review Questions → Action Extraction 生成 `ai_draft`。
- **Human review/approval**：所有草稿都必须在 CLI 或 Web Review 中显式 approve。
- **Knowledge Library**：浏览和管理 `human_approved` 卡片。
- **Wiki rebuild**：基于已审批卡片手动重建 LLM-first Wiki。
- **Source provenance**：保留 source、hash、页码/段落/行号等可用来源信息，方便回查。
- **Related cards**：基于 same source、same tag、same wiki section、same review batch 等确定性关系提示相关卡片。
- **Knowledge Health**：检查 review backlog、低质量卡片、缺少 provenance、重复候选、孤立卡片、stale wiki 等，只给维护建议，不自动修改内容。
- **Local Graph Preview**：基于 source、tag、wiki section、review batch 等确定性关系展示局部关系图；不使用向量数据库，不是 GraphRAG。

## 安全边界

| 边界 | 说明 |
|------|------|
| 默认不联网 | fresh workspace 默认不调用真实 LLM/API，也不上传 telemetry；外部模型调用必须由用户显式配置 provider/API key 并主动触发 import/watch processing 或 Wiki rebuild |
| local-first | 单用户本地 workspace；默认只读写本机文件 |
| API key 本地配置 | 通过 Web Setup 手动输入，存入 local secret store（`.mindforge/secrets.json`） |
| 不自动泄露 secret | MindForge 不会为了处理 source 自动读取 environment files 或 secret store 并输出 API key、token 或 secret |
| 不把本地资料自动外流 | 原始 source、API key、token、secret 默认不进 Git、不进 Web 前端、不上传 telemetry |
| 不要粘贴 key | 不要把 API key 粘贴到聊天、issue、终端日志、README 或 YAML |
| 不自动审批 | `ai_draft` 不会自动进入 Library；`human_approved` 必须显式 approve |
| Wiki 只用已审批卡片 | Wiki rebuild 不绕过 approval，不从未审批内容构建，也不读取 raw source |
| 真实模型必须显式触发 | 配置模型 + API key + 用户触发 import/watch processing 或 wiki rebuild |
| Legacy `.doc` 不支持 | 旧版 Word `.doc` 会友好提示转换为 DOCX/TXT/PDF |
| 不做 OCR | PDF 仅支持文本层；扫描件不会被识别 |
| Graph 不是 GraphRAG | Local Graph Preview 是基于 same_source / same_tag / same_wiki_section / same_review_batch / source_location_neighbor 等 deterministic relations 的局部预览；当前没有独立全局 Graph 页面，不是 Vector DB、Graph DB、Embedding 或 GraphRAG |

Custom strategy 当前是 declarative preview only：preview packet is review-only, not ai_draft, not human_approved；no arbitrary python，no shell；preview to future implementation 需要 reviewed built-in implementation path，并仍然要求 explicit approval 和 explicit opt-in。

明确不做：not RAG / not embedding / no vector DB / no GraphRAG。当前 Recall 是 BM25 词法检索，Local Graph Preview 是确定性局部导航。首次试用建议使用 synthetic source 或临时资料夹验证流程，再接入真实资料。

## 安装要求

- Python >=3.11
- pip
- 一个可用的 LLM API key（Anthropic、OpenAI 或兼容协议）
- Node/npm 用于构建 Web 前端（Web UI 和 Setup 页面需要已构建的前端 assets）

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/yaoziyaoguai/mindforge.git
cd mindforge

# 2. 安装 Python 依赖
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .

# 3. 构建 Web 前端（Web UI / Setup 页面需要）
cd web
npm install
npm run build
cd ..

# 4. 初始化本地 workspace
mkdir -p /tmp/mindforge-first-run
cd /tmp/mindforge-first-run
mindforge init

# 5. 查看 first-run checklist
mindforge start
mindforge status

# 6. 启动 Web 配置模型
mindforge web --open
```

`mindforge init` 创建 MindForge **workspace**：包含 vault 骨架和本地 runtime config。init 完成后会自动记住 workspace 路径（`~/.mindforge/current_workspace.json`），之后在任意目录运行 `mindforge status` / `mindforge start` 等命令都会自动找到它。用户只需理解 workspace 这一个概念，无需关心内部 config 文件路径。

本地 runtime config 对应 `configs/mindforge.yaml` 的运行时配置结构，但普通用户优先通过 Web Setup 配置。

### Web 使用流程

首次使用需要先构建 Web 前端（如果已按快速开始执行过可跳过）：

```bash
cd web
npm install
npm run build
cd ..
```

启动 Web：

```bash
mindforge web --open
```

浏览器打开 `http://127.0.0.1:8765`。

1. 打开 **Setup** 页面 → **Add model**
2. 填写 model id（如 `main`）、type（`anthropic` / `anthropic_compatible` / `openai` / `openai_compatible`）、base URL、模型名、API key
3. 保存；API key 存入 local secret store，**API key 不写 YAML**
4. 在 Setup 或 Sources 中添加 source，或用 CLI：

```bash
printf '# First note\n\nA short note for MindForge.\n' > vault/00-Inbox/first-note.md

mindforge watch add vault/00-Inbox/first-note.md
# 或一次性导入：
mindforge import vault/00-Inbox/first-note.md
```

5. 查看处理进度：

```bash
mindforge runs list
mindforge runs show <run_id>
```

6. 审阅并显式审批：

```bash
mindforge approve list
mindforge approve show --card 1 --show-content
mindforge approve 1 --confirm
```

7. 浏览、检索、重建 Wiki：

```bash
mindforge library list
mindforge recall --query "MindForge"
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show
```

也可以在 Web **Library** 查阅已审批知识卡片，在 Web **Wiki** 查看重建后的个人 Wiki。

## Watch 频率

`watch add` 默认注册为 **manual** 频率，不会自动扫描。需要定期扫描时，通过 `--every` / `--frequency` 指定频率：

```bash
mindforge watch add <path> --every daily
mindforge watch add <path> --frequency "every 6h"
```

可选频率：

| 频率 | 说明 |
|------|------|
| `manual` | 默认值，不自动扫描；手动 `mindforge watch scan` |
| `hourly` | 每 1 小时扫描 |
| `daily` | 每 24 小时扫描 |
| `weekly` | 每 7 天扫描 |
| `every 1h` | 每 1 小时扫描 |
| `every 6h` | 每 6 小时扫描 |
| `every 12h` | 每 12 小时扫描 |
| `every 24h` | 每 24 小时扫描 |

查看当前 watched source 的频率和下次扫描时间：

```bash
mindforge watch status
```

频率可通过 CLI（`--every` / `--frequency`）或 Web UI（Setup → Add Source 的 Frequency 下拉，或 Sources → Edit frequency）设置。

## 支持的资料类型

基础安装支持 Markdown、TXT、本地 HTML。如果需要 PDF / DOCX 支持，请安装可选依赖：

```bash
pip install "mindforge[pdf,docx]"
```

| 格式 | 状态 | 说明 | 依赖 |
|------|------|------|------|
| Markdown | 已支持 | `.md` 文件 | 基础安装 |
| TXT | 已支持 | 纯文本 | 基础安装 |
| HTML | 已支持 | 仅本地 HTML 文件，不抓取 URL | 基础安装 |
| PDF（文本型） | 已支持 | 仅提取文本层文字，不做 OCR、不支持扫描件 | `pypdf`（可选） |
| DOCX | 已支持 | 现代 `.docx` 格式 | `python-docx`（可选） |
| DOC（旧版） | 不支持 | 会友好提示转换为 DOCX/TXT/PDF | — |

支持表示 MindForge 会尝试导入、提取、triage，并在模型配置完整时尝试生成 `ai_draft`；不承诺每个文件都一定生成卡片。低价值内容、空文件、无文本 PDF、超大文件、模型错误等都可能导致 run 被 skipped 或 failed。

## 路径规则

`vault/` 是本地知识库目录。本地 runtime config 已 gitignore，不提交。

**Web Add Source 必须绝对路径。** 浏览器环境无法解析相对路径：

- `~/Documents/note.md` → 自动展开为 `/Users/<name>/Documents/note.md`
- `note.md` → 返回 400，请用绝对路径
- 路径不存在 → 返回 400

**CLI Source Path 支持相对路径**，自动按 cwd → project-root → active-vault 解析为绝对路径，不存在时 exit_code=2 + 中文错误消息。

## Library / Recall / Wiki

```bash
mindforge library list           # 浏览已审批知识库
mindforge library show <ref>     # 查看单张卡片详情
mindforge recall --query "关键词"  # BM25 词法检索
```

Wiki 是 **LLM-first synthesis**：从所有 `human_approved` cards 生成结构化 topic pages。Web **Wiki** 页面点击 **Generate Wiki**，或 CLI：

```bash
mindforge wiki status
mindforge wiki rebuild
mindforge wiki show
```

Wiki 只从 approved cards 生成，不绕过 approval 读取 raw source。Wiki 不是 source of truth，approved cards 才是。LLM synthesis 必须由用户在 Wiki 页面或 CLI 手动触发，不会在 approve 路径自动调用真实模型。

Web **Wiki** 页面 **Advanced** 折叠区提供 Safe fallback rebuild 作为 troubleshooting 回退。这不是推荐的 Wiki 生成路径，只在没有可用模型时应急使用。

## Web UI 概览

启动 `mindforge web --open` 后：

| 页面 | 用途 |
|------|------|
| **Home** | 状态总览、安全摘要、下一步建议 |
| **Setup** | 配置模型、查看 Processing Workflow、添加 source |
| **Sources** | 管理 watched sources、Process now、Import |
| **Review** | 查看 AI 草稿、审批或移入 Trash |
| **Library** | 浏览已审批知识卡片、查看 Related cards 和 Local Graph Preview |
| **Trash** | 安全回收站，支持 Restore |
| **Recall** | 本地 BM25 词法检索 |
| **Wiki** | LLM synthesis 生成 Wiki，查看 Wiki quality / references |

## CLI 参考

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
| `mindforge health` | 只读生成 Knowledge Health 报告 |
| `mindforge doctor` | 环境 + 配置 + 风险诊断 |
| `mindforge version` | 版本 + 配置摘要 |

## 当前状态 / 版本说明

- Package version: `0.7.22`
- Product milestone: `v0.3 Local AI Knowledge Loop / Knowledge Quality & Navigation`

说明：package version 用于 Python 包迭代和安装分发；product milestone 用于说明功能路线和发布阶段。两者不是同一套编号，因此 `0.7.22` 与 `v0.3` 可以同时出现。

当前功能阶段聚焦本地、单用户、显式审批的知识加工闭环，以及质量、追溯、关系和维护诊断能力。适合非敏感资料小规模使用；release 前仍建议做 final release-readiness audit。

## 当前范围与已知限制

- 已支持：Web Setup 配置真实模型、`import` / `watch add` 处理本地 source、生成 `ai_draft`、显式 approve、Library / BM25 Recall / LLM-first Wiki、Knowledge Health、Local Graph Preview。
- 暂不支持：RAG、embedding、向量数据库、GraphRAG、semantic merge、Obsidian plugin、自动审批、自动修改真实私人 vault。
- 长文档或大目录建议先用非敏感资料小批量验证；如果 provider timed out，可拆分 source 或调高 `timeout_seconds` 后重新 import。
- deterministic / template rebuild 只属于 Advanced / Troubleshooting 回退，不是普通用户主路径。

## 安全契约

核心安全边界的完整声明见 [Product Contracts](docs/internal/product-contracts.md)。摘要：

- AI 草稿绝不自动提升为正式知识。每条审批都要求显式确认。
- 真实模型调用必须 opt-in：配置模型 + API key + 显式触发处理。
- API key 只存 local secret store，不进 Git、不进 YAML、不进前端。
- 不做 Obsidian plugin，不写正式 Obsidian note。
- 不做 RAG / embedding / 向量数据库 / GraphRAG，当前检索是 BM25 词法匹配。
- Custom strategy 当前是 declarative preview only，不可执行。
- 提案产物（preview packet 等）仅供审阅，不产生 ai_draft 或 human_approved。
- 测试替身只在 CI fixtures 中使用，不是产品 provider。

## 文档导航

| 文档 | 说明 |
|------|------|
| [快速入门](docs/zh-CN/getting-started.md) | 详细安装与初始化指南 |
| [用户指南](docs/zh-CN/user-guide.md) | 完整功能说明 |
| [模型配置](docs/zh-CN/model-setup.md) | LLM provider 配置详解 |
| [Source 管理](docs/zh-CN/sources.md) | 添加和管理知识来源 |
| [审阅与审批](docs/zh-CN/review-and-approval.md) | AI 草稿审阅与审批流程 |
| [Library / Recall / Wiki](docs/zh-CN/library-recall-wiki.md) | 知识浏览、检索、Wiki、Health 与 Graph |
| [Web Wiki](docs/zh-CN/web-wiki.md) | Web Wiki 页面使用指南 |
| [配置参考](docs/zh-CN/configuration.md) | 完整配置参考 |
| [Troubleshooting](docs/zh-CN/troubleshooting.md) | 常见问题诊断 |
| [FAQ](docs/zh-CN/faq.md) | 常见问题解答 |
| [English README](README.en.md) | English GitHub entry |
| [English Docs](docs/en/) | English documentation |
| [发布说明](docs/RELEASE_NOTES.md) | 发布记录 |
| [真实 LLM Dogfood](docs/real-llm-dogfood.md) | 真实 LLM opt-in 验证指南（Web-first） |
| [开发者文档](docs/dev/) | 架构、测试、贡献指南 |
| [设计文档](docs/design/) | RFC、SDD、路线图 |

## License

MIT
