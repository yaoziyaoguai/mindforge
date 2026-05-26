# v4.8 Global Architecture Quality Audit

**日期**: 2026-05-26
**HEAD**: 5ee842e
**状态**: complete — 全局架构事实基线

---

## 1. Current Architecture Map

### 1.1 分层视图（当前真实状态，非目标）

```
┌─────────────────────────────────────────────────────────┐
│ Frontend (web/src/)                                      │
│   pages/ (13 pages)  api/ (18 modules)  components/ (30) │
│   零前端测试                                              │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP/JSON
┌──────────────────────────▼──────────────────────────────┐
│ Web Adapter (mindforge_web/)                             │
│   routers/ (19 files, 1598 lines)  ← 全薄路由，但……     │
│   services/web_facade.py (2163 lines, 45 methods)        │
│     ↑ 所有 19 routers 都依赖这一个 facade                 │
│   schemas/ (5 files, 1463 lines, 126 classes)            │
│   services/ (5 extracted: config/source/review/          │
│              path_action/processing_run)                  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│ Core Domain (mindforge/)                                  │
│   cards/  services/  processors/  strategies/            │
│   lexical_index.py  provider_readiness.py                │
│   relations/ (lab/internal)  ← 被 web_facade 直接引用    │
│   health/  provenance/  quality/  wiki/  dogfood/        │
│   llm/  sources/  presenters/  extensions/               │
└─────────────────────────────────────────────────────────┘
```

### 1.2 模块分类

| 模块 | 分类 | 行数 | 说明 |
|------|------|------|------|
| `web_facade.py` | Web adapter (God Object) | 2163 | 45 methods, 20 helpers, 10+ domains |
| `schemas/__init__.py` | Schema/DTO (partial God) | 1091 | 99 remaining classes, 38 extracted |
| `routers/` | Web adapter (thin) | 1598 | 19 files, avg 84 lines, all call web_facade |
| `web_config_service.py` | Web adapter (extracted) | 1017 | Config/setup domain |
| `web_source_service.py` | Web adapter (extracted) | 713 | Source/watch domain |
| `processing_run_service.py` | Web adapter (extracted) | 760 | Processing run domain |
| `web_review_service.py` | Web adapter (extracted) | 228 | Review domain |
| `web_path_action_service.py` | Web adapter (extracted) | 312 | Path action domain |
| `dogfood_service.py` | Web adapter (extracted) | 180 | Dogfood domain |
| `relations/` | Core domain (lab/internal) | — | Graph/Sensemaking/Community/Entity |
| `services/` (core) | Core domain | — | library/review/wiki/recall/approval |

### 1.3 依赖方向（当前）

```
routers/*.py ──→ web_facade.py ──→ core services + schemas + relations (lab)
                                      ↑
                                      └── 所有依赖都经过这一个节点
```

---

## 2. Monolith / God Object Audit

### 2.1 web_facade.py — GOD OBJECT

| 指标 | 值 |
|------|-----|
| 行数 | 2163 |
| Public methods | 45 |
| Module-level helpers | 20 |
| Imported by | 19/19 routers |
| Domain responsibilities | 10+ |

**职责分解：**

| 职责域 | 方法 | 行数 | 主路径? | 现状 |
|--------|------|------|---------|------|
| Home/Status | 3 | ~240 | 是 | 直接在 facade |
| Config/Setup | 4 | ~130 | 是 | 委托 WebConfigService |
| Sources/Watch | 5 | ~130 | 是 | 委托 WebSourceService |
| Library | 2 | ~60 | 是 | 直接在 facade |
| Import/Export | 4 | ~380 | 是 | 直接在 facade + helper |
| Drafts/Review | 3 | ~80 | 是 | 委托 WebReviewService |
| Recall | 1 | ~100 | 是 | 直接在 facade |
| Wiki | — | — | 是 | 在 routers/wiki.py (378行) |
| Dogfood | 1 | ~60 | internal | 委托 dogfood_service |
| Provider Readiness | 1 | ~30 | 是 | 直接在 facade |
| Lifecycle | 0 | — | 是 | 在 web_source_service |
| Workflow | 1 | ~30 | 是 | 直接在 facade |
| Trash | 0 | — | 是 | 在 router 直接操作 |
| **Graph** | 3 | ~60 | lab/internal | 直接在 facade |
| **Sensemaking** | 1 | ~80 | lab | 直接在 facade |
| **Communities** | 1 | ~50 | lab/internal | 直接在 facade |
| **Topics** | 1 | ~30 | lab/internal | 直接在 facade |
| **Discovery** | 1 | ~30 | lab | 直接在 facade |
| Quality/Location | 2 | ~30 | internal | 直接在 facade |
| Helpers | 20 | ~500 | — | 模块级函数 |

**判断：GOD OBJECT**
- 45 methods 跨 10+ 领域
- 19/19 routers 强制耦合到此单点
- lab/internal code (graph/sensemaking) 与主路径混在同一类
- 虽然已有 5 个 service 被委托，但 facade 仍然是中心化调度器

