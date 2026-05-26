# v4.7 Architecture Debt Reduction Plan

**日期**: 2026-05-26
**状态**: active
**基于**: v4.6 Documentation System Simplification, quality-debt-ledger P2-02/P2-03

---

## 1. 当前问题事实

### web_facade.py — 2163 行

| 职责域 | 方法数 | 行数估算 | 主路径? |
|--------|--------|----------|---------|
| Home/Status/Config | 6 | ~150 | 是 |
| Setup/Config | 5 | ~180 | 是 |
| Sources/Watch | 8 | ~120 | 是 |
| Drafts/Review | 3 | ~50 | 是 |
| Library | 3 | ~60 | 是 |
| Import/Export | 4 | ~380 | 是 |
| Recall | 2 | ~120 | 是 |
| Graph (v0.6) | 3 | ~60 | 否 (lab/internal) |
| Sensemaking (v4.0) | 1 | ~80 | 否 (lab) |
| Discovery Context | 1 | ~30 | 否 (lab) |
| Knowledge Communities/Topics | 2 | ~80 | 否 (lab/internal) |
| Quality/Location | 2 | ~50 | 否 (lab) |
| Dogfood Report | 1 | ~120 | 否 (internal) |
| Provider Readiness | 1 | ~80 | 是 |
| Lifecycle | 1 | ~60 | 是 |
| Workflow | 1 | ~30 | 是 |
| Module-level helpers | ~20 | ~500 | — |

已委托给独立 service 的职责：WebConfigService、WebSourceService、WebReviewService、WebPathActionService、processing_run_service。

仍在 web_facade 中直接实现的：import/export 编排、graph/sensemaking/discovery、communities/topics、dogfood、provider readiness、lifecycle、recall。

### schemas.py — 1375 行

| Schema 分组 | 类数量 | 行数估算 | 主路径? |
|------------|--------|----------|---------|
| Core/Status | 5 | ~50 | 是 |
| Provider/Config | 7 | ~130 | 是 |
| Setup/Config/Model | 20 | ~200 | 是 |
| Sources/Watch | 6 | ~170 | 是 |
| Library | 8 | ~120 | 是 |
| Graph | 5 | ~70 | 否 (lab/internal) |
| Provenance | 5 | ~60 | 是 |
| Import/Export | 10 | ~180 | 是 |
| Drafts/Review/Approval | 7 | ~110 | 是 |
| Recall | 2 | ~40 | 是 |
| Discovery | 7 | ~70 | 否 (lab) |
| Trash | 5 | ~60 | 是 |
| Quality | 4 | ~30 | 是 |
| Community/Topic | 6 | ~70 | 否 (lab/internal) |
| Dogfood | 1 | ~40 | 否 (internal) |
| Lifecycle | 2 | ~30 | 是 |
| Sensemaking | 7 | ~90 | 否 (lab) |

### Routers 依赖方式

所有 20 个 router 文件直接从 `mindforge_web.schemas` import 具体 schema 类。web_facade.py 从 schemas 导入约 80 个类名。

---

## 2. 风险判断

### web_facade.py 是否真的承担过多职责？
**是**。30+ public methods 跨 10+ 领域。虽然已委托 Source/Config/Review 到独立 service，但 import/export、graph、sensemaking、dogfood、community 等仍直接实现在 facade 中。这不是紧急的，但确实阻碍了每个领域的独立理解和测试。

### schemas.py 是否真的阻碍维护？
**部分**。62 个 schema 类挤在单文件中，但 schema 本身是声明式数据形状定义，不包含业务逻辑。主要痛点是：新增 schema 时找位置困难、文件过大导致编辑器性能下降、所有 schema 改动都在同一个 git blame 条目上。

### 高风险拆分
- **拆分 web_facade 中的 graph/sensemaking 方法** — 这些属于 lab/internal，拆分可能被误解为"正在产品化"。
- **拆分 Community/Topic schemas** — 交织在 graph 和 knowledge 体系中，容易制造循环引用。
- **拆分 Library schemas** — `LibraryCardResponse` 被 10+ 个其他 schema 引用（RelatedCard、DraftDetail、Lifecycle等），拆错了影响面大。

### 低风险拆分
- **Import/Export schemas** — 完全自包含，不被其他 schema 组引用。
- **Import/Export service logic from web_facade** — import_card/preview_folder_import/import_from_folder 逻辑自包含，只依赖 cards 和 schemas。
- **Dogfood schemas** — 只被 dogfood router 和 dogfood test 引用。

### 不应该现在动
- Graph/Sensemaking/Entity/Community 相关 schema 和 service 代码 — 这些是 lab/internal，拆分可能被误解为扩展信号。
- web_facade 的 graph/sensemaking/discovery/community 方法 — 同上。
- schemas.py 中的核心类型 (`LibraryCardResponse`, `DraftSummary`, `NextAction`) — 被广泛引用，需要更仔细的规划。

---

## 3. 拆分原则

1. **用户主路径优先** — 先拆 Import/Export/Review/Approval/Library/Recall，不碰 Graph/Sensemaking。
2. **每次只拆一个 coherent slice** — 一个 PR 只动一个领域。
3. **不新增 Port/ABC** — 本轮目标是减少巨石，不是引入新架构模式。
4. **先拆 schema，再拆 service** — schema 是纯数据形状，拆分风险最低，改动了 schema 结构后再拆 service 更安全。
5. **Backward-compatible imports** — 所有 `from mindforge_web.schemas import X` 必须继续工作。
6. **Router/API contract 不变** — 前端 API 调用完全不受影响。
7. **每个 slice 必须有 regression tests** — 至少运行 full pytest + npm build。
8. **只做有意义拆分** — 不为了降低行数机械拆文件。拆分必须改善内聚和可发现性。

