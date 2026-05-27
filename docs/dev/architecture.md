# Architecture

MindForge 系统架构概览。

---

## 项目结构

```
mindforge/
├── src/
│   ├── mindforge/              # 核心 Python 包（CLI + 业务逻辑）
│   │   ├── cli.py              # CLI 入口，Typer app 定义
│   │   ├── strategies/         # 策略注册与发现
│   │   ├── llm/                # LLM provider 层
│   │   ├── processors/         # 处理流水线 step 实现
│   │   ├── services/           # 服务层（library, review, wiki 等）
│   │   ├── relations/          # 确定性知识图谱（GraphPort、社区检测、发现上下文）
│   │   ├── retrieval/          # 检索端口抽象与实现（RetrievalPort、Bm25RetrievalEngine）
│   │   ├── extensions/         # 安全扩展边界（ExtensionManifest、ExportAdapter）
│   │   ├── sources/            # SourceAdapter 层（13 种文件格式解析）
│   │   ├── presenters/         # 展示层（CLI 输出格式化）
│   │   ├── health/             # 知识健康诊断引擎
│   │   ├── provenance/         # 溯源链路（Source Location）
│   │   ├── quality/            # 卡片和 Wiki 质量评估
│   │   ├── dogfood/            # Dogfood 场景自动化和使用报告
│   │   ├── wiki/               # Wiki 服务层
│   │   ├── lexical_index.py    # BM25 词法检索引擎
│   │   ├── provider_readiness.py  # Provider 就绪状态诊断
│   │   ├── input_safety.py     # 导入安全校验
│   │   └── prompts_runtime.py  # Prompt 运行时加载
│   └── mindforge_web/          # Web 后端（FastAPI）
│       ├── app.py              # FastAPI 应用入口
│       ├── routers/            # API 路由（15 个端点模块）
│       ├── schemas/            # Pydantic 模型（package: __init__.py + 12 domain 子模块）
│       ├── services/           # Web 服务层（web_facade orchestration + domain services）
│       └── presenters/         # Web 展示层 — 从 web_facade.py 提取的响应构建器（v4.7-v4.8）
├── web/                        # React 前端（TypeScript + Tailwind）
├── tests/                      # pytest 测试
├── prompts/                    # Prompt 模板（运行时资产）
├── configs/                    # 示例配置
├── docs/                       # 文档
│   ├── zh-CN/                  # 中文用户文档
│   ├── en/                     # 英文用户文档
│   ├── dev/                    # 开发者文档
│   ├── design/                 # 设计文档（RFC、SDD、Roadmap）
│   ├── plans/                  # 阶段规划文档
│   ├── implementation-notes/   # 实现笔记
│   └── internal/               # 内部规则和账本
└── examples/                   # 示例和 fixture
```

---

## 核心链路

```
Source → SourceAdapter → Processing Workflow → ai_draft
                                                    │
                                              Human Review
                                                    │
                                              Explicit Approve
                                                    │
                                              human_approved
                                                    │
                                    ┌───────────────┼───────────────┐
                                    │               │               │
                                  Library        Recall          Wiki
                                 (浏览)        (BM25 检索)   (LLM synthesis)
```

---

## 核心模块

### CLI 层 (`cli.py`)

Typer 应用定义，命令注册。每个命令族由独立的 `*_cli.py` 模块实现：

| 模块 | 职责 |
|------|------|
| `process_cli.py` | `mindforge process` 命令 |
| `approval_cli.py` | `mindforge approve` 命令 |
| `strategy_cli.py` | `mindforge strategies` 命令 |
| `wiki_cli.py` | `mindforge wiki` 命令 |
| `watch_cli.py` | `mindforge watch` 命令 |
| `import_cli.py` | `mindforge import` 命令 |
| `runs_cli.py` | `mindforge runs` 命令 |
| `library_cli.py` | `mindforge library` 命令 |
| `recall_index_cli.py` | `mindforge recall` 命令 |

### 策略层 (`strategies/`)

策略注册与发现。定义策略元数据（provider_mode、safety_policy、output_schema_id），提供 `build_strategy()` 工厂。

内建策略：
- `knowledge_card`（默认）：标准知识卡片提取
- `five_stage`：五段式处理流水线

### Provider 层 (`llm/`)

LLM provider 抽象，协议差异收敛在 provider 内部：

| 模块 | 协议 |
|------|------|
| `llm/openai_compatible.py` | `POST /chat/completions` |
| `llm/anthropic_compatible.py` | `POST /v1/messages` |

### 处理流水线 (`processors/`)

固定五段 Knowledge Card Workflow：Triage → Distill → Link Suggestion → Review Questions → Action Extraction。每个 step 可路由到不同模型。

### 服务层 (`services/`)

| 服务 | 职责 |
|------|------|
| `library_service.py` | 知识卡片 CRUD |
| `review_service.py` | 草稿审阅 |
| `wiki_service.py` | Wiki 生成 |
| `recall_service.py` | BM25 检索 |
| `approval_service.py` | 审批状态管理 |
| `trash_service.py` | 回收站 |

### Web 后端 (`mindforge_web/`)

FastAPI 应用，与 CLI 共享同一 Python 服务层。路由：

