# Architecture Quality Reset — Slice 2 Implementation Notes

Date: 2026-05-27
Plan: `docs/plans/2026-05-27-122-targeted-architecture-quality-reset.md`
Baseline: Slice 1 completion (`2cba857`)
Task type: `architecture_refactor` (Slice 2: presenter extraction)

---

## 1. Summary

将 `web_facade.py` 中 ~540 行模块级私有 helper 函数提取到 `presenters/` 子模块中。这些函数是纯数据变换（domain objects → Pydantic response schemas），无 IO，无副作用，提取风险极低。

## 2. What Changed

### 2.1 web_facade.py 瘦身

| 指标 | Before (v4.8) | After Slice 2 |
|------|--------------|---------------|
| 行数 | 1487 | **922** (-38.0%) |
| 私有 helper | ~540 lines | 0 (全部提取) |
| 导入行 | ~30 个（含大量仅 helper 使用的类型） | ~20 个 (精简) |

从最初 2163 行到 922 行，累计减少 **57.4%**。

### 2.2 新建 presenter 模块（5 个文件，640 行）

| 文件 | 函数数 | 行数 | 依赖 |
|------|--------|------|------|
| `presenters/shared.py` | 2 | 39 | 无（零依赖） |
| `presenters/graph_presenter.py` | 7 | 132 | `shared` |
| `presenters/library_presenter.py` | 6 + 1 class | 222 | `graph_presenter`, `shared` |
| `presenters/discovery_presenter.py` | 3 | 162 | 无（domain-only） |
| `presenters/provenance_presenter.py` | 1 | 85 | `discovery_presenter` |

### 2.3 现有文件修改

| 文件 | 修改内容 |
|------|---------|
| `presenters/__init__.py` | 重写 — 从 7 个模块 re-export 全部 20+ 公开函数 |
| `presenters/web_errors.py` | 新增 `http_error()` 公开函数（was `_http_error` in facade） |
| `services/web_facade.py` | 删除全部私有 helper · 导入切换至 presenters · 方法内调用改为 `build_xxx`/`http_error` |
| `services/web_lab_service.py` | 6 处 import block 更新：`web_facade` → `presenters`，`_xxx` → `build_xxx` |
| `services/web_recall_service.py` | 2 处导入更新：`_build_graph_builder` → `build_graph_builder` 等 |
| `tests/relations/test_provenance_related_sources.py` | 导入路径更新 |
| `tests/test_path_boundaries.py` | 断言字符串更新：`_http_error(` → `http_error(` |

### 2.4 命名规范变更

私有 `_xxx` → 公开 `build_xxx` / `get_xxx`（presenter 公开 API）：

- `_library_card_response` → `build_library_card_response`
- `_library_stats_response` → `build_library_stats_response`
- `_graph_response` → `build_graph_response`
- `_graph_node_response` → `build_graph_node_response`
- `_graph_edge_response` → `build_graph_edge_response`
- `_local_graph_response` → `build_local_graph_response`
- `_provenance_trail_response` → `build_provenance_trail_response`
- `_discovery_context_response` → `build_discovery_context_response`
- `_build_graph_builder` → `build_graph_builder`
- `_resolve_card_id` → `resolve_card_id`
- `_graph_neighbor_count` → `get_graph_neighbor_count`
- `_center_card_communities` → `get_center_card_communities`
- `_relation_reason_label` → `get_relation_reason_label`
- `_compute_related_sources` → `compute_related_sources`
- `_http_error` → `http_error`

## 3. Design Decisions

### 3.1 循环导入避免 — `shared.py`

原 `_library_detail_response` 调用 `_local_graph_response`，而 `_local_graph_response` 调用 `_relation_reason_label`。如果 graph 和 library 拆为独立模块，会产生 library→graph→library 循环。

解决：将 `make_relation_record` 和 `get_relation_reason_label` 提取到 `shared.py`（零依赖底层模块），graph 和 library 都从 shared 导入，打破循环。

最终依赖链：`shared` (zero deps) ← `graph_presenter` ← `library_presenter`；`discovery_presenter` (zero deps) ← `provenance_presenter`

### 3.2 `http_error` vs `user_error`

`http_error` 使用 `detail={"message": msg}` 格式（HTTPException 直接构造），而 `user_error` 使用 `detail={"error": label, "message": msg}`（带 ErrorLabel）。两个函数签名不同，不合并。

### 3.3 `__init__.py` re-export 策略

`presenters/__init__.py` 作为 barrel re-export 所有公开函数，保持 `from mindforge_web.presenters import build_xxx` 作为统一的导入入口。这是 facade 和 service 层的推荐导入方式。

## 4. Architecture Compliance

- **无层违规** — presenters 只依赖 domain models（`mindforge.relations.*`, `mindforge.cards.*`），不从 web services 导入
- **无循环导入** — 已验证所有模块可独立导入
- **无 IO / 副作用** — 所有 presenter 函数为纯数据变换
- **behavior unchanged** — 所有 API 返回格式保持完全一致

## 5. Gates (All Pass)

| Gate | Command | Exit | Notes |
|------|---------|------|-------|
| ruff (Python) | `ruff check src/ tests/` | 0 | All checks passed |
| git diff | `git diff --check` | 0 | — |
| full pytest | `python -m pytest tests/ -q --tb=short` | 0 | 545 passed, 1 skipped |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | ~73 passed |
| npm build | `npm --prefix web run build` | 0 | pre-existing chunk size warning |

## 6. Remaining Architecture Debt

- **Slice 3+ deferred**: `web_config_service.py` split (1017 lines, mixed concerns — needs separate plan)
- **Frontend test infrastructure** (P2-05) — separate plan, target v3.7
- **Coverage configuration** (P2-06) — separate plan, target v3.7

Architecture Quality Reset workstream is now complete for the scope defined in the plan. Remaining debt is documented in `quality-debt-ledger.md`.

## 7. Decision Log

- **Why not split more web_facade.py methods?** Remaining ~922 lines are thin delegations to extracted services (WebLabService, WebRecallService, WebImportExportService). Further splitting is low-value cleanup, not debt payment.
- **Why keep `__init__.py` as barrel?** Present mf-autopilot governance requires backward compat. Barrel keeps existing imports working while allowing gradual migration to direct module imports.
- **Why defer Slice 3?** `web_config_service.py` refactoring is functionally correct today; splitting mixed concerns needs a dedicated plan with boundary tests.
