# v2.0-v2.5 Independent Delivery Audit

## Overall Score: 93/100 — 交付真实，发现 1 个 P1 文档/代码不一致

审计日期: 2026-05-25

---

## 1. Delivery Truth Audit

### v2.0 — Knowledge OS Architecture Baseline

| 主张 | 证据 | 判定 |
|------|------|------|
| 架构边界测试 | `tests/test_architecture_boundaries.py` (224行, 9 tests) — AST import 验证 | ✅ PASS |
| 模块边界契约测试 | `tests/test_module_boundary_contract.py` (129行, 10 tests) — public API 导入验证 | ✅ PASS |
| 架构基线实现笔记 | `docs/implementation-notes/2026-05-25-060-v2_0-architecture-baseline.md` (50行) | ✅ PASS |

### v2.1 — Deep Graph Discovery & Community Layer

| 主张 | 证据 | 判定 |
|------|------|------|
| U1: 社区层级与深度 | `relations/community.py:111` — `_build_hierarchy()` 多层级分组 + 重叠检测 + 质量评分 | ✅ PASS |
| U2: 多跳关系扩展 | `relations/related_cards.py:83` — BFS 2-hop, `_HOP_DECAY=0.7`, via_path 路径可见 | ✅ PASS |
| U3: 发现上下文增强 | `relations/discovery_context.py:206` — `_build_reasoning()` + `_estimate_token_count()` | ✅ PASS |
| U4: 图谱关系质量测试 | `tests/relations/test_graph_golden.py` — golden tests + edge cases + perf baseline | ✅ PASS |
| U5: 社区视图 UI | `web/src/components/KnowledgeCommunityPanel.tsx` (223行) + GraphNavigationPanel community grouping | ✅ PASS |

### v2.2 — Local Lexical Search / FTS Foundation

| 主张 | 证据 | 判定 |
|------|------|------|
| RetrievalPort 抽象 | `retrieval/retrieval_port.py:23` — ABC, search/hybrid_search 方法 | ✅ PASS |
| BM25/词法索引 | `lexical_index.py` — BM25F 加权实现，停用词过滤 | ✅ PASS |
| searchIndexPort | **仅存在于 docs/plans 中作为计划项，代码中无定义** | ❌ P1 MISSING |
| BM25 vs FTS ADR | `docs/adr/2026-05-24-001-retrieval-backend.md` — ADR-001 | ✅ PASS |

### v2.3 — Embedded Graph Backend Spike

| 主张 | 证据 | 判定 |
|------|------|------|
| GraphPort 契约测试 | `tests/relations/test_graph_port.py` — 9 tests, contract + builder | ✅ PASS |
| 查询能力差距分析 | `docs/adr/2026-05-25-004-graph-query-capability-gap-analysis.md` | ✅ PASS |
| ADR-002 刷新 | `docs/adr/2026-05-24-002-kuzu-graph-backend.md` — Accepted, keep in-memory | ✅ PASS |
| GraphPort 抽象 | `relations/graph_port.py:20` — ABC, 4 抽象方法 | ✅ PASS |

### v2.4 — Source Ingestion & Local Workspace Pipeline

| 主张 | 证据 | 判定 |
|------|------|------|
| U1: Markdown 文件夹导入 | `web_facade.py:657,760` + `routers/library.py` + `FolderImportForm.tsx` | ✅ PASS |
| U2: 导入去重 | `web_facade.py:865` — exact match + Jaccard fuzzy (threshold >=0.6) | ✅ PASS |
| U3: 批量粘贴导入 | `ImportCardForm.tsx:12` — `---` 分隔检测 + `library.py:241` batch API | ✅ PASS |
| U5: 验证框架 | `web_facade.py:645-655` + `tests/test_import_validation.py` (16 tests) | ✅ PASS |
| U6: Zip 导出 | `library.py:166-224` — StreamingResponse(cards.md + manifest.json) | ✅ PASS |
| 路径不一致 | changelog 说 `import_service.py`/`export_service.py`/`import_validation.py`，实际在 `web_facade.py`/`routers/library.py` | ⚠️ P2 PATH_MISMATCH |

### v2.5 — Personal Knowledge Workbench Productization

