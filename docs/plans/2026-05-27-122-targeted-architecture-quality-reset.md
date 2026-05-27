# Targeted Architecture Quality Reset — Plan

Date: 2026-05-27
Baseline HEAD: `1b39edb`
Task type: `architecture_refactor` (plan/spec phase)
Source: AUDIT-118-03 / CURRENT_PROJECT_STATE.md §6

---

## 0. Scope Boundary

**In scope（本轮允许）:**
- Architecture evidence audit（只读）
- Targeted reset plan（本文档）
- Slice 0: architecture boundary tests（验证当前 contract，不做实现变更）
- Slice 1+: small safe refactoring slices（仅 plan 批准后执行）

**Out of scope（本轮禁止）:**
- web_facade.py 大规模拆分
- schemas 重组织
- Graph/Sensemaking/Entity/Community 扩张
- 新增依赖
- 改 product behavior / API contract
- 改 approval 语义

---

## 1. Evidence Audit

### 1.1 File Size Distribution

```
9255 total lines in src/mindforge_web/

Top files:
  1487  web_facade.py         — God Facade: ~60 methods, module-level helpers
  1017  web_config_service.py — Config CRUD + validation + provider status
   760  processing_run_service.py — Processing pipeline, imported by core
   713  web_source_service.py — Source management
   399  schemas/__init__.py   — Barrel re-exports (was 1375, reduced 63.4%)
   376  web_import_export_service.py
   338  web_lab_service.py    — Lab/Graph/Sensemaking (extracted from facade)
   228  web_review_service.py
   177  web_recall_service.py
```

**Assessment:** web_facade.py at 1487 lines is still the largest file but already reduced 31.3% from 2163 lines (v4.8 extracted lab/import-export/recall). The remaining bulk is in module-level private helpers (_library_card_response, _graph_response, _provenance_trail_response, etc.) and the core facade methods. Not an emergency but the private helpers at module level create testing friction.

### 1.2 Core → Web Reverse Dependency (CRITICAL)

7 import sites where `src/mindforge/` (core) imports from `src/mindforge_web/` (web):

| # | Core Module | Imports From | Severity |
|---|------------|-------------|----------|
| 1 | `processing_worker.py:18` | `mindforge_web.services.processing_run_service._run_worker` | **P1** — imports private `_run_worker` |
| 2 | `cli_processing_runtime.py:20` | `mindforge_web.services.processing_run_service` (public + private `_save_record`) | **P1** — imports private `_save_record` |
| 3 | `runs_cli.py:10` | `mindforge_web.services.processing_run_service` (get_processing_run, list_processing_runs) | **P2** — CLI importing from web layer |
| 4 | `watch_cli.py:293` | `mindforge_web.services.processing_run_service.latest_run_for_source` | **P2** |
| 5 | `services/local_status.py:24` | `mindforge_web.services.processing_run_service.list_processing_runs` | **P2** — core service importing from web |
| 6 | `dogfood/scenario_runner.py:190` | `mindforge_web.services.dogfood_service.compute_dogfood_report` | **P2** |
| 7 | `web_cli.py:138` | `mindforge_web.server.run_server` | **P3** — CLI entry for web server, acceptable |

**Root cause:** `processing_run_service.py` lives in `mindforge_web/services/` but contains processing pipeline logic that belongs in core. The private function imports (`_run_worker`, `_save_record`) are the most severe violation — core modules reaching into web internals.

### 1.3 web_config_service.py Complexity

1017 lines. Handles:
- Config CRUD (read/write YAML)
- Validation (patch validation)
- Provider status (model_setup, env keys, cubox)
- Editable config generation
- Dotenv presence detection
- Watch source listing

**Assessment:** Mixed concerns but not urgent. Config persistence, validation, and provider status querying are three distinct responsibilities crammed into one class. Can be split later but not in Slice 0.

### 1.4 schemas/__init__.py Status

399 lines, down from 1375 (v4.8 Slice 1). 12 sub-modules extracted. Remaining content is:
- ProvenanceTrailResponse inline (was already here before extraction)
- Some inline schema classes (PathActionResponse, DiscoveryContextResponse, CommunityResponse, etc.)
- Re-exports from all 12 sub-modules

**Assessment:** Already well-organized. NOT a target for this reset. The inline schemas that remain are either small (PathActionResponse) or logically belong to specific features (ProvenanceTrail) that could be extracted later but not now.

---

## 2. Problem Analysis

### 2.1 What's Actually Broken

1. **Layer violation (P1):** Core imports from web — the dependency arrow points the wrong way. `processing_run_service` contains processing pipeline logic but lives in web layer, forcing core modules to import from web. This is the only P1 architecture debt.

2. **web_facade.py module-level helpers (P2):** `_library_card_response`, `_library_detail_response`, `_graph_response`, `_provenance_trail_response`, `_local_graph_response`, `_discovery_context_response`, etc. These are pure data transformation functions (~500 lines combined) that could move to dedicated presenter modules.

3. **web_config_service.py mixed concerns (P3):** Config CRUD, provider status, validation, editable config generation all in one class. Functional but hard to test in isolation.

### 2.2 What's NOT Broken (Don't Touch)

- schemas/__init__.py — already well-organized
- Router layer — clean, thin, delegates to facade
- Facade delegation to WebLabService, WebRecallService, WebImportExportService — already extracted
- Core service layer — well-structured
- Tests — passing, reliable

---

## 3. Target Design

### 3.1 Layer Dependency Direction (Fix P1)

**Current (broken):**
```
src/mindforge/ (core)
  ↓ imports from
src/mindforge_web/services/processing_run_service.py
```

