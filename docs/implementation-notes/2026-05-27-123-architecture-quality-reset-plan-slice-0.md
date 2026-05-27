# Architecture Quality Reset — Plan + Slice 0 Implementation Notes

Date: 2026-05-27
Task type: `architecture_refactor` (plan/spec + boundary tests)
Source: AUDIT-118-03 / CURRENT_PROJECT_STATE.md §6

---

## 1. What Was Done

### Plan

Written `docs/plans/2026-05-27-122-targeted-architecture-quality-reset.md`:

- **Evidence Audit:** File size distribution (9255 lines in src/mindforge_web/), 7 core→web reverse dependency sites identified
- **Problem Analysis:** Layer violation (P1 — core imports from web), web_facade module-level helpers (P2), config_service mixed concerns (P3)
- **Target Design:** Processing logic → core, private helpers → presenters
- **3 Implementation Slices:** Slice 0 (boundary tests), Slice 1 (fix reverse deps), Slice 2 (extract presenters), Slice 3+ (deferred)
- **Risk Assessment + Gates + Non-Goals**

### Slice 0: Architecture Boundary Tests

Extended `tests/test_architecture_boundaries.py` with 3 new test classes (6 new tests):

1. **TestArchitectureCoreWebLayerBoundary** — AST-based scan preventing new core→web reverse dependencies
   - `test_core_web_imports_are_known_only`: All `mindforge_web` imports in `src/mindforge/` must be in known-violations dict. 7 known sites documented.
   - `test_no_core_imports_web_private_symbols`: Private symbol (`_` prefix) imports from web layer are the most severe violation. 2 known sites (`_run_worker`, `_save_record`) tolerated; new ones blocked.

2. **TestArchitectureWebFacadeContract** — Runtime contract tests for WebFacade public API
   - `test_web_facade_public_methods_exist`: ~40 required methods verified via `WebFacade.__dict__`
   - `test_web_facade_core_methods_have_consistent_return_types`: 10 core methods verified to have return type annotations via `inspect.signature`

3. **TestArchitectureProcessingRunContract** — Processing run function contract for Slice 1 safety
   - `test_processing_run_functions_exist`: 5 key functions/types verified in `processing_run_service`
   - `test_processing_run_record_fields`: 5 critical fields on `ProcessingRunRecord` dataclass verified

**Design pattern:** Followed existing known-violations pattern from `test_main_path_services_lab_imports_are_known` — tests document current state and only fail on NEW violations.

---

## 2. Files Changed

| File | Action | Lines |
|------|--------|-------|
| `docs/plans/2026-05-27-122-targeted-architecture-quality-reset.md` | Created | 241 |
| `tests/test_architecture_boundaries.py` | Modified | +282 (6 new tests in 3 classes) |

---

## 3. Why This Is Safe

- Slice 0 is **zero production code change** — only tests and a plan document
- All 6 new tests are read-only (AST parsing + runtime introspection)
- No behavior change, no API contract change, no schema change
- No RAG/embedding/vector DB introduced
- No real LLM/Cubox/Upstage/private data/Obsidian write touched
- No approval semantics changed

---

## 4. Gates

| Gate | Command | Exit Code | Result |
|------|---------|-----------|--------|
| git diff --check | `git diff --check` | 0 | pass |
| ruff | `ruff check src/ tests/ docs/` | 0 | All checks passed |
| architecture boundary tests | `python -m pytest tests/test_architecture_boundaries.py -q --tb=short` | 0 | 14 passed |
| product copy tests | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | 9 passed |
| web build | `npm --prefix web run build` | 0 | pass |

No timeout, no truncated output, no pre-existing failures hidden.

---

## 5. Deferred

- **Slice 1** (Fix Core → Web Reverse Dependency): Plan-authorized, requires plan approval before execution. Moves `processing_run_service.py` processing logic to `src/mindforge/processing/`.
- **Slice 2** (Extract web_facade.py Private Helpers to Presenters): Low risk, plan-authorized.
- **Slice 3+** (web_config_service.py split, frontend tests, coverage): Separate plans.

---

## 6. Commit

- **Commit:** `8eb3fd4`
- **Message:** `test: add Slice 0 architecture boundary tests for targeted quality reset`
- **Push:** success, main → origin/main, 0 0 aligned
