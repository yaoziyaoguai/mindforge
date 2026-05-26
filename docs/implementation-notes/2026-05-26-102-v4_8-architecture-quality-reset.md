# v4.8 Architecture Quality Reset — Implementation Notes

**日期**: 2026-05-26
**基于**: docs/plans/2026-05-26-101-v4_8-global-architecture-quality-roadmap.md
**状态**: completed — Slice 0-5 全部完成

---

## Slice 0 — Architecture Boundary Tests ✅

**文件**: `tests/test_architecture_boundaries.py` (267 lines)

**8 tests 覆盖 4 个边界维度：**

1. **Main path routers must not import lab modules**
   - `test_main_path_routers_do_not_import_lab_graph`
   - 只允许 `graph.py` 和 `discovery.py` route 导入 lab 模块

2. **Web services lab imports must be known violations**
   - `test_main_path_services_lab_imports_are_known`
   - `known_lab_imports` dict 跟踪 web_facade.py + dogfood_service.py 的已知违规
   - 新增 lab import 会触发 test failure

3. **Schema import direction**
   - `test_schema_submodules_no_service_imports` — schema 子模块不 import services/routers
   - `test_all_schema_submodule_classes_re_exported` — 所有 public 类在 __init__.py 中 re-export

4. **No RAG/embedding/vector DB**
   - `test_no_rag_embedding_imports` — 扫描全部 src/ 代码树

5. **Approval safety semantics**
   - `test_approval_schemas_importable` — approval schema 保持可导入
   - `test_human_approved_value_unchanged` — `_TARGET_STATUS == "human_approved"`
   - `test_approval_requires_explicit_confirm` — ApproveRequest.confirm 是 `bool`，不能默认 True

**Gate**: ruff 0, pytest 8/8, npm build 0

---

## Slice 1 — Schema Modularization ✅

**目标**: schemas/__init__.py 从 1091 行 → target ~100 行 (re-exports only)

| Sub-slice | Domain | 类数 | 新文件 | 行数 |
|-----------|--------|------|--------|------|
| 1a | Provider/Config/Setup | 27 | `provider.py` | 310 |
| 1b | Sources/Watch | 9 | `source.py` | 146 |
| 1c | Library/Card | 9 | `library.py` | 114 |
| 1d | Recall/Search | 2 | `recall.py` | 38 |
| 1e | Graph (lab/internal) | 5 | `graph.py` | 65 |
| 1f | Sensemaking (lab) | 9 | `sensemaking.py` | 110 |
| 1g | Trash | 5 | `trash.py` | 56 |
| 1h | Quality/Health | 6 | `quality.py` | 66 |

**已存在子模块** (v4.7 Slice A-D):

| 模块 | 类数 | 行数 |
|------|------|------|
| `common.py` | 4 types | 78 |
| `import_export.py` | 14 classes | 120 |
| `dogfood_lifecycle.py` | 4 classes | 89 |
| `review.py` | 6 classes | 85 |

**总计**: 12 个子模块, ~96 schema classes extracted, __init__.py 399 行 (-63.4%)

**剩余类** (~20 classes, 仍留在 __init__.py):
- ApiError
- CardBodyUpdateRequest/Response
- WorkflowSummaryResponse
- UnavailableResponse
- PathActionRequest/RevealRequest/PathActionResponse
- ProvenanceTrail* (5 classes)
- Discovery* (7 classes)
- SourceLocationResponse
- SubCommunityRefResponse, CommunityOverlapResponse
- KnowledgeCommunity* / KnowledgeTopic* (6 classes)

这些类属于较小的跨领域或 lab/internal 类型，可以在后续 slices 中提取。

**向后兼容**: 所有 `from mindforge_web.schemas import X` 路径不变，通过 __init__.py re-export 保证。

**已知跨 domain 依赖**: `recall.py` → `provider.py` (RecallResponse 引用 RecallStatus)。这是合法依赖 — recall 结果需要表达索引可用性。

---

## Gate 结果 (Slice 0 + 1)

| Gate | Command | Exit Code |
|------|---------|-----------|
| ruff | `ruff check src/ tests/ docs/` | 0 |
| pytest | `python -m pytest tests/ -q --tb=short` | 0 (1 skip, pre-existing) |
| npm build | `npm --prefix web run build` | 0 |
| boundary tests | `python -m pytest tests/test_architecture_boundaries.py -q` | 0 (8/8) |

---

## 下一步 (v4.8 已完成)

按 roadmap:
- **Slice 2**: ✅ web_facade.py Lab/Internal Isolation — 将 7 个 graph/sensemaking/discovery 方法移至 web_lab_service.py
- **Slice 3**: ✅ WebImportExportService Extraction — 从 web_facade 提取 import/export 逻辑
- **Slice 4**: ✅ WebRecallWikiService Extraction — 从 web_facade 提取 recall 逻辑
- **Slice 5**: ✅ Architecture Debt Ledger Closure — 更新所有 debt 条目

