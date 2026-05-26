# v4.8 Global Architecture Quality Roadmap

**日期**: 2026-05-26
**基于**: 
- docs/audits/2026-05-26-099-global-architecture-quality-audit.md
- docs/design/2026-05-26-100-target-architecture-map.md
**状态**: active

---

## Slice 0 — Architecture Boundary Tests（优先执行）

**目标：** 在继续重构前，先建立架构边界验证网。

**新增文件：** `tests/test_architecture_boundaries.py`

**测试范围：**
1. Main path routers must not import lab/internal graph/sensemaking modules
2. Schema domain modules maintain correct import direction (no domain→domain except common)
3. web_facade.py imports are categorized (future refactor target)
4. Approval-related schemas remain importable from stable public path
5. No new RAG/embedding/vector imports anywhere

**行数估算：** ~80-120 lines

---

## Slice 1 — Complete Main Path Schema Modularization

**目标：** 完成 schemas/__init__.py 的 domain 模块化。

**每个子 slice 提取一个 domain schema 组：**

| Sub-slice | Domain | 类数 | 行数 | 主路径 |
|-----------|--------|------|------|--------|
| 1a | Provider/Config/Setup | ~20 | ~300 | 是 |
| 1b | Sources/Watch | ~6 | ~130 | 是 |
| 1c | Library/Card | ~8 | ~100 | 是 |
| 1d | Recall/Search | ~2 | ~40 | 是 |
| 1e | Graph | ~5 | ~60 | lab/internal |
| 1f | Sensemaking | ~7 | ~70 | lab |
| 1g | Trash | ~5 | ~50 | 是 |
| 1h | Quality/Health | ~4 | ~30 | 是 |

**执行顺序：** 先主路径 (1a→1d)，再 lab/internal (1e, 1f)，最后杂项 (1g, 1h)

**每个 sub-slice 要求：**
- backward-compatible re-exports
- ruff + pytest + npm build gates
- 不改变 API shape

---

## Slice 2 — web_facade.py Lab/Internal Isolation

**目标：** 将 graph/sensemaking/discovery/community/topic 方法从 web_facade 移至独立模块。

**涉及方法：** 7 methods (~200 lines total)
- `knowledge_communities()`
- `knowledge_topics()`
- `get_graph_node()`
- `get_graph_explore()`
- `get_graph_edge()`
- `get_sensemaking()`
- `get_discovery_context()`

**新增文件：** `src/mindforge_web/services/web_lab_service.py`

**原则：**
- 不删除任何功能
- 不改变 API contract
- 从 web_facade 中删除方法，委托给 web_lab_service
- 标记 lab 方法为 LAB/INTERNAL

---

## Slice 3 — WebImportExportService Extraction

**目标：** 从 web_facade 提取 import/export 逻辑。

**涉及方法：** 4 methods + 模块级 helpers (~400 lines total)
- `import_card()`
- `preview_folder_import()`
- `import_from_folder()`
- `_find_duplicates()`
- `_REJECTED_FILENAME_PATTERNS`
- `_MAX_IMPORT_FILE_BYTES`

**新增文件：** `src/mindforge_web/services/web_import_export_service.py`

**注意：** web_facade 保留 thin wrapper，router contract 不变。

---

## Slice 4 — WebRecallWikiService Extraction

**目标：** 从 web_facade 和 wiki.py router 提取 recall/wiki 逻辑。

**涉及：**
- web_facade.recall() (100 lines)
- wiki.py router 中的 wiki rebuild 逻辑

**新增文件：** `src/mindforge_web/services/web_recall_wiki_service.py`

---

## Slice 5 — Architecture Debt Ledger Closure

**目标：** 更新 quality-debt-ledger，诚实反映 v4.8 后的状态。

**更新范围：**
- P2-02 (web_facade.py God Service) → 更新现状
- P2-03 (schemas.py God Schema) → 更新现状
- 新增架构 boundary tests debt
- 新增前端测试 debt (仍 open)

---

## Self-Review

### 这是不是又变成机械拆文件？
**不是。** Slice 2-4 是按 domain responsibility 拆 service，不是按行数拆。每个 slice 解决一个具体的架构问题：
- Slice 2: lab 代码物理隔离
- Slice 3: import/export domain 独立
- Slice 4: recall/wiki domain 独立

### 是否真的改善了主路径？
**是。** Slice 3 和 Slice 4 直接改善主路径中最需要重构的两个步骤。

### 是否只是为了降低行数？
**不是。** 目标是将 web_facade 从 God Object 降级为 thin orchestration layer。行数降低是副作用，不是目标。

### 是否新增了更多小巨石？
**不会。** 每个新 service 只有一个 domain responsibility。不创建通用/utility/helper module。

### 是否引入更多抽象而不是减少复杂度？
**不会。** Slice 0-5 不新增任何 Port/ABC/Repository。新 service 是 plain class with methods。

### 是否碰到了 Graph/Sensemaking/Lab？
**Slice 2 会触碰。** 但只是移动方法位置，不改功能。不改 Graph/Sensemaking 业务逻辑。

### 是否破坏 API contract？
**不会。** Router → web_facade → new service 的内部委托对 router 透明。API response shape 不变。

### 是否需要先补测试再动代码？
**Slice 0 正是这个目的。** 先建架构边界测试，再动代码。

---

## 执行顺序

1. **Slice 0** — Architecture Boundary Tests（本轮即可开始）
2. **Slice 1** — Complete Schema Modularization（如果 context 充足，完成主路径 sub-slices）
3. **Slice 2** — Lab/Internal Isolation（中等风险，需 boundary tests 保护）
4. **Slice 3** — ImportExportService（中等风险，router contract 不变）
5. **Slice 4** — RecallWikiService（中等风险）
6. **Slice 5** — Ledger Closure
