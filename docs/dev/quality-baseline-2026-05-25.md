---
title: "Quality Baseline — 2026-05-25"
type: quality-report
date: 2026-05-25
version: v2.0
---

# Quality Baseline 2026-05-25

## Gate Status（fresh re-run）

| Gate | Command | Exit | Status |
|------|---------|------|--------|
| ruff | `ruff check src tests` | 0 | pass |
| pytest full | `python -m pytest tests/ -q` | 0 | 100% pass (~340 tests) |
| npm build | `npm --prefix web run build` | 0 | pass |
| product copy | `python -m pytest tests/test_web_product_copy.py -q` | 0 | pass |
| git diff | `git diff --check` | 0 | clean |

## 测试覆盖审计

### 核心模块（有专用 test 文件）

| 模块 | Test 文件 | 测试函数数 | 覆盖评估 |
|------|----------|-----------|---------|
| approval_service | test_approval_service.py (13) + test_approval_service_boundaries.py + test_approval_decision.py | 20+ | good |
| review_service | test_review_service.py (7) + test_review_service_boundaries.py | 10+ | adequate |
| recall_service | test_recall_service.py (8) | 8 | adequate |
| wiki_service | test_wiki_service.py (16) + wiki/ (10 files) | 50+ | good |
| trash_service | test_trash_service.py (21) | 21 | good |
| safety_policy | test_safety_policy.py (5) | 5 | adequate |
| relations/community | test_community.py (9) | 9 | adequate |
| relations/discovery_context | test_discovery_context.py (21) | 21 | good |
| relations/graph_builder | test_graph_builder.py (36) | 36 | good |
| relations/graph_models | test_graph_models.py (12) | 12 | good |
| relations/related_cards | test_related_cards.py (15) | 15 | good |
| relations/scoring | test_scoring.py (15) | 15 | good |
| relations/local_graph | test_graph.py (same domain, 20+) | indirect | adequate |
| health/health_service | test_health_service.py | 5+ | adequate |

### 核心模块（通过集成/API 测试间接覆盖）

| 模块 | 间接覆盖来源 | 覆盖评估 |
|------|------------|---------|
| library_service | test_web_api.py, test_library_cli.py | indirect — adequate for current usage |
| ingestion_service | test_ingestion_service_boundaries.py, test_ingestion_diagnostics.py | indirect — adequate |
| card_workspace_service | test_cards_approval_metadata.py, test_web_api.py | indirect — adequate |
| lexical_index | test_recall_service.py (uses BM25 via recall) | indirect — adequate |
| provider_readiness | test_v013_provider_readiness.py, test_v013_cli_provider_surface.py | indirect — adequate |
| config | test_config.py, test_workspace_resolution.py | indirect — good |
| process_service | test_process_service.py, test_process_service_boundaries.py | 10+ | good |

### 测试覆盖盲区

| 模块 | 风险 | 建议 |
|------|------|------|
| library_service | 无直接单元测试，依赖 Web API 集成测试 | 低风险 — 是否新增直接测试留给 v2.0+ |
| card_workspace_service | 无直接单元测试 | 低风险 — 逻辑简单（frontmatter-safe body replace） |
| lexical_index | 无直接单元测试 | 中等风险 — BM25 算法正确性需更多断言；v2.2 会加强 |
| local_graph | 无独立测试文件 | 低风险 — 通过 graph_builder 间接覆盖 |

## 已知问题清单

### P2（应修复但不阻塞主线）

| ID | 描述 | 位置 | 来源 |
|----|------|------|------|
| P2-001 | CLI 依赖 Web 模块 | `cli_processing_runtime.py`, `processing_worker.py`, `runs_cli.py` → `mindforge_web.services` | v2.0 architecture audit |
| P2-002 | I4 zip export 未实现 | `v1.5 I4 defer` | completion summary |
| P2-003 | I5 scheduled health check 未实现 | `v1.5 I5 defer` | completion summary |

### P3（低优先级改进）

| ID | 描述 | 位置 |
|----|------|------|
| P3-001 | Router 内联业务逻辑 | `routers/wiki.py` inline imports; `routers/library.py:export_cards` inline serialization |
| P3-002 | architecture.md 过时 | `docs/dev/architecture.md` 引用旧目录结构（strategies/, processors/, services/） |

### P4（愿望清单）

| ID | 描述 |
|----|------|
| P4-001 | `library_service.py` 增加直接单元测试 |
| P4-002 | `lexical_index.py` 增加独立 benchmark tests |
| P4-003 | `card_workspace_service.py` 增加直接单元测试 |

## 技术债务登记

| 债务 | 位置 | 影响 | 清偿计划 |
|------|------|------|---------|
| processing_run_service 放在 web | `mindforge_web/services/` | CLI 必须 import Web | v2.0+ 考虑迁移到 core |
| schemas.py ~1030 lines | `mindforge_web/schemas.py` | 单文件过大 | 考虑按 domain 拆分 |
| web_facade.py ~1400 lines | `mindforge_web/services/web_facade.py` | 编排层增长 | 考虑按 domain 拆分 facade |
| i18n.ts ~1260 lines | `web/src/lib/i18n.ts` | 单文件过大 | 考虑按 domain 拆分 |

## 文档健康状况

| 文档 | 状态 | 备注 |
|------|------|------|
| architecture.md | 过时 | 引用 v0.x 结构（strategies/, processors/）；v2.0 新增 architecture-map.md 替代 |
| engineering-workflow.md | 最新 | v1.5 更新 |
| testing.md | 最新 | 覆盖本地 push gate |
| copy-policy.md | 最新 | Web copy 规范 |
| design-system.md | 最新 | Tailwind token 定义 |
| user-guide.md | 可用 | 可能需要更新 v1.4+ 新 UI |

## Next Actions

1. 本基线文档作为 v2.0 交付件
2. P2-001（CLI→Web 依赖）记录在案，不修复
3. P3-001（router 内联逻辑）记录在案，不修复
4. 测试覆盖盲区留给 v2.1-v2.5 各阶段按需加强
5. 技术债务留给后续 phase 按优先级清偿
