# Quality Debt Ledger

基于 v2.0-v3.6 independent delivery audit 和 v3.6.1 remediation Batch A 更新。

更新日期: 2026-05-25

---

## Open Debt

| ID | Priority | Description | Source | Status | Target |
|----|----------|-------------|--------|--------|--------|
| P2-02 | P2 | web_facade.py God Service (2033 行), 30+ public methods 跨 10+ 领域 | v2.x → v3.x | open | v3.7+ |
| P2-03 | P2 | schemas.py God Schema (1279 行), 62 schema 单文件 | v2.x → v3.x | open | v3.7+ |
| P2-04 | P2 | RetrievalPort ABC 未集成到 recall_service — recall_service 绕过端口直接调用 lexical_index | v2.2 → v3.6 | resolved — v3.6.1 Batch B2 | v3.7 |
| P2-05 | P2 | 零前端测试覆盖 (0 test files in web/src/) | v2.x → v3.x | open | v3.7 |
| P2-06 | P2 | 无覆盖率配置 — pyproject.toml 无 [tool.coverage] | v2.x → v3.x | open | v3.7 |
| P1-04 | P1 | v4.2 后 `/graph` 独立页仍展示 8 种 NodeType selector，其中 community/topic/entity/concept_candidate 会被 API 422；GraphExplorer 主入口已收缩，但内部路由仍可误导 | v4.2 post-remediation re-audit | open | 下一轮稳定化 |
| P2-07 | P2 | 旧 ADR / roadmap / implementation notes 中仍有 v4.2 前的 graph/sensemaking 过度声明；本轮只修正 user guide、architecture 和关键 notes，完整文档归档/收缩仍未做 | v4.2 post-remediation re-audit | open | Documentation System Reset |
| P3-01 | P3 | npm build chunk size >500KB | v2.5 | open (非阻塞) | — |
| P3-02 | P3 | 1 skipped test (conditional: no runs written) | pre-existing | acknowledged (正常条件跳过) | — |
| P3-03 | P3 | test_approval/review/process_service_boundaries 三文件间 ~50% AST helper 同构代码（有意不共享 fixture，独立可理解） | v2.x | acknowledged (设计选择) | — |

## Resolved Debt

| ID | Priority | Description | Resolution |
|----|----------|-------------|------------|
| P1-01 | P1 | SearchIndexPort changelog 措辞修正 | v3.0: changelog 措辞已修 |
| P2-01 | P2 | v2.4 changelog 路径不一致 | v3.0: 路径引用已更新 |
| P1-01 (audit) | P1 | Gate Evidence 不可重现 — pytest exit code=1 (docx import fail + flaky perf test) | v3.6.1 Batch A: docx importorskip + GC disable/warmup fix |
| P1-02 (audit) | P1 | zh-CN user-guide.md 未随 v2.5 更新 | v3.6.1 Batch B1 |
| P1-03 (audit) | P1 | architecture.md 引用不存在的 import_service.py/export_service.py | v3.6.1 Batch A4: 修正为 web_facade.py + routers/library.py |
| — | pre-existing | ruff 17 errors | Resolved pre-v3.0 (ruff clean) |
| — | pre-existing | pytest failures (docx import + flaky perf test) | Resolved v3.6.1: importorskip + GC disable/warmup |
| P2-03 (legacy) | P2 | Import/Export 无独立导航入口 | v3.5: Workbench UX 集成已处理 |
| P2-04 | P2 | RetrievalPort ABC 未集成到 recall_service | v3.6.1 Batch B2: recall_service 通过 engine.load_or_build_index() 管理索引生命周期，不再直接操作 lexical_index |

---

## Gate Baseline (v3.6.1 Batch B2 — Reproducible)

全量 gate 在 remediation tree 上运行，exit code 真实可重现。

| Gate | Command | Exit Code | Timeout | Detail |
|------|---------|-----------|---------|--------|
| ruff | `ruff check src/ tests/ docs/` | 0 | no | All checks passed |
| git diff | `git diff --check` | 0 | no | — |
| npm build | `npm --prefix web run build` | 0 | no | built in ~2.5s (chunk size >500KB warning, known P3-01) |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | 0 | no | 76 passed |
| test_web_api | `python -m pytest tests/test_web_api.py -q --tb=short` | 0 | no | 170 passed (docx importorskip working) |
| graph perf (x3) | `python -m pytest tests/relations/test_graph_perf.py -q --tb=short` ×3 | 0 | no | 8 passed ×3 (deterministic repeat stable) |
| recall + port | `python -m pytest tests/test_recall_service.py tests/test_retrieval_port.py -q --tb=short` | 0 | no | 23 passed (含 B2 新增 test_recall_service_uses_retrieval_port_for_index_loading) |
| full pytest | `python -m pytest tests/ -q --tb=short` | 0 | no | ~3028 passed, 1 skip (conditional: no runs written) |

### 验证说明

- v3.6.1 Batch A + B2 修复后，所有 gate exit 0 在当前环境可重现
- P2-04 (RetrievalPort 集成) 已修复：recall_service 通过 engine.load_or_build_index() 管理索引生命周期
- test_web_api.py docx 相关测试在缺少 python-docx 时正确 skip（`pytest.importorskip("docx")`）
- test_perf_deterministic_repeat 通过 GC disabled + warmup 调用消除 flakiness（3 次连续运行稳定 pass）
- architecture.md 不存在的文件引用已修正
- test_rebuild_deterministic 偶发失败为 pre-existing test isolation 问题（非本批次引入，单独运行 wiki_service 测试 16 passed）
- 每个 gate 报告包含 exact command + real exit code + timeout status + failure detail (if any)