**推荐拆分方式：**
- 不是把 45 methods 拆成 45 个 service
- 保留 web_facade 作为 thin orchestration facade（~200 lines）
- 拆出独立 service：ImportExportService、RecallWikiService、DogfoodService
- Graph/Sensemaking/Discovery 方法移至单独的 lab service 或保持现状

### 2.2 schemas/__init__.py — PARTIAL GOD

| 指标 | 值 |
|------|-----|
| 行数 | 1091 (was 1375, -21%) |
| 剩余类 | 99 (was 62, +37 — 子模块 re-export) |
| 子模块 | 4 (common, import_export, dogfood_lifecycle, review) |

**剩余 schema 分组（估算）：**

| 分组 | 行数 | 主路径? |
|------|------|---------|
| Provider/Config/Setup | ~300 | 是 |
| Sources/Watch | ~130 | 是 |
| Home/Status | ~80 | 是 |
| Library | ~100 | 是 |
| Graph | ~60 | lab/internal |
| Provenance | ~50 | 是 |
| Recall | ~40 | 是 |
| Quality | ~30 | 是 |
| Community/Topic | ~60 | lab/internal |
| Sensemaking | ~70 | lab |
| Trash | ~50 | 是 |
| Re-exports (4 sub-modules) | ~30 | — |

**判断：仍在巨石化**
- 99 classes 在一个文件仍然过大
- 但 v4.7 extraction pattern 已经建立（common → domain sub-modules）
- 继续按 domain 提取不会引入新风险

### 2.3 Routers — THIN BUT COUPLED

所有 19 个 routers 都直接依赖 `web_facade.py`。好消息是大多数 routers 本身很薄：

| Router | 行数 | web_facade refs | 判断 |
|--------|------|-----------------|------|
| wiki.py | 378 | 33 | 偏大，业务逻辑在 router 内 |
| library.py | 298 | 29 | 偏大 |
| sources.py | 158 | 21 | 合理 |
| trash.py | 146 | 15 | 合理 |
| config.py | 59 | 13 | 合理 |
| graph.py | 107 | 9 | 合理（lab） |

**判断：wiki.py (378行) 和 library.py (298行) 承载了过多逻辑**

### 2.4 Core Services — HEALTHY BUT INCOMPLETE

| Service | 行数 | 状态 |
|---------|------|------|
| library_service.py | — | 合理 |
| review_service.py | — | 合理 |
| approval_service.py | — | 合理 |
| recall_service.py | — | 合理 |
| wiki_service.py | — | 合理 |
| trash_service.py | — | 合理 |

Web 对应的 service 层尚未完全对齐：
- 没有 WebImportService（import/export 在 web_facade）
- 没有 WebRecallService（recall 在 web_facade）
- 没有 WebWikiService（wiki 逻辑在 router wiki.py 中）

---

## 3. Coupling Audit

### 3.1 Router → web_facade 强制耦合

**问题：** 所有 19/19 routers 都通过 `web_facade` 访问所有能力。无法只 import 需要的部分。

**影响：**
- 新增 router 时必须理解整个 web_facade
- web_facade 的任何改动影响所有 router 的测试
- 无法为单个 router 做 isolation test

### 3.2 web_facade → relations (lab/internal) 耦合

**问题：** web_facade 的 graph/sensemaking/discovery/community/topic 方法直接 import `mindforge.relations.*`。主路径代码和 lab 代码共享同一个 facade 实例。

**当前状态：** 主路径 routers 不直接依赖 lab modules（通过 grep 验证，零 hits）。但 web_facade 的 lab 方法使边界模糊。

### 3.3 Schemas 互相纠缠

**问题：** `__init__.py` 中剩余 99 classes 共享同一个文件命名空间。虽然 v4.7 已提取 38 个独立 schema，但 Provider/Config/Setup/Library/Graph/Sensemaking 等仍混在一起。

**实际风险：** 低。Schema 是声明式数据定义，交叉引用只通过类型注解。不存在"schema A 方法调用 schema B 方法"的情况。

### 3.4 Frontend API 同步

前端 `web/src/api/` 有 18 个模块，与后端 19 个 routers 基本一一对应。类型定义在 `types.ts`。

**判断：** 结构基本合理，零测试覆盖是主要债务。

### 3.5 Lab/Internal 是否污染主路径？

**Structurally clean but semantically fuzzy.** 主路径 routers 不 import lab 模块。但 web_facade 作为中央调度器，同时暴露主路径和 lab 方法。前端 GraphPage/SensemakingPage 通过各自的 API 模块独立访问。

---

## 4. Abstraction Audit

### 4.1 现有抽象价值评估