---

## 4. 推荐 Slices

### Slice A — Import/Export Schema Extraction（第一刀，推荐）

从 `schemas.py` 提取 import/export 相关 schema 到 `schemas/import_export.py`。

涉及 schema（10 个类，~180 行）：
- `ExportCardsRequest`, `ExportCardsResponse`
- `ImportCardRequest`, `ImportCardResponse`
- `BatchImportCardItem`, `BatchImportCardRequest`, `BatchImportCardResponse`
- `_PotentialDuplicateResponse`
- `FolderImportPreviewRequest`, `FolderImportPreviewResponse`
- `_FolderImportPreviewFile`, `_FolderImportResultItem`
- `FolderImportRequest`, `FolderImportResponse`

**理由**：完全自包含，不被其他 schema 组依赖。只有 routers/library.py 和 web_facade.py 引用这些类。最低风险。

### Slice B — Review/Approval Schema Extraction

从 `schemas.py` 提取 review/approval 相关 schema 到 `schemas/review_approval.py`。

涉及 schema（7 个类，~110 行）：
- `DraftSummary`, `DraftsResponse`, `DraftDetailResponse`
- `ApproveRequest`, `RejectRequest`, `ApprovalResponse`, `UnavailableResponse`
- `CardBodyUpdateRequest`, `CardBodyUpdateResponse`

**理由**：保护 explicit approval 语义。被 routers/drafts.py、routers/approval.py、web_facade.py、web_review_service.py 引用。测试覆盖好。

### Slice C — Import/Export Service Extraction from web_facade

从 `web_facade.py` 提取 import/export 方法到 `services/web_import_service.py`。

涉及方法（4 个方法 + 2 个 helper，~400 行）：
- `import_card()`, `preview_folder_import()`, `import_from_folder()`
- `_find_duplicates()`, `_parse_markdown_title_body()`
- `_REJECTED_FILENAME_PATTERNS`, `_MAX_IMPORT_FILE_BYTES`

**理由**：逻辑自包含，只依赖 cards 和 schemas。提取后 web_facade 减少 ~400 行。必须在 Slice A 完成后再做。

### Slice D — Dogfood Schema + Service Extraction

从 `schemas.py` 提取 DogfoodReportResponse 到独立文件；从 web_facade 提取 dogfood_report()。

**理由**：Dogfood 是 internal 工具，与主路径完全隔离。提取后 web_facade 减少 ~160 行。

### Slice E — Provider Readiness + Lifecycle Schema Extraction

从 `schemas.py` 提取 ProviderReadiness 和 Lifecycle 相关 schema。

**理由**：这两个域各自独立，都是主路径能力（Provider Readiness Center、Source-to-Card Lifecycle）。

---

## 5. 推荐执行顺序

1. **Slice A** — Import/Export Schema Extraction（本轮执行）
2. **Slice B** — Review/Approval Schema Extraction（如果 context 充足）
3. **Slice C** — Import/Export Service Extraction（必须在 A 完成后）
4. Slice D/E — 如果前面顺利且 context 充足

---

## 6. Self-Review

### 是否只是为了降低行数而拆？
**不是**。Import/Export schema 有明显的领域边界，拆到独立文件后：
- 新增 import/export 相关 API 类型时只需找 `schemas/import_export.py`
- import/export 相关改动不再与 Setup/Graph/Sensemaking schema 挤在同一个 diff 中
- 文件大小从 1375 行降到 ~1200 行，提升编辑器响应

### 是否会造成更多小文件和低内聚？
**不会**。使用 `schemas/` package 而非平铺文件。每个子模块有明确的领域边界。`schemas/__init__.py` 统一 re-export，保持 import 路径不变。

### 是否新增了无意义抽象？
**没有**。只是文件级别的重组，不改变类定义、字段类型、继承关系。

### 是否会让 router imports 更混乱？
**不会**。所有 router 仍使用 `from mindforge_web.schemas import X`。

### 是否会破坏 API contract？
**不会**。Pydantic 模型定义不变，JSON schema 生成不变，API response/request shape 不变。

### 是否会影响 Web frontend types？
**不会**。后端 API 响应 shape 不变，前端类型推导不受影响。

### 是否会碰到 Graph/Sensemaking/Lab 代码？
**不会**。Import/Export 是纯主路径逻辑，与 Graph/Sensemaking 无任何交叉依赖。

### 是否真的改善主路径维护性？
**是**。Import/Export 是主路径的第一站和最后一站（Source/Import → ai_draft → ... → Export）。清晰的 schema 边界让这两个关键步骤更容易定位和修改。

---

## 7. 实施计划 (Slice A)

### 步骤

1. 创建 `src/mindforge_web/schemas/` 目录，带 `__init__.py`
2. 创建 `src/mindforge_web/schemas/import_export.py`，移入 import/export 相关 schema
3. 更新 `schemas/__init__.py`，re-export import_export 中的所有类
4. 从 `schemas.py` 中删除已移动的类，在顶部添加注释指向新位置
5. 更新 `schemas.py` 中的 import（从 import_export 子模块导入，保持 re-export）
6. 验证所有 import 路径仍有效
7. 运行 full test suite + npm build + ruff

### 验证标准

- `from mindforge_web.schemas import ImportCardResponse` 仍然有效
- `from mindforge_web.schemas import_export import ImportCardResponse` 新增有效
- 所有测试通过
- ruff check 通过
- npm build 通过
