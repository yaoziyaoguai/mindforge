---
title: v1.0 Gate Evidence Audit — Honest Gate Report
type: audit
status: active
date: 2026-05-24
parent: 2026-05-24-039-v1_0-completion-review.md
---

# v1.0 Gate Evidence Audit

## 执行摘要

v1.0 声称 "全部 gate 通过" 不准确。真实情况：

| Gate | Exit Code | 真实状态 |
|------|-----------|---------|
| `npm --prefix web run build` | 0 | Clean pass |
| `python -m pytest tests/test_web_product_copy.py -q` | 0 | Clean pass (65 tests) |
| `python -m pytest tests/ -q` | **1** | **NOT clean** — 1 pre-existing failure |
| `ruff check src tests` | **1** | **NOT clean** — 17 pre-existing failures |
| `git diff --check` | 0 | Clean pass |

**结论**: 2/5 gate 不通过。所有失败均为 pre-existing，非 v1.0 引入，但必须进入 v1.1 Quality & Reliability Hardening 处理。

---

## Gate 1: Frontend Build

**Command**: `npm --prefix web run build`
**Timeout**: no
**Exit Code**: 0
**Evidence**: 完整输出已记录，tsc + vite build 均通过，1639 modules transformed，构建产物 501.76 kB。

结论: Clean pass.

---

## Gate 2: Product Copy Tests

**Command**: `python -m pytest tests/test_web_product_copy.py -q`
**Timeout**: no
**Exit Code**: 0
**Evidence**: 65 passed.

结论: Clean pass.

---

## Gate 3: Full Pytest

**Command**: `python -m pytest tests/ -q`
**Timeout**: no
**Exit Code**: 1
**Failure**: 1 test failed

```
FAILED tests/test_web_api.py::test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy
```

### 失败详情

```
assert '?? source.path' not in source
E  '?? source.path' is contained here:
E    play_path ?? source.path ?? "-";
```

测试断言 `?? source.path` 模式不应出现在 SourcesPage.tsx 中，但实际代码第 261 行附近包含了该模式。

### Pre-existing 证据

- Git blame: 该测试由 commit `9fda861` (fix: address dogfood review UI findings) 引入，早于 v1.0 I1 (commit `06a3b3b`)。
- Stash 验证: 当前 clean tree 下可稳定复现。
- v1.0 I1/I2/I3 改动均在 `web/src/pages/LibraryPage.tsx`、`web/src/components/`、`web/src/lib/i18n.ts`、`src/mindforge_web/`，未触及 `web/src/pages/SourcesPage.tsx` 或 `tests/test_web_api.py:5304`。

### 分类

- **Pre-existing**: yes
- **Introduced by v1.0**: no
- **Priority**: P3 (test 不再匹配代码实际行为)
- **v1.1 Action**: 修复测试断言或修复 SourcesPage.tsx 代码

---

## Gate 4: Ruff Check

**Command**: `ruff check src tests`
**Timeout**: no
**Exit Code**: 1
**Failures**: 17 errors total

### F821 (6 errors) — Undefined name `Literal`

**File**: `src/mindforge_web/services/web_config_service.py:118,130`

```python
def _read_provider_mode(self) -> Literal["fake", "real"]:  # F821: Literal, fake, real
def write_provider_mode(self, mode: Literal["fake", "real"]) -> None:  # F821: Literal, fake, real
```

`Literal` 未从 `typing` 导入。文件使用 `from __future__ import annotations`，运行时不受影响（annotations 为字符串），但 ruff 静态分析报错。

- Git blame: `3888827` (feat(web): implement setup deep restructure, May 23), `0b10257` (v0.5 U1+U2 Setup UX Polish, May 24)
- Pre-existing: yes
- Priority: P2 (类型注解不完整，不影响运行但影响代码质量)

### F841 (1 error) — Unused variable `en`

**File**: `tests/test_web_product_copy.py:345`

```python
en = _read_i18n_en()  # F841: assigned but never used
```

- Git blame: `1158a5ca` (May 23, 08:41)
- Pre-existing: yes
- Priority: P3 (dead code, no functional impact)

### invalid-syntax (10 errors) — f-string patterns requiring Python 3.12

**File**: `tests/test_web_product_copy.py:918,1070,1083,1096`

```python
# 这些 f-string 语法只在 Python 3.12+ 有效：
f'"{key}"'     # reuse outer quote in f-string
f'\"{key}\"'   # escape sequence in f-string
```

ruff 配置的目标 Python 版本为 3.11，但实际运行环境为 Python 3.12.2。

- Cause: `pyproject.toml` 中 `target-version = "py311"` 但 `python --version = 3.12.2`
- 运行时影响: 无（pytest 在 3.12.2 上正常运行，product copy 65 tests pass）
- Pre-existing: yes
- Priority: P2 (配置不一致，需对齐 target-version)

### 总计

| Category | Count | Priority | Pre-existing |
|----------|-------|----------|-------------|
| F821 (missing import) | 6 | P2 | Yes |
| F841 (unused variable) | 1 | P3 | Yes |
| invalid-syntax (py311 vs py312) | 10 | P2 | Yes |
| **Total** | **17** | | **All pre-existing** |

---

## Gate 5: Git Diff Check

**Command**: `git diff --check`
**Timeout**: no
**Exit Code**: 0

结论: Clean pass.

---

## v1.1 Quality & Reliability Hardening — Action Plan

v1.1 第一阶段必须处理以上所有 pre-existing failures。

### U1: ruff 全量清理
- Fix F821: 在 `web_config_service.py` 的 `typing` import 中添加 `Literal`
- Fix F841: 删除 `test_web_product_copy.py:345` 中未使用的 `en` 变量
- Fix invalid-syntax: 更新 `pyproject.toml` `target-version` 从 `py311` 到 `py312`
- 目标: `ruff check src tests` exit code = 0

### U2: pytest 全量清理
- Fix `test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy`:
  - 方案 A: 更新测试断言，允许 `?? source.path` fallback 模式（代码行为正确）
  - 方案 B: 修改 SourcesPage.tsx 代码使 `?? source.path` 不再出现
  - 评估后选择最优方案
- 目标: `python -m pytest tests/ -q` exit code = 0

### U3: Gate Evidence Reporting 硬化
- 确保 `/mf-autopilot` gate reporting 遵循 gate evidence rule (mf-autopilot.md §7.1)
- 禁止 truncated output、禁止 timeout-as-pass、禁止 hidden exit code
- 目标: 之后所有 gate 报告格式统一

### U4: Quality Dashboard Note
- 写入当前 quality baseline
- 建立 pre-existing issues 追踪
- 定义每个 pre-existing 的 ownership 和 target version