| 抽象 | 类型 | 价值 | 建议 |
|------|------|------|------|
| `RetrievalPort` | ABC | 中等 | 当前只有 BM25 实现，保留以备未来扩展 |
| `GraphPort` | ABC | 低 | 只有 DeterministicGraphBuilder 一个实现，尚未证明需要多态 |
| `GraphRepository` | Repository | 低 | 在 GraphPort 之上的一层薄封装，增加 indirection 而未见使用 |
| `ExportAdapter` | ABC | 中等 | 已定义但无实现，保留以备未来真实的 export plugins |
| `ExtensionManifest` | Schema | 低 | Plugin system 预留，当前无实际使用 |
| `SourceAdapter` (13) | ABC | 高 | 核心价值抽象，支撑 13+ 种文件格式归一化 |
| `Strategy` pattern | Registry | 高 | 策略注册与发现，核心设计模式 |

### 4.2 判断原则

- **保留** 真正有多个实现或已证明业务价值的 ABC
- **不新增** Port/ABC 专门为了"架构看起来好" — v4.7 原则已证明有效
- **不删除** 已存在的 ABC（即使价值低），除非它阻碍重构
- GraphPort、GraphRepository、ExtensionManifest 保持现状但不扩张

---

## 5. Main Path Boundary Audit

主路径流程和当前模块对应：

```
Source/Import ──→ web_facade.import_card/preview_folder_import
                      ↓
              processing workflow (core)
                      ↓
              ai_draft ──→ web_facade.drafts/draft_detail
                      ↓
              Review ──→ WebReviewService (extracted) ✓
                      ↓
              explicit approval ──→ approval_service (core)
                      ↓
              human_approved ──→ web_facade.library_cards
                      ↓
    ┌─────────┼─────────┬──────────┐
    ↓         ↓         ↓          ↓
  Library  Recall    Wiki       Export
(web_fac) (web_fac) (router)  (web_fac)
```

**边界评估：**

| 步骤 | 边界清晰度 | 问题 |
|------|-----------|------|
| Import | C | 逻辑在 web_facade，380 行 inline |
| ai_draft | B | 通过 core processing，边界合理 |
| Review | A | 已委托 WebReviewService |
| Approval | A | 通过 core approval_service |
| Library | B | 在 web_facade 中，但只有 60 行 |
| Recall | C | 在 web_facade 中，100 行 inline |
| Wiki | C | 在 router wiki.py (378行) 中直接实现 |
| Export | C | 在 web_facade 中，与 import 共享 380 行 |

**最急需改善的主路径步骤：Import/Export、Recall/Wiki**

---

## 6. Test Architecture Audit

### 6.1 现有测试分类

| 类别 | 文件 | 行数 | 质量 |
|------|------|------|------|
| Approval boundary | test_review_approval_boundary.py | ~500 | 高 — 保护安全语义 |
| Module boundary | test_module_boundary_contract.py | 132 | 中 — 已适配 schemas package |
| Package safety | test_package_safety.py | ~200 | 高 — artifact-level checks |
| Product copy | test_web_product_copy.py | 1681 | 高 — 防止 lab 功能被宣传为主路径 |
| Web API integration | test_web_api.py | 5447 | 中 — 覆盖广但部分脆弱 |
| Process/approve/service boundaries | 多个文件 | ~2000 | 高 — 保护 service 边界 |
| Sensemaking | test_sensemaking.py | 558 | 低 — 测试 lab 功能 |
| Dogfood | test_dogfood.py | — | 低 — 内部工具测试 |

### 6.2 缺失的测试

| 缺什么 | 为什么需要 |
|--------|-----------|
| **Architecture boundary tests** | 验证 main path 不 import lab modules |
| **Schema import direction tests** | 验证 schema 子模块 import 方向正确 |
| **Frontend smoke tests** | 0 frontend tests in web/src/ |
| **API contract tests** | 验证 API shape 不退化 |
| **web_facade isolation tests** | 验证 service 边界不泄露 |

---

## 7. 关键发现总结

1. **web_facade.py 是最大瓶颈** — 2163 行/45 methods，所有 19 routers 强制耦合
2. **schemas/__init__.py 仍是巨石** — 1091 行/99 classes，需继续按 domain 模块化
3. **Lab/Internal 代码物理上在主路径代码中** — graph/sensemaking 方法在 web_facade 内部
4. **wiki.py router 过大** — 378 行，承载了 wiki service 本该处理的逻辑
5. **0 前端测试**
6. **架构边界测试缺失**
7. **好消息：router 都很薄，分层方向正确，5 个 service 已成功提取**
8. **好消息：v4.7 extraction pattern 已验证可行，可以继续**

---

## 8. 风险矩阵

| 风险 | 严重度 | 发生概率 | 建议 |
|------|--------|---------|------|
| web_facade 继续增长 | 高 | 高 | 拆分 import/export/recall 为独立 service |
| schemas 重新膨胀 | 中 | 低 | v4.7 pattern 建立后风险降低 |
| lab 代码被当作主路径 | 中 | 中 | 架构边界 tests |
| 新增 router 绕过 facade | 低 | 低 | 当前 pattern 已固定 |
| 前端 API 不同步 | 低 | 中 | 零测试是隐患 |