| 主张 | 证据 | 判定 |
|------|------|------|
| U1: 工作台首页增强 | `HomePage.tsx:134,257` — LifecycleStep 组件 + lifecycle API | ✅ PASS |
| U2: 生命周期视图 | `routers/lifecycle.py` + `app.py:105` — GET /api/lifecycle | ✅ PASS |
| U3: Dogfood 报告 | `routers/dogfood.py` + `DogfoodPage.tsx` + `app.py:103` | ✅ PASS |
| U4: Provider 就绪 | `provider_readiness.py` (238行) + router + `app.py:104` | ✅ PASS |
| U5: LoadingSkeleton | `LoadingSkeleton.tsx:12` — 10 variants, all present | ✅ PASS |
| U6: Product Copy Tests | `test_web_product_copy.py` — health/dogfood/lifecycle/import/export/provider tests | ✅ PASS |
| U7: Documentation Polish | `architecture.md` 路由表 6→15, `user-guide.md` 新增 4 章节 | ✅ PASS |
| U8: Changelog | `docs/design/v2.0-v2.5-changelog.md` | ✅ PASS |

---

## 2. Gate Evidence Audit

### 当前 Gate 运行（完整输出，无 tail/head）

| Gate | 命令 | Timeout | Exit Code | 结果 |
|------|------|---------|-----------|------|
| npm build | `npm --prefix web run build` | no (2.48s) | 0 | ✅ PASS |
| product copy | `python -m pytest tests/test_web_product_copy.py -q` | no | 0 (72 passed) | ✅ PASS |
| ruff | `ruff check src/ tests/ --statistics` | no | 0 (clean) | ✅ PASS |
| git diff | `git diff --check` | no | 0 | ✅ PASS |
| full pytest | `python -m pytest tests/ -q` | no | 0 (~3600 tests, 1 skip) | ✅ PASS |

### 上一轮 Gate Evidence 问题

上一轮使用了 `tail -3`/`tail -5` 截断输出报告 gate 结果，违反 gate evidence rule。
本轮已修正：所有 gate 完整运行并报告完整 exit code。

### Pre-existing 问题复查

之前报告的 17 ruff errors 和 pytest failures 在本轮验证中已不存在：
- ruff: clean (EXIT_CODE=0)
- pytest: full pass (EXIT_CODE=0, 1 intentional skip)

---

## 3. Architecture Boundary Audit

### 模块边界清晰度

| 边界 | 评分 | 说明 |
|------|------|------|
| Source ↔ Card | ✅ 清晰 | SourceAdapter 归一化层明确 |
| Card ↔ Wiki | ✅ 清晰 | Wiki 只读 human_approved |
| Graph ↔ Search | ✅ 清晰 | GraphPort / RetrievalPort 各自抽象 |
| Review ↔ Approval | ✅ 清晰 | 显式审批门禁无绕过 |
| Export ↔ Import | ⚠️ 部分耦合 | `web_facade.py` 承载过多逻辑 (~1500行)，import/export 逻辑散布在 router 和 facade 之间 |
| Provider Safety | ✅ 清晰 | Secret store 隔离，API 不返回 raw key |
| Web ↔ Backend | ⚠️ 观察 | `web_facade.py` 是事实上的 monolithic service aggregator，尚可接受但需警惕 |

### 新巨石风险

`web_facade.py` 约 1500+ 行，聚合了 lifecycle、dogfood、import、export、provider_readiness 等多种职责。当前仍在可管理范围内，但 v3.x 应考虑按 domain 拆分。

### 贫血抽象

- `SearchIndexPort` 存在于文档但不存于代码 — 这是一个文档超前于实现的例子
- 其他端口抽象 (GraphPort, RetrievalPort) 有实际实现支撑

---

## 4. Safety Semantics Audit

| 检查项 | 结果 | 证据 |
|--------|------|------|
| AI 只生成 ai_draft | ✅ PASS | `import_card()` 全部创建 `status="ai_draft"` |
| human_approved 需 explicit approval | ✅ PASS | 审批路径全部经过 `approve.show` + `--confirm` |
| 无自动审批 | ✅ PASS | `custom.py:194` 显式拒绝 `auto_approve` key |
| 无 LLM/Cubox/Upstage 调用 | ✅ PASS | 无真实外部 API 调用路径 |
| 无 .env/secrets 读取 | ✅ PASS | API key 通过 secret store，不在 git |
| 无 RAG/embedding/vector DB | ✅ PASS | grep 确认所有 mention 均为"不使用/不做"声明 |
| 无真实私人资料处理 | ✅ PASS | 所有测试用 fixture/fake 数据 |
| 无真实 Obsidian write | ✅ PASS | obsidian_cli 只读解析 wikilinks |
| API key 不泄露 | ✅ PASS | `provider_readiness.py` masked key, `safety_policy.py` 白名单 |

