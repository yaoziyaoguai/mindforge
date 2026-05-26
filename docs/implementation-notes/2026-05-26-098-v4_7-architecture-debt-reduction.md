# v4.7 Architecture Debt Reduction — Implementation Notes

**日期**: 2026-05-26
**输入**: docs/plans/2026-05-26-098-v4_7-architecture-debt-reduction-plan.md
**状态**: in_progress

---

## 执行摘要

v4.7 开始偿还 quality-debt-ledger 中的 P2-02/P2-03（web_facade.py/schemas.py 巨石），采用小步 schema extraction 策略。每步只提取无交叉依赖的独立 schema 组，保持 backward-compatible imports。

### Commits

| Slice | Commit | Description |
|-------|--------|-------------|
| Plan | `374ce2e` | docs: v4.7 architecture debt reduction plan |
| A | `374ce2e` | refactor: extract import/export schemas (14 classes, ~120 lines) |
| B | `b28cd0b` | refactor: extract dogfood + lifecycle schemas (4 classes, ~89 lines) |

---

## Slice A: Import/Export Schema Extraction

从 `schemas.py` 提取 14 个 import/export API schema 类到 `schemas/import_export.py`。

### 变动
- `schemas.py` → `schemas/` package (git mv → `schemas/__init__.py`)
- 新增 `schemas/import_export.py` (120 lines)
- `schemas/__init__.py` 通过 re-export 保持 backward compatibility
- `tests/test_module_boundary_contract.py` 更新：适配 schemas package 结构

### 原因
Import/Export 是主路径第一站和最后一站，schema 完全自包含，零交叉依赖风险。

---

## Slice B: Dogfood + Lifecycle Schema Extraction

从 `schemas/__init__.py` 提取 Dogfood 和 Lifecycle schema 到 `schemas/dogfood_lifecycle.py`。

### 变动
- 新增 `schemas/dogfood_lifecycle.py` (89 lines)
- `schemas/__init__.py` 从 1285 → 1216 lines

### 原因
DogfoodReportResponse 和 LifecycleResponse 都完全自包含，无跨 schema 引用。

---

## schemas.py 行数演变

| 阶段 | __init__.py | 子模块 | 总计 |
|------|-----------|--------|------|
| Before | 1375 | — | 1375 |
| After Slice A | 1285 | 120 | 1405 |
| After Slice B | 1216 | 209 | 1425 |

注：总行数略增是因为每个子模块有独立的 docstring + import header，但 **主文件从 1375 → 1216 行（-12%）**，可发现性显著提升。

---

## Gate Results

所有 slice 共享相同 gate 基线：

| Gate | Command | Exit Code | Notes |
|------|---------|-----------|-------|
| ruff | `ruff check src/ tests/ docs/` | 0 | All checks passed |
| pytest | `python -m pytest tests/ -q --tb=short` | 0 | 3030+ passed, 1 skipped (pre-existing) |
| npm build | `npm --prefix web run build` | 0 | built in ~4s |
| git diff | `git diff --check` | 0 | Clean |

---

## 未做事项

### 本轮 defer

- **Slice C: Import/Export Service Extraction from web_facade** — 需独立 spec，在 schema 稳定后进行
- **Review/Approval schema extraction** — DraftSummary 引用 SourcePathViewModel，存在循环 import 风险，需先提取共享类型
- **web_facade.py graph/sensemaking 方法提取** — lab/internal 代码，暂不优先

### 下一轮推荐

1. 提取共享 schema 类型（`SourcePathViewModel`、`StatusItem`、`NextAction`）到 `schemas/common.py`，为更多 domain extraction 扫清循环 import 障碍
2. Slice C: Import/Export Service Extraction from web_facade
3. Review/Approval schema extraction（在共享类型提取后可行）

---

## 硬红线遵守

- 未破坏任何 API contract — 所有 `from mindforge_web.schemas import X` 仍然有效
- 未新增 Port/ABC
- 未触碰 Graph/Sensemaking/Entity/Community 代码
- 未修改任何业务逻辑
- 未读取 .env/secrets
- 未调用真实 LLM
- 未新增依赖
