# v4.8 Target Architecture Map

**日期**: 2026-05-26
**基于**: docs/audits/2026-05-26-099-global-architecture-quality-audit.md
**状态**: target reference — 指导 v4.8 重构方向

---

## 1. 目标分层

```
┌──────────────────────────────────────────────────────┐
│ Presentation / Web UI (web/src/)                      │
│   13 pages → 18 API modules → 30+ components          │
│   目标：加 1 个 smoke test，不重构前端                 │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP/JSON
┌───────────────────────▼──────────────────────────────┐
│ Web Adapter Layer (mindforge_web/)                     │
│                                                       │
│  routers/ (19 thin files)                              │
│    └─ 每个 router ~20-100 lines                        │
│    └─ 只做：参数解析、调用 service、返回 response       │
│    └─ 不做：业务逻辑、数据转换、复杂编排               │
│                                                       │
│  services/web_facade.py (~400 lines target)            │
│    └─ Thin orchestration facade                        │
│    └─ 负责：app_context 创建、config 注入              │
│    └─ 委托：所有 domain logic 到独立 service           │
│                                                       │
│  services/web_import_export_service.py (new)           │
│    └─ Import/Export 的所有逻辑                         │
│                                                       │
│  services/web_recall_wiki_service.py (new)             │
│    └─ Recall + Wiki 的 Web adapter 逻辑               │
│                                                       │
│  services/web_dogfood_service.py (exists)              │
│  services/web_config_service.py (exists)               │
│  services/web_source_service.py (exists)               │
│  services/web_review_service.py (exists)               │
│  services/web_path_action_service.py (exists)          │
│  services/processing_run_service.py (exists)           │
│                                                       │
│  schemas/ (package)                                    │
│    ├── __init__.py (re-exports only, ~100 lines)       │
│    ├── common.py (shared types)                        │
│    ├── provider.py (new — provider/config/status)      │
│    ├── source.py (new — source/watch/ingestion)        │
│    ├── library.py (new — library/card)                 │
│    ├── import_export.py (exists)                       │
│    ├── review.py (exists)                              │
│    ├── recall.py (new — recall/search)                 │
│    ├── wiki.py (new — wiki)                            │
│    ├── graph.py (new — graph, lab/internal)            │
│    ├── sensemaking.py (new — sensemaking, lab)         │
│    ├── dogfood_lifecycle.py (exists)                   │
│    ├── trash.py (new — trash)                          │
│    └── quality.py (new — quality/health)               │
│                                                       │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│ Core Domain Layer (mindforge/)                          │
│                                                       │
│  services/ (library/review/wiki/recall/approval 等)    │
│    └─ 与 CLI 和 Web 共享                               │
│    └─ 不做 Web adapter 逻辑                            │
│                                                       │
│  cards/ processors/ strategies/ llm/ sources/          │
│  lexical_index.py provider_readiness.py                │
│                                                       │
│  relations/ (lab/internal)                              │
│    └─ 明确标记 LAB/INTERNAL                             │
│    └─ 不被主路径 service 直接 import                   │
│                                                       │
└──────────────────────────────────────────────────────┘
```

---

## 2. 依赖方向规则

```
routers → web_facade (thin) → specific web services → core services
                ↓
           schemas (domain modules, re-exported via __init__.py)

禁止：
  router → core service (绕过 web_facade)
  router → relations (lab/internal) (绕过 web_facade 也不行)
  schema domain module → schema domain module (除了 common)
  web service → other web service (只能通过 web_facade)

允许：
  web service → core service
  web service → schemas (domain module)
  web service → cards/config (core domain)
```

---

## 3. 关键设计决策

### 3.1 web_facade 保留但瘦身

**不删除 web_facade**。它作为：
- AppContext 创建与 config 注入的单一入口
- Router → Service 的干净调度层
- 避免每个 router 需要自己管理 app_context

**目标大小：~400 lines**（从 2163 减少 80%）

### 3.2 Schema 模块化但不机械

- 每个 domain 有自己的 schema module
- `__init__.py` 只做 re-exports（~100 lines）
- 共享类型只在 `common.py`
- Lab/internal schema 也独立文件，但标记清楚

### 3.3 不新增 Port/ABC

- 本轮目标是减少巨石，不是引入新架构模式
- 已存在的 ABC 保留但不扩张
- 新 service 是 plain class，不是 protocol 实现

### 3.4 Lab/Internal 物理隔离

- Graph/Sensemaking/Community/Topic schema 在独立文件
- web_facade 中的 graph/sensemaking 方法移至独立文件或标记为 lab
- 架构 boundary tests 验证隔离

---

## 4. 不做什么

- 不重写前端架构
- 不新增 Port/ABC/Repository
- 不删除 Graph/Sensemaking/Entity 代码
- 不改变 API contract
- 不改变 explicit approval/human_approved 语义
- 不做大 bang 重构（一次只动一个 domain）
