---
title: "MindForge Knowledge OS Architecture Map"
type: architecture-reference
date: 2026-05-25
version: v2.0
status: active
---

# MindForge Knowledge OS Architecture Map

## 分层模型

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Frontend (React/Vite)                  │
│  pages/ + components/ + api/ + lib/                         │
├─────────────────────────────────────────────────────────────┤
│                  Web API Layer (FastAPI)                     │
│  routers/ ──→ schemas.py ──→ services/web_facade.py         │
├─────────────────────────────────────────────────────────────┤
│                   CLI Layer (Typer)                          │
│  cli.py, *_cli.py, *_presenter.py                           │
├─────────────────────────────────────────────────────────────┤
│                   Service Layer (core)                       │
│  *_service.py, relations/, health/, llm/, lexical_index     │
├─────────────────────────────────────────────────────────────┤
│                   Policy Layer                               │
│  safety_policy, input_safety, obsidian_manifest_policy      │
├─────────────────────────────────────────────────────────────┤
│                   Adapter Layer                              │
│  obsidian_*, cubox_*, llm/fake, llm/openai, llm/anthropic   │
├─────────────────────────────────────────────────────────────┤
│                   Data Layer                                 │
│  cards.py, config.py, models.py, checkpoint.py, envelope    │
└─────────────────────────────────────────────────────────────┘
```

## Layer Rules

| Layer | 可 import | 不可 import |
|-------|----------|------------|
| Data | stdlib, yaml | 任何 MindForge 模块（除同层） |
| Adapter | Data, Policy, stdlib | Service, CLI, Web |
| Policy | Data, stdlib | Service, Adapter, CLI, Web |
| Service | Data, Policy, Adapter | CLI, Web |
| CLI | Service, Data, Policy | Web |
| Web API | Service, Data, Policy（通过 WebFacade） | CLI（违反则记） |
| Web Frontend | Web API (via HTTP) | Core Python modules |

## 模块清单

### Data Layer（数据模型与持久化）

| 模块 | 文件 | 职责 | 依赖 |
|------|------|------|------|
| cards | `cards.py` | 卡片扫描、frontmatter 解析、CardSummary | yaml, pathlib |
| config | `config.py` | 配置加载、VaultConfig、LLMConfig、ProviderConfig | cards (type refs) |
| models | `models.py` | 数据模型定义 | — |
| checkpoint | `checkpoint.py` | 处理状态检查点 | — |
| envelope | `envelope.py` | 数据封装/解封 | — |
| evidence | `evidence.py` | 证据收集 | — |
| secret_store | `secret_store.py` | Secret 管理（presence-only） | — |

### Policy Layer（安全与合规策略）

| 模块 | 文件 | 职责 |
|------|------|------|
| safety_policy | `safety_policy.py` | 全局安全边界定义、Obsidian workflow 安全线 |
| input_safety | `input_safety.py` | 输入安全检查 |
| obsidian_manifest_policy | `obsidian_manifest_policy.py` | Obsidian 导出安全策略 |
| provider_readiness | `provider_readiness.py` | Provider 就绪状态检查（presence-only） |

### Adapter Layer（外部系统适配）

| 模块 | 文件 | 类型 | 职责 |
|------|------|------|------|
| llm/fake | `llm/fake.py` | fake | 默认 fake provider |
| llm/openai | `llm/openai_compatible.py` | real-opt-in | OpenAI 兼容 provider |
| llm/anthropic | `llm/anthropic_compatible.py` | real-opt-in | Anthropic 兼容 provider |
| llm/factory | `llm/factory.py` | infra | Provider 工厂 |
| llm/client | `llm/client.py` | infra | LLM client wrapper |
| llm/base | `llm/base.py` | infra | LLM base types |
| obsidian_stage | `obsidian_stage.py` | safe | Staged export |
| obsidian_workflow | `obsidian_workflow.py` | safe | Obsidian 工作流导航 |
| obsidian_cli | `obsidian_cli.py` | safe | Obsidian CLI 命令 |
| obsidian_cli_presenter | `obsidian_cli_presenter.py` | safe | Obsidian CLI 格式化 |
| obsidian | `obsidian.py` | safe | Obsidian 集成 |
| cubox_readiness | `cubox_readiness.py` | safe | Cubox 就绪检查 |
| cubox_dryrun_presenter | `cubox_dryrun_presenter.py` | safe | Cubox dry-run 展示 |
| source_archive_service | `source_archive_service.py` | safe | Source 归档 |
| assets_runtime | `assets_runtime.py` | infra | 运行时资产路径 |
| prompts_runtime | `prompts_runtime.py` | infra | Prompt 模板加载 |
| scanner | `scanner.py` | safe | 文件扫描 |

### Service Layer（核心业务逻辑）

| 模块 | 文件 | 职责 |
|------|------|------|
| approval_service | `approval_service.py` | 审批服务 |
| approver | `approver.py` | 审批核心逻辑 |
| review_service | `review_service.py` | 审阅服务 |
| reviewer | `reviewer.py` | 审阅核心逻辑 |
| library_service | `library_service.py` | 知识库查询 |
| recall_service | `recall_service.py` | BM25 召回服务 |
| lexical_index | `lexical_index.py` | BM25 词法索引实现 |
| card_workspace_service | `card_workspace_service.py` | 卡片正文编辑 |
| ingestion_service | `ingestion_service.py` | Source ingestion |
| ingestion_diagnostics | `ingestion_diagnostics.py` | Ingestion 诊断 |
| wiki_service | `wiki_service.py` | Wiki 合成服务 |
| wiki_renderer | `wiki_renderer.py` | Wiki 渲染 |
| wiki_view_model | `wiki_view_model.py` | Wiki 视图模型 |
| trash_service | `trash_service.py` | 回收站服务 |
| health/health_service | `health/health_service.py` | 知识健康检查 |
| relations/graph_builder | `relations/graph_builder.py` | 确定性图谱构建 |
| relations/graph_models | `relations/graph_models.py` | 图谱数据模型 |
| relations/graph_port | `relations/graph_port.py` | 图谱端口抽象 |
| relations/local_graph | `relations/local_graph.py` | 卡片中心局部图 |
| relations/related_cards | `relations/related_cards.py` | 关联卡片计算 |
| relations/community | `relations/community.py` | 社区检测 |
| relations/discovery_context | `relations/discovery_context.py` | 发现上下文组装 |
| relations/scoring | `relations/scoring.py` | 关系评分 |
| process_service | `process_service.py` | 处理流水线服务 |
| process_executor | `process_executor.py` | 处理执行器 |
| source_mux | `source_mux.py` | Source multiplexer |
| source_discovery | `source_discovery.py` | Source 发现 |
| watch_registry | `watch_registry.py` | Watch 注册 |
| strategy_selection | `strategy_selection.py` | 策略选择 |
| strategy_display | `strategy_display.py` | 策略展示 |
| project_context | `project_context.py` | 项目上下文 |
| multi_project_context | `multi_project_context.py` | 多项目上下文 |

### CLI Layer（命令行接口）

| 模块 | 职责 |
|------|------|
| `cli.py` | CLI 入口 |
| `cli_runtime.py` | CLI 运行时 |
| `*_cli.py` (approval, review, library, recall, wiki, etc.) | 各领域 CLI 命令 |
| `*_presenter.py` | CLI 输出格式化 |
| `web_cli.py` | `mindforge web` 命令 |

### Web API Layer（FastAPI 后端）

| 模块 | 文件 | 职责 |
|------|------|------|
| App | `app.py`, `server.py` | FastAPI 应用入口 |
| Deps | `deps.py` | 依赖注入 |
| Schemas | `schemas.py` | API 请求/响应 Pydantic 模型 |
| WebFacade | `services/web_facade.py` | Web 场景编排（1400+ lines） |
| Routers | `routers/*.py` (16 files) | API 端点定义 |
| Services | `services/web_*.py` (6 files) | Web 专属服务 |

### Web Frontend（React/Vite/Tailwind）

| 层级 | 文件 | 职责 |
|------|------|------|
| Pages | `pages/*.tsx` (11 files) | 页面级组件 |
| Components | `components/*.tsx` (30+ files) | 可复用组件 |
| API | `api/*.ts` (12 files) | API client 函数 |
| Lib | `lib/i18n.ts`, `lib/utils.ts`, `lib/wiki-renderer.ts` | 工具库 |

## 跨层依赖边界

### 正确依赖方向

```
Web Frontend → Web API → Service → Data
                  ↓
               Policy (injected)
```

### 已知边界违规（v2.0 审计发现，不修复）

| 违规 | 文件 | 描述 | 严重度 |
|------|------|------|--------|
| CLI → Web | `cli_processing_runtime.py` | import mindforge_web | P2 |
| CLI → Web | `processing_worker.py` | import mindforge_web | P2 |
| CLI → Web | `runs_cli.py` | import mindforge_web | P2 |
| Router 内联业务逻辑 | `routers/wiki.py` | inline imports from mindforge.wiki_service | P3 |
| 导出端点内联逻辑 | `routers/library.py:export_cards` | 内联 JSON/OPML 序列化（应在 facade/service 层） | P3 |

P2 违规（CLI → Web）的根因：processing_run_service 放在 `mindforge_web/` 下，但 CLI 也需要它。推荐将此服务迁至 `mindforge/` 核心层。

## 模块依赖图（简化）

```
cards.py ◄── config.py ◄── app_context.py
   ▲              ▲              ▲
   │              │              │
   └── library_service ── WebFacade ── routers
   ┌── approval_service
   ├── review_service
   ├── ingestion_service
   ├── wiki_service
   ├── relations/*
   ├── health/*
   └── lexical_index
```

## Port / Boundary 抽象（已定义）

| Port | 位置 | 默认实现 | 替代方案 |
|------|------|---------|---------|
| GraphPort | `relations/graph_port.py` | `DeterministicGraphBuilder` | Kuzu spike (ADR-002) |
| RetrievalPort | (待正式提取 v2.2) | `lexical_index.py` BM25 | SQLite FTS5 spike (ADR-001) |
| ProviderPort | `llm/base.py` + `llm/factory.py` | `FakeProvider` | OpenAI/Anthropic (opt-in) |

## 参考

- `docs/adr/2026-05-24-001-retrieval-backend.md` — Retrieval backend ADR
- `docs/adr/2026-05-24-002-kuzu-graph-backend.md` — Graph backend ADR
- `docs/dev/architecture.md` — 原架构文档
