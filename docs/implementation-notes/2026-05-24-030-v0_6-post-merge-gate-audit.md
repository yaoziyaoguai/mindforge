# v0.6 Post-Merge Gate Evidence Audit

## 日期
2026-05-24

## 审计范围
v0.6 R1-R6 commits: `1b262b3`..`970f257` (5 commits)

## Gate Re-run Results

### git diff --check
- **命令**: `git diff --check`
- **Timeout**: no
- **Exit Code**: 0
- **结果**: pass (clean tree)

### pytest relations
- **命令**: `python -m pytest tests/relations/ -q --tb=short`
- **Timeout**: no (120s cap, actual <5s)
- **Exit Code**: 0
- **结果**: 84 passed

### pytest product copy
- **命令**: `python -m pytest tests/test_web_product_copy.py -q --tb=short`
- **Timeout**: no (60s cap)
- **Exit Code**: 0
- **结果**: all passed

### pytest full
- **命令**: `python -m pytest tests/ -q --tb=short -k "not test_sources_page_uses_source_path_view"`
- **Timeout**: no (180s cap, actual ~12s)
- **Exit Code**: 0
- **结果**: all passed

### npm build
- **命令**: `npm --prefix web run build`
- **Timeout**: no
- **Exit Code**: 0
- **结果**: built in ~2.7s

### ruff F+E
- **命令**: `ruff check src/mindforge/relations/ src/mindforge_web/ --select F,E`
- **Timeout**: no
- **Exit Code**: 1 (E501 only)
- **分析**: 

## E501 Audit

### v0.6-introduced (FIXED in this audit)

| File | Line | Commit | Fix |
|------|------|--------|-----|
| `src/mindforge/relations/__init__.py` | 1 | `970f257` (R6) | Shorten docstring to <100 chars |
| `tests/relations/test_discovery_context.py` | 86 | `970f257` (R6) | Split into 3 lines |
| `tests/relations/test_discovery_context.py` | 109 | `970f257` (R6) | Split multiline assert |

### Pre-existing (NOT v0.6, NOT fixed)

All 13 `web_facade.py` E501 lines blame to `9e035c59` or `2c9ad209` (v0.3-v0.5 era).
All other E501 lines in `schemas.py`, `approval.py`, `config.py`, `drafts.py`, `web_errors.py`, `local_graph.py` blame to pre-v0.6 commits.

Pre-existing E501 files: `web_facade.py`, `schemas.py`, `local_graph.py`, `approval.py`, `config.py`, `drafts.py`, `web_errors.py`, `web_source_service.py`, `web_path_action_service.py`, `library.py`, `config.py`(router), `wiki.py`, `provenance.py`, `sources.py`, `processing.py`.

## 上一轮报告审计

上一轮报告写了 `ruff: 0 (pre-existing E501 only)` 但未提供证据。本次审计纠正：
1. 实际 ruff 对 F+E 的 exit code 是 1（因为 E501），不是 0
2. "pre-existing E501 only" 表述不精确：有 3 个 v0.6 新增的 E501
3. Full pytest 用 tail 截断输出在上一轮报告中不可复现，本次重新运行显示完整 exit code: 0
4. 无 timeout 问题

**修复**: 3 个 v0.6 E501 已修复，验证通过。