| 路由模块 | 职责 |
|----------|------|
| `routers/setup.py` | 模型配置 API |
| `routers/sources.py` | Source 管理 API |
| `routers/review.py` | 审阅 API |
| `routers/library.py` | Library API |
| `routers/wiki.py` | Wiki API |
| `routers/recall.py` | BM25 检索 API |
| `routers/graph.py` | 知识图谱 API（关系、社区） |
| `routers/health.py` | 知识健康诊断 API |
| `routers/provenance.py` | 溯源链路 API |
| `routers/export.py` | 安全导出 API |
| `routers/import_.py` | 本地导入 API |
| `routers/trash.py` | 回收站 API |
| `routers/dogfood.py` | 工作台使用报告 API |
| `routers/provider_readiness.py` | Provider 就绪状态 API |
| `routers/lifecycle.py` | Source-to-Card 生命周期 API |

### 图谱与关系 (`relations/`)

确定性知识图谱，基于共享标签、来源、Wiki 章节等构建关系。不调用 LLM，不使用 embedding/vector DB。
当前正式支持并暴露的 graph NodeType 只有 `card` / `source` / `tag` / `wiki_section`。
`community` / `topic` / `entity` / `concept_candidate` 仍是 ontology 或 lab/internal
概念，不应作为已完成的主产品图查询能力声明。

| 模块 | 职责 |
|------|------|
| `relations/graph_builder.py` | 确定性图谱构建器 |
| `relations/related_cards.py` | 多跳关联卡片计算 |
| `relations/community.py` | 知识社区检测与分组 |
| `relations/discovery_context.py` | 可解释发现上下文组装 |
| `relations/graph_port.py` | GraphPort 抽象（参考 ADR-002） |

> **当前状态**: Library 内的 Local Graph Preview / Graph Explorer 是用户可见入口。
> 独立 `/graph` 路由和 Sensemaking 分析保留为 lab/internal；Sensemaking 的
> bridge/evolution/influence 等结果来自简单确定性 heuristics，不是成熟的
> graph analytics 或产品主路径。

### 检索 (`lexical_index.py`)

BM25 词法匹配检索引擎。纯本地、确定性、零外部依赖。不调用 embedding/vector DB。

| 组件 | 职责 |
|------|------|
| `lexical_index.py` | BM25 索引构建与查询 |
| `RetrievalPort` | 检索抽象（参考 ADR-001） |

### 导入导出

安全本地导入导出管线。所有导入仅创建 `ai_draft`，显式审批不可绕过。

| 模块 | 职责 |
|------|------|
| `mindforge_web/services/web_import_export_service.py` | 导入逻辑（import_card、preview_folder_import、import_from_folder、_find_duplicates） |
| `mindforge_web/routers/library.py` | 导入导出 API 端点（import、export、folder-import）；export_cards 仍在 router 层 |
| `mindforge/sources/` (13 adapters) | 源文件格式解析（Markdown/DOCX/PDF/HTML/TXT/ChatExport 等） |
| `mindforge/obsidian_stage.py` | Obsidian staged export 安全路径规划（不写真实 vault） |

> **当前状态 (v4.8)**: import 逻辑已提取到 `web_import_export_service.py`；export 逻辑仍在 `routers/library.py` 中。`web_facade.py` 已从 2163 行减至 922 行 (-57.4%)：lab/internal 方法 → `web_lab_service.py`、recall → `web_recall_service.py`、import/export → `web_import_export_service.py`、响应构建器 → `mindforge_web/presenters/`（7 个文件）。

### 知识健康 (`health/`)

纯本地诊断引擎，检测结构性问题（孤立卡片、低质量、过期 Wiki、溯源缺失等）。不调用 LLM。

### Provider 就绪 (`provider_readiness.py`)

Provider 配置状态诊断，报告哪些 alias 可用、阻塞原因、是否需要 API key。不返回 key 值。

---

## 关键设计决策

### 显式审批不可绕过

`ai_draft` → `human_approved` 只能通过显式用户确认。不存在自动审批路径。Wiki 只从 `human_approved` 生成，不可绕过审批。

### API Key 不进 YAML

API key 通过 Web Setup 存入 local secret store（`.mindforge/secrets.json`），provider runtime 从 secret store 取 key。YAML config 从不包含 raw key。

### 策略元数据作者是策略模块

每个策略模块声明自己的元数据（DISPLAY_NAME、DESCRIPTION、provider_mode、safety_policy、output_schema_id），registry 只汇总。CLI 列表和文档生成器从 registry 取数据。

### CLI 和 Web 共享服务层

CLI 和 Web 使用相同的 service 层，保证行为一致。CLI 的 `*_cli.py` 模块和 Web 的 `routers/*.py` 都调用相同的 service。

### SourceAdapter 归一化

不同文件格式通过 SourceAdapter 层归一化为统一流水线输入。后续 step 不感知原始格式。

---

## 安全架构

| 边界 | 实现 |
|------|------|
| API key 隔离 | Secret store 独立于 config YAML |
| 审批门禁 | 所有 approve 路径检查显式确认 |
| Wiki 数据源 | 只读 `human_approved`，不读 raw source |
| Provider 日志 | 白名单字段，不含 key/prompt/completion |
| 前端安全 | API 只返回 masked key |
| 本地优先 | 不联网，不上传 telemetry |
