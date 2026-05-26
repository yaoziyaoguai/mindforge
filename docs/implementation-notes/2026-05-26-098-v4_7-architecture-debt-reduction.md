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
| C | (pending) | refactor: extract shared common schemas (4 types, ~78 lines) |

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

## Slice C: Common Shared Schema Types Extraction

从 `schemas/__init__.py` 提取 4 个共享基础类型到 `schemas/common.py`。

### 变动
- 新增 `schemas/common.py` (78 lines)：`StatusLevel`、`NextAction`、`StatusItem`、`SourcePathViewModel`
- `schemas/__init__.py` 从 1216 → 1154 lines (-62 lines)
- 通过 `from mindforge_web.schemas.common import ...` 在 `__init__.py` 中保持 re-export

### 原因
这 4 个类型被 `__init__.py` 中多个 domain schema（DraftSummary、DraftsResponse、ProviderReadinessResponse 等）以及 6+ 个 service 文件广泛引用。将它们提取为独立公共模块，为后续 Review/Approval schema extraction 扫清循环 import 障碍。
`SourcePathViewModel` 此前是 Review/Approval 提取的主要阻塞点（DraftSummary 引用它），现在该阻塞已解除。

---

## schemas.py 行数演变

| 阶段 | __init__.py | sub-modules | 总计 |
|------|-----------|-------------|------|
| Before | 1375 | — | 1375 |
| After Slice A | 1285 | 120 | 1405 |
| After Slice B | 1216 | 209 | 1425 |
| After Slice C | 1154 | 287 | 1441 |

注：总行数略增是因为每个子模块有独立的 docstring + import header，但 **主文件从 1375 → 1154 行（-16%）**。`__init__.py` 现在只包含 domain schema 定义 + re-exports。

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

- **Slice D: Import/Export Service Extraction from web_facade** — 需独立 spec，在 schema 稳定后进行
- **web_facade.py graph/sensemaking 方法提取** — lab/internal 代码，暂不优先

### 下一轮推荐

1. **Review/Approval schema extraction** — Slice C 解除循环 import 障碍后现已可行。DraftSummary、DraftsResponse、DraftDetailResponse 等 schema 可提取到 `schemas/review.py`
2. **Provider/Config schema extraction** — ProviderReadinessResponse、EnvKeyStatus 等 provider/config schema 可提取到 `schemas/provider.py`
3. Slice D: Import/Export Service Extraction from web_facade

---

## 硬红线遵守

- 未破坏任何 API contract — 所有 `from mindforge_web.schemas import X` 仍然有效
- 未新增 Port/ABC
- 未触碰 Graph/Sensemaking/Entity/Community 代码
- 未修改任何业务逻辑
- 未读取 .env/secrets
- 未调用真实 LLM
- 未新增依赖