---

## Slice 2 — Lab/Internal Isolation ✅

**文件**: `src/mindforge_web/services/web_lab_service.py` (338 lines, new)

**web_lab_service.py**: 7 个 lab/internal 方法 → WebLabService:
- `knowledge_communities()` → KnowledgeCommunitiesResponse
- `knowledge_topics()` → KnowledgeTopicsResponse
- `get_graph_node(ref, depth)` → GraphResponse
- `get_graph_explore(node_type, node_id, depth)` → GraphResponse
- `get_graph_edge(source, target)` → GraphEdgeDetailResponse
- `get_sensemaking(ref)` → SensemakingResponse
- `get_discovery_context(ref)` → DiscoveryContextResponse

**web_facade.py**: 7 个方法体改为 thin delegation → WebLabService
**修正**: 发现 `GraphNodeType` → `NodeType` 引用错误（graph_models 中实际类名 NodeType），已修正
**架构测试**: 更新 known_lab_imports，web_lab_service.py 和 web_facade.py 分别跟踪
**清理**: 从 web_facade 移除 2 个不再使用的 unused import（assemble_discovery_context, GraphNodeType）

**Gate**: ruff 0, pytest 0 (1 skip), npm build 0

**Commit**: `bb34389`

---

## Slice 3 — WebImportExportService Extraction ✅

**文件**: `src/mindforge_web/services/web_import_export_service.py` (376 lines, new)

**提取的方法**:
- `import_card(title, body, source_name)` → ImportCardResponse
- `preview_folder_import(folder_path)` → FolderImportPreviewResponse
- `import_from_folder(folder_path, indices)` → FolderImportResponse
- `_parse_markdown_title_body(raw, filename)` → (title, body) — static
- `_find_duplicates(title)` → list of potential duplicates

**类常量**: _REJECTED_FILENAME_PATTERNS, _MAX_IMPORT_FILE_BYTES

**测试更新**: `tests/test_import_validation.py` — 所有引用从 WebFacade 更新为 WebImportExportService，_find_duplicates 使用 mock cfg + mock iter_cards

**Gate**: ruff 0, pytest 0 (1 skip), npm build 0

**Commit**: `57c7af6`

---

## Slice 4 — WebRecallService Extraction ✅

**文件**: `src/mindforge_web/services/web_recall_service.py` (177 lines, new)

**提取的方法**:
- `recall(query, context)` → RecallResponse — BM25 lexical recall
- `recall_status(approved_count)` → RecallStatus — 索引状态

**清理**: 从 web_facade 移除未使用的 import（default_index_path, RecallQuery, RecallServiceError, run_bm25_recall, RecallHit）

**Gate**: ruff 0, pytest 0 (1 skip), npm build 0

**Commit**: `ce9b3b9`

---

## Slice 5 — Architecture Debt Ledger Closure ✅

**更新**:
- `docs/dev/quality-debt-ledger.md`: P2-02 (web_facade.py God Service) 标记 resolved (v4.8)
- `docs/dev/architecture.md`: 更新 service 层描述和导入导出章节
- 本文件: 状态更新为 completed

**web_facade.py 瘦身结果**:
| 阶段 | 行数 | 变动 |
|------|------|------|
| v4.8 前 | 2163 | — |
| Slice 0-1 (schema extraction) | ~2033 | schemas 移出 |
| Slice 2 (lab isolation) | ~1770 | WebLabService |
| Slice 3 (import extraction) | ~1530 | WebImportExportService |
| Slice 4 (recall extraction) | 1487 | WebRecallService |
| **总计** | **1487** | **-31.3%** |

**提取的 services**:
| Service | 行数 | 职责 |
|---------|------|------|
| WebLabService | 338 | graph/sensemaking/discovery/community/topic (lab) |
| WebImportExportService | 376 | 卡片导入、文件夹导入、去重 |
| WebRecallService | 177 | BM25 recall + 索引状态 |

---

## 全部 Gates (Slice 0-5 最终)

| Gate | Command | Exit Code |
|------|---------|-----------|
| ruff | `ruff check src/ tests/ docs/` | 0 |
| pytest | `python -m pytest tests/ -q --tb=short` | 0 (1 skip) |
| npm build | `npm --prefix web run build` | 0 |
| boundary tests | `python -m pytest tests/test_architecture_boundaries.py -q` | 0 (8/8) |

**硬红线**:
- 不改 Graph/Sensemaking 业务逻辑
- 不改 API contract
- 不新增 Port/ABC
- 不做 RAG/embedding/vector DB
- 不调用真实 LLM
