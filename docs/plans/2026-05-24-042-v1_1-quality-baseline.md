---
title: v1.1 Quality Baseline
type: quality-dashboard
status: active
date: 2026-05-24
parent: 2026-05-24-041-v1_1_to_v1_5-multi-stage-roadmap.md
---

# v1.1 Quality Baseline

## Current Status (2026-05-24)

| Gate | Exit Code | Status |
|------|-----------|--------|
| `npm --prefix web run build` | 0 | Clean |
| `python -m pytest tests/test_web_product_copy.py -q` | 0 | Clean (65 tests) |
| `python -m pytest tests/ -q` | 0 | Clean (371 passed, 1 skipped) |
| `ruff check src tests` | 0 | Clean |
| `git diff --check` | 0 | Clean |

## Pre-existing Issues — RESOLVED

| ID | File | Issue | Priority | Introduced | Fixed |
|----|------|-------|----------|-----------|-------|
| R-001 | `src/mindforge_web/services/web_config_service.py` | F821: `Literal` not imported from typing (6 occurrences) | P2 | v0.5 (May 23) | v1.1 U1 |
| R-002 | `tests/test_web_product_copy.py:345` | F841: unused variable `en` | P3 | May 23 | v1.1 U2 |
| R-003 | `pyproject.toml:56` | ruff `target-version = "py311"` mismatched with Python 3.12.2 (10 invalid-syntax errors) | P2 | pre-v0.5 | v1.1 U3 |
| R-004 | `tests/test_web_api.py:5304` | `test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy` failure — `?? source.path` fallback pattern | P3 | v0.5 (May 23) | v1.1 U4 |

## Test Coverage Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_web_product_copy.py` | 65 | All pass |
| `tests/test_web_api.py` | ~141 | All pass |
| `tests/relations/` | ~40 | All pass |
| Other tests | ~125 | All pass |
| **Total** | **~371** | **All pass (1 skipped)** |

## Known Limitations

- No frontend component tests (Vitest/Playwright not configured)
- No performance benchmarks
- Browser smoke requires manual execution
- `test_web_product_copy.py` uses static contract assertions, not real DOM rendering

## Next Quality Milestones

| Milestone | Target Version | Description |
|-----------|---------------|-------------|
| Frontend component tests | v1.2+ | Vitest setup for React components |
| Performance benchmarks | v1.3 | Graph build time, BM25 query latency, memory usage |
| Browser smoke automation | v1.4 | Playwright-based automated smoke tests |
| Coverage reporting | v1.4 | `pytest --cov` reports with 80%+ target |
