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
│   │   ├── presenters/         # 展示层（CLI 输出格式化）
│   │   └── prompts_runtime.py  # Prompt 运行时加载
│   └── mindforge_web/          # Web 后端（FastAPI）
│       ├── app.py              # FastAPI 应用入口
│       ├── routers/            # API 路由
│       ├── schemas.py          # Pydantic 模型
│       └── services/           # Web 服务层
├── tests/                      # pytest 测试
├── prompts/                    # Prompt 模板（运行时资产）
├── configs/                    # 示例配置
├── docs/                       # 文档
│   ├── zh-CN/                  # 中文用户文档
│   ├── en/                     # 英文用户文档
│   ├── dev/                    # 开发者文档
│   ├── design/                 # 设计文档（RFC、SDD、Roadmap）
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
| `routers/recall.py` | Recall API |

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
