# Architecture Quality Reset — Slice 1 Implementation Notes

Date: 2026-05-27
Task type: `architecture_refactor` (implementation)
Source: `docs/plans/2026-05-27-122-targeted-architecture-quality-reset.md` §4 Slice 1

---

## 1. What Was Done

### Slice 1: Fix Core → Web Reverse Dependency (P1)

Moved processing run persistence, query, and worker logic from `mindforge_web/services/processing_run_service.py` (web layer) to `mindforge.processing.run_store` (core layer).

**New files:**
- `src/mindforge/processing/__init__.py` — package docstring
- `src/mindforge/processing/run_store.py` — 508 lines, contains:
  - `ProcessingRunRecord` dataclass + `RunStatus` type + constants
  - Persistence layer: `_runs_dir`, `_run_path`, `_save_record`, `_load_record`
  - Query API: `get_processing_run`, `list_processing_runs`, `latest_run_for_source`
  - Worker: `_run_worker`, `_apply_summary`, `_heartbeat`, `_heartbeat_loop`, `_save_final_record_if_active`
  - Run lifecycle: `start_processing_run`, `start_sync_processing_run`
  - Error utilities: `_safe_error_message`, `_looks_like_secret`
  - Message helpers: `_running_message`, `_message_for_summary`, `_failed_current_step`, `_skip_reasons`, `_first_skip_reason`
  - Internal helpers: `_draft_ids`, `_empty_summary`, `_new_run_id`, `_now`, `_parse_datetime`, `_normalize_abandoned_run`, `started_response_message`

**Modified file (web shim):**
- `src/mindforge_web/services/processing_run_service.py` — reduced to ~160 lines. Now re-exports all core symbols from `mindforge.processing.run_store` and keeps only 3 web-schema-dependent functions:
  - `processing_run_response` (depends on `mindforge_web.schemas.ProcessingRunResponse`)
  - `next_actions_for_record` (depends on `mindforge_web.schemas.NextAction`)
  - `_safe_public_source_ref` (web-specific path redaction)

**Core modules updated (5 files):**
| File | Old Import | New Import |
|------|-----------|-----------|
| `processing_worker.py:18` | `mindforge_web...import _run_worker` | `mindforge.processing.run_store import _run_worker` |
| `cli_processing_runtime.py:20-26` | `mindforge_web...import {5 symbols}` + `_save_record` | `mindforge.processing.run_store import {5 symbols}` |
| `runs_cli.py:10` | `mindforge_web...import {2 symbols}` | `mindforge.processing.run_store import {2 symbols}` |
| `watch_cli.py:293` | `mindforge_web...import latest_run_for_source` | `mindforge.processing.run_store import latest_run_for_source` |
| `services/local_status.py:24` | `mindforge_web...import list_processing_runs` | `mindforge.processing.run_store import list_processing_runs` |

**Boundary tests updated:**
- `_CORE_WEB_KNOWN_VIOLATIONS`: removed 5 processing_run_service entries (kept only dogfood_service + web_cli)
- `_CORE_WEB_KNOWN_PRIVATE_IMPORTS`: emptied entirely — both `_run_worker` and `_save_record` private imports eliminated
- Updated docstrings to reflect Slice 1 completion

---

## 2. Architecture Impact

**Before (broken):**
```
src/mindforge/ (core)
  ↓ imports from
src/mindforge_web/services/processing_run_service.py  ← P1 violation
```

**After (correct):**
```
src/mindforge_web/ (web)
  ↓ imports from
src/mindforge/processing/run_store.py  (core)
```

The layer dependency direction is now correct. Processing run logic is a core concept, not a web concept.

---

## 3. Why This Is Safe

- **Identical code:** Logic moved verbatim, no behavioral changes. All function bodies are byte-for-byte the same.
- **Backward compatible:** Web routers still import from `processing_run_service.py` which re-exports everything from core. No API contract change.
- **No schema change:** `ProcessingRunRecord` fields unchanged. Run JSON format unchanged.
- **No approval semantics changed.**
- **No RAG/embedding/vector DB introduced.**
- **No real LLM/Cubox/Upstage/private data/Obsidian write touched.**
- **Protection:** Slice 0 boundary tests guard against regression. Any new core→web import will be caught.

---

## 4. Gates

| Gate | Command | Exit Code | Result |
|------|---------|-----------|--------|
| ruff | `ruff check src/ tests/` | 0 | All checks passed |
| architecture boundary tests | `pytest tests/test_architecture_boundaries.py -q --tb=short` | 0 | 14 passed |
| full test suite | `pytest tests/ -q --tb=short` | 0 | 100% pass |
| product copy tests | `pytest tests/test_web_product_copy.py -q --tb=short` | 0 | 9 passed |
| web build | `npm --prefix web run build` | 0 | pass (pre-existing chunk warning) |
| git diff --check | `git diff --check` | 0 | pass |

No timeout, no truncated output, no hidden failures.

---

## 5. Remaining Known Violations (P2/P3)

After Slice 1, two core→web imports remain in the known-violations dict:

| # | Core Module | Imports From | Severity | Status |
|---|------------|-------------|----------|--------|
| 6 | `dogfood/scenario_runner.py:190` | `mindforge_web.services.dogfood_service` | P2 | deferred |
| 7 | `web_cli.py:138` | `mindforge_web.server` | P3 | acceptable (web server CLI entry) |

These are not P1 — no private symbols, no processing pipeline coupling.

---

## 6. Commit

- **Commit:** `2cba857`
- **Message:** `refactor: Slice 1 — move processing run logic to core, fix core→web layer violation`
- **Push:** success, main → origin/main, 0 0 aligned