**Target:**
```
src/mindforge_web/ (web)
  ↓ imports from
src/mindforge/ (core)
```

Processing run persistence and worker logic should live in core (`src/mindforge/processing/`), not in web. Web layer should only have thin wrappers that call core.

### 3.2 web_facade.py Private Helpers (Fix P2)

Module-level private helpers should move to `src/mindforge_web/presenters/`:
- `_library_card_response` → `presenters/library_presenter.py`
- `_graph_response` / `_graph_node_response` / `_graph_edge_response` → `presenters/graph_presenter.py`
- `_provenance_trail_response` → `presenters/provenance_presenter.py`
- `_local_graph_response` → `presenters/local_graph_presenter.py`
- `_discovery_context_response` → `presenters/discovery_presenter.py`

Each presenter module: pure function, input = domain object, output = Pydantic response schema. No IO, no config, no side effects.

### 3.3 web_config_service.py (Defer)

Config service refactoring is deferred to a separate plan. The current service works correctly; splitting it would be cleanup, not debt payment.

---

## 4. Implementation Slices

### Slice 0: Architecture Boundary Tests (SAFE — no behavior change)

**Goal:** Write contract tests that verify the current architecture boundaries, creating a safety net before any refactoring.

**Tests to write:**
1. **`tests/test_architecture_boundary_core_no_web_import.py`** — Assert that `src/mindforge/` (excluding `web_cli.py`) does not import from `mindforge_web`. This test will FAIL initially (documenting the current violation), then pass after Slice 1 fixes the layer violation.

2. **`tests/test_architecture_boundary_web_facade_contract.py`** — Assert that `WebFacade` public methods exist and return expected response types. Ensures refactoring doesn't accidentally remove or rename methods.

3. **`tests/test_architecture_boundary_processing_run_contract.py`** — Assert that processing run functions (`get_processing_run`, `list_processing_runs`, `latest_run_for_source`, `_run_worker`) exist and have consistent signatures, regardless of which module they live in.

**Files created:** 3 test files, 0 production code changes.

### Slice 1: Fix Core → Web Reverse Dependency (P1)

**Goal:** Move `processing_run_service.py` processing logic to core, eliminate reverse imports.

**Steps:**
1. Create `src/mindforge/processing/__init__.py` (if not exists)
2. Create `src/mindforge/processing/run_store.py` — extract persistence/query logic from `processing_run_service.py`
3. Update core modules to import from `src/mindforge/processing/` instead of `mindforge_web.services.processing_run_service`
4. Update `mindforge_web/services/processing_run_service.py` to be a thin re-export shim (backward compat)
5. Remove private function imports (`_run_worker`, `_save_record`) from core
6. Run boundary tests from Slice 0

**Risk:** Medium. Processing pipeline is a critical path. Must preserve exact behavior.
**Files changed:** ~6 files (3 new, 3 modified)
**Lines changed:** ~200 (mostly moved)

### Slice 2: Extract web_facade.py Private Helpers to Presenters (P2)

**Goal:** Move data transformation helpers from module-level in web_facade.py to dedicated presenter modules.

**Steps:**
1. Create `presenters/library_presenter.py` — `_library_card_response`, `_library_detail_response`
2. Create `presenters/graph_presenter.py` — `_graph_response`, `_graph_node_response`, `_graph_edge_response`
3. Create `presenters/local_graph_presenter.py` — `_local_graph_response`
4. Create `presenters/provenance_presenter.py` — `_provenance_trail_response`
5. Create `presenters/discovery_presenter.py` — `_discovery_context_response`
6. Update web_facade.py imports
7. Run full gate

**Risk:** Low. Pure data transformation functions, no IO, no side effects.
**Files changed:** ~7 files (5 new, 2 modified)
**Lines changed:** ~500 (moved, not changed)

### Slice 3+: Deferred

- web_config_service.py split → separate plan
- web_facade.py remaining methods split → separate plan (low priority, already functional)
- Frontend test infrastructure (P2-05) → separate plan
- Coverage configuration (P2-06) → separate plan

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Processing pipeline broken by Slice 1 | Medium | High | Boundary tests (Slice 0) + full gate + keep backward compat shim |
| API contract drift | Low | High | Contract tests verify public method signatures |
| Import cycle created | Low | Medium | Boundary test prevents new reverse imports |
| Slice 0 tests fail unexpectedly | Low | Low | Tests intentionally document current state; expected to find violations |

---

## 6. Gates

Each slice must pass:
- `git diff --check`
- `ruff check src/ tests/`
- `python -m pytest tests/ -q --tb=short` (full suite)
- `npm --prefix web run build` (if web layer touched)
- `python -m pytest tests/test_web_product_copy.py -q --tb=short`

---

## 7. Non-Goals

- 不做 RAG / embedding / vector DB
- 不新增依赖
- 不改 approval 语义
- 不改 API contract（除非是内部模块路径）
- 不扩张 Graph/Sensemaking
- 不做 web_facade.py 的大规模拆分（仅 presenter 提取）
- 不拆 web_config_service.py（deferred to separate plan）

---

## 8. Decision Log

- **Why not split web_facade.py methods now?** Already reduced 31.3% from 2163 lines. Remaining methods are thin delegations to extracted services. The real debt is in private helpers and layer violation.
- **Why Slice 0 first?** Architecture boundary tests are zero-risk, create a safety net, and document the current state. They can be written and committed immediately.
- **Why defer web_config_service.py?** 1017 lines but functionally correct. Splitting config CRUD from provider status is cleanup, not debt payment. Separate plan keeps scope tight.