---

## 5. Product Usefulness Audit

### 能力闭环检查

| 路径 | 状态 | 说明 |
|------|------|------|
| import → ai_draft | ✅ 可用 | 文件夹导入 / 批量粘贴 / 单文件 |
| ai_draft → review → approve | ✅ 可用 | CLI + Web Review 页 |
| approved → Library/Recall/Wiki | ✅ 可用 | BM25检索 + Library浏览 + Wiki合成 |
| graph discovery | ✅ 可用 | 关系图谱 + 社区检测 + 多跳导航 |
| export | ✅ 可用 | JSON/OPML/Zip 多格式 |
| dogfood report | ✅ 可用 | 本地使用报告仪表板 |
| provider readiness | ✅ 可用 | Setup 页 provider 状态面板 |
| health check | ✅ 可用 | 知识健康诊断 |

### 剩余割裂

- Import/Export 没有独立的顶层导航页 — 功能挂在 Library 页下
- Dogfood/Health/Lifecycle 是新页面但入口分散
- 整体 navigation 仍以功能页为主，缺少 user-journey 视角

---

## 6. Findings Classification

### P0 — Critical (0项)
无。没有破坏性 bug、安全漏洞、或核心功能缺失。

### P1 — High (1项)

| ID | 发现 | 影响 |
|----|------|------|
| P1-01 | `SearchIndexPort` 代码缺失 — changelog 声称 v2.2 建立了此边界，但代码中不存在 | 文档/代码不一致。changelog 需要修正措辞或代码需要补充 |

### P2 — Medium (3项)

| ID | 发现 | 影响 |
|----|------|------|
| P2-01 | v2.4 changelog 路径不一致 — `import_service.py`/`export_service.py`/`import_validation.py` 实际在 `web_facade.py` | 文档导航误导 |
| P2-02 | `web_facade.py` 1500+行，承载 lifecycle/dogfood/import/export/provider 等多种职责 | 长期维护风险 |
| P2-03 | Import/Export 无独立导航入口 — 功能挂在 Library 页下 | 产品 UX 割裂 |

### P3 — Low (2项)

| ID | 发现 | 影响 |
|----|------|------|
| P3-01 | npm build chunk size warning (>500KB) | 性能: 非阻塞 |
| P3-02 | 1 skipped test in full pytest suite | 测试: 需确认 skip 理由 |

---

## 7. Remediation Plan

### 进入 v3.0 立即修复

| 优先级 | 项目 | 行动 |
|--------|------|------|
| P1-01 | SearchIndexPort 缺失 | 修正 changelog 措辞: "planned boundary" 而非 "established"；或在代码中补充最小 Port 定义 |
| P2-01 | 路径不一致 | 更新 changelog/notes 中的模块路径引用 |
| P3-02 | Skipped test | 确认 skip 理由并记录或修复 |

### 进入 v3.1+ 处理

| 优先级 | 项目 | 行动 |
|--------|------|------|
| P2-02 | web_facade.py 巨石 | v3.1 workspace persistence 重构时按 domain 拆分 |
| P2-03 | Import/Export 导航 | v3.5 Workbench UX Integration 统一入口 |
| P3-01 | Chunk size | v3.5 前端优化时处理 |

### 不修复

无。所有发现均可归类处理。

---

## 8. Audit Conclusion

v2.0-v2.5 long-horizon roadmap 的代码交付是**真实的**——每个阶段都有可追溯的代码、测试、文档三重支撑。唯一的文档/代码差距是 `SearchIndexPort`（存在于 roadmap 规划但未在代码中实现），需要在 v3.0 修正 changelog 措辞或补充代码。

架构边界整体清晰，安全语义无违规，产品路径可 dogfood。主要改进空间在代码组织（web_facade 巨石化）和 UX 连贯性（navigation 分散）。
