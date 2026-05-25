# v3.6.1 Remediation — Batch A + B1 + B2

基于 `docs/audits/2026-05-25-v2.0-v3.6-independent-audit.md` 的修复执行记录。

日期: 2026-05-25

---

## 审计发现处理

| Finding | Priority | Batch | Status |
|---------|----------|-------|--------|
| P1-01: Gate Evidence 不可重现 (pytest exit 1) | P1 | A | 已修复 |
| P1-02: zh-CN user-guide.md 未随 v2.5 更新 | P1 | B1 | 已修复 |
| P1-03: architecture.md 引用不存在的文件 | P1 | A4 | 已修复 |
| P2-04: RetrievalPort 未集成到 recall_service | P2 | B2 | 已修复 |

---

## A1: docx 可选依赖修复

**文件**: `tests/test_web_api.py`

**问题**: `_write_minimal_docx()` 在缺少 `python-docx` 时抛出 `ModuleNotFoundError`，污染 full gate。

**修复**:
- 在 `_write_minimal_docx()` 函数首行添加 `pytest.importorskip("docx", reason="...")`
- 添加中文注释说明 docx 是可选依赖，缺失时应 skip 而非 fail

**安全性**: 不影响核心产品语义，不改变审核/审批行为。

**验证**:
```bash
python -m pytest tests/test_web_api.py -q --tb=short
# exit 0, 170 passed
```

---

## A2: test_perf_deterministic_repeat flaky 修复

**文件**: `tests/relations/test_graph_perf.py`

**问题**: 全量测试套件中，其他测试的 GC 垃圾对象和 JIT/import 缓存一次���开销导致性能测量异常值（>5x avg）。

**修复**:
- 添加 `import gc`
- 在测量循环前添加预热调用（排除 JIT/import 缓存开销）
- 测量期间 `gc.disable()`，结束后 `gc.enable()`

**安全性**: 不降低断言价值，不 skip/xfail，不改变被测代码行为。

**验证**:
```bash
for i in 1 2 3; do python -m pytest tests/relations/test_graph_perf.py -q --tb=short; done
# exit 0 ×3, 8 passed each
python -m pytest tests/ -q --tb=short
# exit 0, ~3028 passed
```

---

## A3: Gate Baseline 重跑与品质债账本更新

**文件**: `docs/dev/quality-debt-ledger.md`

**变更**: 
- 完全重写 Gate Baseline 表格，每行包含 exact command + exit code + timeout status + detail
- 所有 P1 audit findings 标记 resolved
- 添加可重现性验证说明
- 更新 Resolved Debt 表格

---

## A4: architecture.md 不存在文件引用修复

**文件**: `docs/dev/architecture.md`

**问题**: 引用 `services/import_service.py`、`services/export_service.py`、`import_validation.py` — 三个文件均不存在。

**修复**: 纠正为当前真实代码路径 `web_facade.py` + `routers/library.py`，添加诚实的状态注释说明：
- 导入导出逻辑当前集中在 `web_facade.py` (2033 行)
- 尚未拆分为独立 `ImportService` / `ExportService`
- v3.6 已定义 `ExportAdapter` ABC，未来将迁移

---

## B1: docs/zh-CN/user-guide.md 同步

**文件**: `docs/zh-CN/user-guide.md`

**新增内容**:
- Provider Readiness 章节（就绪/阻塞/未知状态说明）
- 知识生命周期流程图（Source → ai_draft → human_approved → Library/Wiki/Recall）
- Community Browser 和 Multi-hop Relations 说明
- Web 控制台页面表从 8 项扩展至 12 项
- Import & Export 完整章节（导入方式、导出格式、安全规则）
- Dogfood 章节（活动摘要、参与度指标、基础设施、建议）
- 已知限制更新（图谱确定性、Kuzu spike-only）
- 明确 fake/sample/dry-run 边界标注

---

## B2: recall_service 通过 RetrievalPort ABC 集成

**文件**:
- `src/mindforge/retrieval/retrieval_port.py` — 新增 `IndexLoadResult` dataclass 和 `load_or_build_index()` 抽象方法
- `src/mindforge/retrieval/bm25_engine.py` — 实现 `load_or_build_index()`，封装磁盘加载/内存重建/过期检测全部逻辑
- `src/mindforge/recall_service.py` — ~55 行直接 `lx.*` 索引操作替换为单个 `engine.load_or_build_index()` 调用
- `tests/test_retrieval_port.py` — 新增 `test_load_or_build_index_returns_index_load_result` 契约测试
- `tests/test_recall_service.py` — 新增 `test_recall_service_uses_retrieval_port_for_index_loading` 回归测试

**设计说明**:
- `load_or_build_index()` 将原本散落在 recall_service 中的索引生命周期逻辑收敛到 RetrievalPort 边界内
- recall_service 不再直接调用 `lx.BM25Index.load()` / `lx.build_index()` / `lx.diff_index()`
- `lx` import 保留用于 `default_index_path()` / `resolve_field_weights()` / `compute_config_hash()`（配置计算，非索引操作）
- 索引加载的 warnings 在 JSON 输出模式下过滤，保持原有行为一致性

**安全性**:
- 不引入 RAG / embedding / vector DB
- 不调用真实 LLM / Cubox / Upstage
- 不处理真实私人资料
- 不破坏 ai_draft / human_approved 审批语义
- Bm25RetrievalEngine 仍是唯一生产实现，未来可替换为其他后端而 recall_service 无需改动

---

## Gate 结果 (最终)

| Gate | Command | Exit Code |
|------|---------|-----------|
| ruff | `ruff check src/ tests/ docs/` | 0 |
| git diff | `git diff --check` | 0 |
| npm build | `npm --prefix web run build` | 0 |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 |
| test_web_api | `python -m pytest tests/test_web_api.py -q --tb=short` | 0 |
| graph perf ×3 | `python -m pytest tests/relations/test_graph_perf.py -q --tb=short` ×3 | 0 |
| recall + port | `python -m pytest tests/test_recall_service.py tests/test_retrieval_port.py -q --tb=short` | 0 |
| full pytest | `python -m pytest tests/ -q --tb=short` | 0 |
| second full pytest (consistency) | `python -m pytest tests/ -q --tb=short` | 0 |

---

## 延后项

以下明确延后至 v3.7+，不在本次 remediation loop 中处理:

- **B3**: coverage threshold 配置
- **B4**: 前端 smoke tests (vitest/happy-dom)
- **B5**: web_facade.py 分解（需单独 spec/plan/review）

理由: B3/B4/B5 属于 v3.7 Quality Platform / Frontend Quality / Service Decomposition，不应在修复 gate 的 remediation loop 中执行。

---

## v3.7 Planning

**状态: 已解锁**

Batch A 全部完成 + B1/B2 完成 + 所有 gate 可重现 clean。v3.7 planning 可以开始，但不要直接实现 v3.7 新功能（需独立 spec/review/plan）。
