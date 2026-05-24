---
title: "v2.0-v2.5 Long-horizon Roadmap — Knowledge OS Architecture & Deep Discovery"
type: roadmap
status: active
date: 2026-05-25
parent: v1.5 Safe Integration & Import/Export Expansion
---

# v2.0-v2.5 Long-horizon Roadmap

## 总览

| 阶段 | 主题 | 预估 Units | 依赖 |
|------|------|-----------|------|
| v2.0 | Knowledge OS Architecture & Quality Baseline | 4-6 | v1.5 complete |
| v2.1 | Deep Graph Discovery & Community Layer | 4-6 | v2.0 |
| v2.2 | Local Lexical Search / FTS Foundation | 3-5 | v2.0 |
| v2.3 | Optional Embedded Graph Backend Spike | 3-4 | v2.0 |
| v2.4 | Source Ingestion & Local Workspace Pipeline | 4-6 | v2.0 |
| v2.5 | Personal Knowledge Workbench Productization | 5-8 | v2.1-v2.4 |

v2.1-v2.4 可部分并行（v2.1 和 v2.2 互不依赖，v2.3 和 v2.4 互不依赖）。Autopilot 应串行执行以避免 context 碎片化。

---

## v2.0: Knowledge OS Architecture & Quality Baseline

### Goals

1. 梳理 Source / Card / Wiki / Graph / Search / Review / Approval / Export / Import / Provider Safety 十个领域的模块边界，输出 architecture map
2. 建立 "core / adapter / UI / policy / future-spike" 分层模型
3. 清理所有 completion summary、task status、gate evidence
4. 建立 architecture boundary tests（不依赖具体实现细节）
5. 建立 quality baseline note（module health、test coverage gaps、known tech debt）
6. 不新增功能，只做架构可见性和可维护性

### Non-goals

- 不改现有 API contract
- 不重构模块内部实现
- 不新增依赖
- 不引入新的 graph/search/import 功能

### Implementation Units

#### U1: Architecture Map & Boundary Inventory
- 遍历全部 `src/mindforge/` 和 `src/mindforge_web/` 模块
- 输出 `docs/dev/architecture-map.md`：
  - 每个模块的职责（一句话）
  - 所属 layer（core / adapter / UI / policy / spike）
  - 上下游依赖关系
  - import 边界（谁可以 import 谁）
- 识别循环依赖、layer violation、边界模糊的模块

#### U2: Module Health Baseline
- 检查每个核心模块的：
  - 是否有对应 test 文件
  - test 覆盖的主要路径
  - 已知 P2-P4 问题
  - docstring/注释覆盖
- 输出 `docs/dev/quality-baseline-2026-05-25.md`
- 不修复问题，只记录（修复留给后续 phase）

#### U3: Architecture Boundary Tests
- 新增或增强 `tests/test_architecture_boundaries.py`：
  - 验证核心模块不 import Web/UI 模块
  - 验证 policy 模块不 import service 模块
  - 验证 adapter 模块不 import 其他 adapter
  - 验证 fake provider 不 import 真实 provider
- 新增 `tests/test_module_boundary_contract.py`：
  - 验证 public API 表面（`__all__` 或等效）不泄露内部实现

#### U4: Gate Evidence & Quality Dashboard Baseline
- 更新 `docs/dev/testing.md` 和 gate evidence 规则
- 建立可复现的 gate 运行脚本
- 确保 `./scripts/check.sh` 覆盖全部 gate
- 输出 quality dashboard note

#### U5 (optional): Code Simplicity Audit
- 识别 dead code、unused imports、过度抽象
- 不做删除（留给后续 phase），只记录

#### U6 (optional): Docs Cross-reference Audit
- 检查 docs/ 下文档的一致性
- 更新过时的 architecture.md 引用

### Acceptance Criteria

- [ ] `docs/dev/architecture-map.md` 覆盖全部模块
- [ ] `docs/dev/quality-baseline-2026-05-25.md` 有每个核心模块的健康评估
- [ ] Boundary tests 通过且不依赖实现细节
- [ ] Gate evidence baseline 可复现
- [ ] 所有 gate 通过（ruff / pytest / npm build / product copy / git diff）

### Tests

- `tests/test_architecture_boundaries.py` — import layer 约束
- `tests/test_module_boundary_contract.py` — public API 表面约束
- 现有全量 test suite 必须保持 100% pass

### Smoke Plan

- 仅 docs 和 tests 改动，不涉及 Web/API 变更 → 跑 gate 即可，无需 browser smoke
- 如果 architecture-map 引用了具体文件路径，用 `git diff --check` 验证

### Stop Conditions

- HARD_STOP_GIT_UNSAFE_STATE
- HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN
- 如 pytest regression 非 pre-existing，回退修复

### Next-stage Transition

v2.0 完成 → 直接进入 v2.1（Deep Graph Discovery）

---

## v2.1: Deep Graph Discovery & Community Layer

### Goals

1. 深化现有 deterministic graph/relation 能力（当前 `relations/` 9 个文件）
2. 增强 deterministic topic/community grouping（当前 `community.py` 已 detect_communities）
3. 为每个 community/topic 提供 evidence/reason，不调用 LLM
4. 增强 relationship map 的 depth 和 breadth（multi-hop expansion）
5. 增强 source provenance trail 的 graph 视角
6. 输出 explainable discovery context（当前 `discovery_context.py` 已 assemble_discovery_context）

### Non-goals

- 不做 RAG answering
- 不调用真实 LLM
- 不做 embedding/vector DB
- 不引入 graph DB dependency
- 不改 `GraphPort` 接口语义（已有 ADR-002 决策）

### Implementation Units

#### U1: Community Hierarchy & Depth
- 基于当前 `community.py` 的 `detect_communities()` 扩展：
  - 多层级 community grouping（source-based → tag-based → wiki-section-based → cross-type）
  - community member scoring（card quality 加权）
  - community overlap detection（shared members across communities）
- API: 扩展 `KnowledgeCommunityResponse` 增加 `sub_communities`、`overlap_with`、`quality_score`

#### U2: Multi-hop Relationship Expansion
- 基于当前 `related_cards.py` 的 `compute_related_cards()` 扩展：
  - 2-hop → 3-hop traversal（可配置 depth）
  - path-based relation（不仅"相关"，还展示"通过什么路径相关"）
  - relation strength decay by hop distance
- API: 扩展 `RelatedCardResponse` 增加 `hop_distance`、`via_path`

#### U3: Discovery Context Composer Enhancement
- 基于当前 `discovery_context.py` 扩展：
  - community-aware context（不仅是 direct neighbors）
  - 为每个 discovery context 输出 explainable reasoning
  - context size budgeting（总 token 数估计，不做实际 LLM 调用）
- API: 扩展 `DiscoveryContextResponse` 增加 `community_refs`、`reasoning`

#### U4: Graph Relation Quality Tests
- 新增 golden tests：验证 relation 的确定性（相同输入 → 相同输出）
- 新增 edge case tests：空 graph、单 node、全连接 graph
- 新增 performance characterization tests（100/500/1000 cards）

#### U5: Community View UI Enhancement
- 增强 `KnowledgeCommunityPanel`：支持展开/折叠子社区、overlap 可视化
- 增强 `GraphNavigationPanel`：community-based grouping、community 颜色编码

#### U6 (optional): Graph Explorer Query Enhancement
- `GraphExplorer` 增加 multi-hop 展开、community filter

### Acceptance Criteria

- [ ] Community detection 支持 3+ 种 grouping type
- [ ] Multi-hop relation 支持 3-hop traversal
- [ ] Discovery context 包含 explainable reasoning
- [ ] Golden tests 验证 relation 确定性
- [ ] 所有 gate 通过

### Tests

- `tests/relations/test_community.py` — 扩展社区检测测试
- `tests/relations/test_related_cards.py` — 扩展 multi-hop 测试
- `tests/relations/test_discovery_context.py` — 扩展 context composer 测试
- `tests/relations/test_graph_golden.py` — 新 golden tests
- `tests/relations/test_graph_api.py` — API contract tests

### Smoke Plan

- Web smoke: Library → GraphNavigationPanel → community view → multi-hop expand
- API smoke: `GET /api/knowledge/communities` → `GET /api/graph/related?depth=3`

### Stop Conditions

- HARD_STOP_RAG_EMBEDDING（如果实现滑向 RAG）
- HARD_STOP_REAL_LLM（如果需要真实 LLM 做 community summary）
- 其他标准 hard-stop

### Next-stage Transition

v2.1 完成 → 继续 v2.2（Local Lexical Search）

---

## v2.2: Local Lexical Search / FTS Foundation

### Goals

1. 建立清晰的 `SearchIndexPort` / `RetrievalPort` / `LexicalIndex` 边界（当前 `lexical_index.py` 已存在，`graph_port.py` 已有 Port 模式）
2. 评估当前 BM25 实现的覆盖盲区并做定向增强
3. 如果做 FTS spike，必须 isolated、可删除、默认关闭
4. 输出检索质量评估 note（precision/recall on fake data）

### Non-goals

- 不做 embedding/vector DB
- 不引入 SQLite FTS5 / DuckDB FTS 作为生产依赖（已有 ADR-001 决策）
- 不调用真实 LLM
- 不做 RAG answering
- 不改变 recall API contract

### Background

ADR-001 已评估 BM25 vs SQLite FTS5 vs DuckDB FTS，结论是保持 BM25（零外部依赖、性能足够、确定性可测试）。本阶段的重点是加固边界和增强 BM25 质量，而非替换后端。

### Implementation Units

#### U1: RetrievalPort Formalization
- 提取 `RetrievalPort` 抽象（Protocol），参考现有 `GraphPort` 模式
- 当前 `lexical_index.py` 实现 `RetrievalPort`
- 确保 `recall_service.py` 只依赖 Port，不直接依赖实现

#### U2: BM25 Enhancement — Tokenization
- 增强中文 tokenization（当前 CJK 逐字切分）
- 可选：加 jieba 分词支持（isolated，默认关闭）
- 英文 stemming/stop-word 增强

#### U3: BM25 Enhancement — Ranking & Field Weighting
- title vs body 字段加权（title 权重 > body）
- 引入简单的 length normalization
- 搜索结果 scoring 可解释性增强

#### U4: Isolated FTS Spike (optional)
- 创建 `src/mindforge/spikes/fts_spike/` 目录
- SQLite FTS5 或 DuckDB FTS 的 prototype
- 必须：默认关闭、可完全删除、不影响 production path
- 比较 BM25 vs FTS5 的 precision/recall on shared test data

#### U5: Retrieval Quality Evaluation
- 建立 fake test data 基准
- 计算 precision@5、recall@5
- 输出 `docs/adr/2026-05-25-003-retrieval-quality-baseline.md`

### Acceptance Criteria

- [ ] `RetrievalPort` 抽象定义且 `recall_service` 只依赖 Port
- [ ] BM25 tokenization 增强不破坏现有 test
- [ ] Ranking enhancement 有可测量改善
- [ ] FTS spike 完全隔离（如果实现）
- [ ] 所有 gate 通过

### Tests

- `tests/test_recall_service.py` — 扩展检索质量测试
- `tests/test_lexical_index.py`（如不存在则新建）
- `tests/spikes/test_fts_spike.py`（如果做 spike）

### Smoke Plan

- API smoke: `GET /api/recall?q=测试查询` — 验证结果质量
- Web smoke: Search 页面 → 输入查询 → 验证结果展示

### Stop Conditions

- HARD_STOP_LARGE_DEPENDENCY（如果 FTS spike 依赖难以隔离）
- 其他标准 hard-stop

### Next-stage Transition

v2.2 完成 → 继续 v2.3（Embedded Graph Backend Spike）

---

## v2.3: Optional Embedded Graph Backend Spike

### Goals

1. 设计 `GraphRepository` / `GraphPort` 边界（当前 `graph_port.py` 已有基础）
2. 评估 In-Memory vs Kuzu-like embedded graph backend 的取舍
3. 如果做 spike，必须 isolated、可删除、默认关闭
4. 输出更新版 ADR

### Non-goals

- 不把 Kuzu 引入生产依赖
- 不改现有 `DeterministicGraphBuilder` 行为
- 不使用真实私人数据
- 不做 vector/semantic graph

### Background

ADR-002 已评估 In-Memory vs Kuzu，结论是保持 In-Memory（零依赖、性能足够）。本阶段是可选 spike，仅在 v2.0 架构清晰化后，评估是否需要更复杂的图查询能力时才触发。

### Implementation Units

#### U1: GraphRepository Pattern Formalization
- 基于现有 `GraphPort` 抽象，定义 `GraphRepository` Protocol
- `DeterministicGraphBuilder` 作为默认实现
- 定义 spike 插入点（config flag 切换）

#### U2: Graph Query Capability Assessment
- 盘点当前支持的图查询类型（1-hop、2-hop、community、source-centered）
- 识别当前 In-Memory 方案无法高效支持的查询类型
- 输出 gap analysis note

#### U3: Isolated Kuzu Spike (ONLY if U2 identifies real gaps)
- 创建 `src/mindforge/spikes/kuzu_spike/`
- 实现 Kuzu-based GraphRepository
- 仅跑 benchmarks on fake data
- 不替换 production path
- Gate: config flag `graph.backend: "kuzu-spike"` 默认 `"in-memory"`

#### U4: Updated ADR-002
- 基于 spike 结果更新 ADR-002
- 明确触发条件：何时需要 embedded graph DB，何时不需要

### Acceptance Criteria

- [ ] `GraphRepository` Protocol 定义清晰
- [ ] Gap analysis note 诚实评估当前限制
- [ ] Kuzu spike（如果做）完全隔离，不影响 production
- [ ] ADR-002 更新版有理有据
- [ ] 所有 gate 通过

### Tests

- `tests/test_graph_port.py` — Port contract tests
- `tests/spikes/test_kuzu_spike.py`（如果做 spike）

### Smoke Plan

- API smoke: graph 相关 endpoints 仍然正常响应
- 确认 `graph.backend: "in-memory"` 默认生效

### Stop Conditions

- HARD_STOP_LARGE_DEPENDENCY（如果 Kuzu 无法干净隔离）
- 其他标准 hard-stop

### Next-stage Transition

v2.3 完成 → 继续 v2.4（Source Ingestion Pipeline）

---

## v2.4: Source Ingestion & Local Workspace Pipeline

### Goals

1. 强化本地资料进入 MindForge 的安全路径
2. 扩展 fake/local import adapters（Markdown folder dry-run、manual paste import refinement）
3. 做 import preview、provenance、dedupe、safe validation
4. 改善 import error UX

### Non-goals

- 不处理真实私人资料
- 不写真实 Obsidian vault
- 不调用真实 LLM
- 不自动 approve

### Implementation Units

#### U1: Markdown Folder Import Adapter
- 扫描指定文件夹的 `.md` 文件
- Dry-run preview：列出将创建哪些卡片，不做实际写入
- 确认后批量创建 ai_draft 卡片
- 安全检查：拒绝系统文件、隐藏文件、超大文件

#### U2: Import Dedup Detection
- 基于 title + body hash 检测重复导入
- 与已有卡片做 fuzzy title matching
- Preview 中标记 potential duplicates
- 不自动跳过，用户选择

#### U3: Import Error UX Enhancement
- Manifest-style 导入结果报告（成功/跳过/失败）
- `ImportCardForm` 支持粘贴多篇（frontmatter 分隔）
- 错误信息本地化（zh/en）

#### U4: Workspace Pipeline Status View
- 新增或增强 SourcesPage 的 pipeline 状态展示
- Source → Draft → Approved 的 lifecycle 可视化
- Import history（最近 N 次导入记录）

#### U5: Safe Validation Framework
- 导入前校验：title 非空、body 非空、无 system path injection
- 导入后校验：文件确实写入、frontmatter 合法
- 校验失败的结构化错误返回（非 500 crash）

#### U6: Zip Export Package (v1.5 I4 follow-up)
- `POST /api/knowledge/export` 支持 `format: "zip"`
- zip 内包含：cards.md + manifest.json
- 前端下载 .zip 文件

### Acceptance Criteria

- [ ] Markdown folder import 可用（dry-run + confirm）
- [ ] Dedup detection 工作
- [ ] Import error report 结构化
- [ ] Zip export 可用
- [ ] 所有 gate 通过

### Tests

- `tests/test_web_api.py` — 扩展 import/export API 测试
- `tests/test_import_dedup.py` — 新 dedup 测试
- `tests/test_import_validation.py` — 新 validation 测试

### Smoke Plan

- Web smoke: Library → Import → 粘贴内容 → 确认创建 → verify in card grid
- Web smoke: Export → 选择 zip → 下载 → 解压验证内容
- Web smoke: Folder import → dry-run → confirm

### Stop Conditions

- HARD_STOP_PRIVATE_DATA（如果意外处理真实私人资料）
- 其他标准 hard-stop

### Next-stage Transition

v2.4 完成 → 继续 v2.5（Productization）

---

## v2.5: Personal Knowledge Workbench Productization

### Goals

1. 把 v2.0-v2.4 的功能组织成完整、可长期使用的本地知识工作台
2. 强调产品闭环（import → review → approve → graph → search → export）
3. 强化 Workspace Home、Source-to-Card Lifecycle、Dogfood Report Center
4. 最终 smoke test 覆盖完整用户旅程

### Non-goals

- 不做 cloud SaaS
- 不做多用户/协作
- 不做移动端
- 不做 plugin marketplace

### Implementation Units

#### U1: Workspace Home Enhancement
- HomePage 集成：knowledge stats + lifecycle overview + quick actions
- Dashboard cards: recent imports, pending reviews, graph highlights, health summary
- 各 card 点击导航到对应页面

#### U2: Source-to-Card Lifecycle View
- 展示 Source → ai_draft → human_approved 的完整 journey
- Timeline 视图：import time → draft generated → review → approve → last updated
- 跨 source 的统计（每个 source 产出多少 card）

#### U3: Dogfood Report Center
- 实现 v1.4 W6（deferred）的 dogfood report 后端
- `GET /api/dogfood/report` — 结构化工作台使用报告
- 前端 DogfoodReportPage 或 HomePage 中的 section
- 报告内容：card 增长趋势、approval 率、graph density、search usage、import/export 统计

#### U4: Provider Readiness Center
- SetupPage 增强：provider status dashboard
- 基于 `provider_readiness.py` → Web API → UI
- 展示每个 provider 的 readiness 状态（fake_default / ready / blocked）
- 不展示 API key 值

#### U5: Cross-cutting UX Polish
- 页面间 navigation breadcrumb 一致性
- Loading/empty/error state 全覆盖审查
- i18n 覆盖审查（zh/en 完整性）
- 响应式布局审查（mobile/tablet/desktop）

#### U6: End-to-End Product Copy & Smoke
- 扩展 product copy tests 覆盖全部页面
- Browser smoke: 完整用户旅程
  1. Home → 看到 dashboard
  2. Import → 导入一篇 markdown → 成功
  3. Drafts → 查看草稿 → 确认内容
  4. Library → 浏览卡片 → 查看 graph/relations
  5. Wiki → 浏览 wiki → 查看 sections
  6. Search → 搜索 → 验证结果
  7. Export → 导出 zip → 验证内容
  8. Health → 查看健康报告

#### U7: Documentation Polish
- 更新 `docs/en/user-guide.md`
- 更新 `docs/en/getting-started.md`
- 更新 `docs/dev/architecture.md`
- 确保所有 implementation notes 索引在 README 中

#### U8: Release Notes & Changelog
- 生成 v2.0-v2.5 changelog
- 不 tag/release（硬红线）

### Acceptance Criteria

- [ ] HomePage dashboard 展示完整知识工作台状态
- [ ] Dogfood report API 可用
- [ ] Provider readiness 在 UI 中可见
- [ ] 完整用户旅程 smoke 通过
- [ ] 所有 gate 通过

### Tests

- `tests/test_web_product_copy.py` — 扩展覆盖
- `tests/test_dogfood_report.py` — 新
- `tests/test_provider_readiness_web.py` — 新（如不存在）

### Smoke Plan

- 完整 Browser MCP smoke: 8 步用户旅程

### Stop Conditions

- HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN
- 其他标准 hard-stop

### Next-stage Transition

v2.5 完成 → v2.0-v2.5 roadmap 交付完毕。所有 P1 单元交付。如无新 roadmap 输入，HARD_STOP_PRODUCT_DECISION。

---

## 全局硬约束（全阶段生效）

1. 不读取 `.env` 或 secrets
2. 不调用真实 LLM、Cubox、Upstage 或外部服务
3. 不处理真实私人资料
4. 不写真实 Obsidian vault
5. 不实现 mail/email/mail storage
6. 不做 RAG answering
7. 不做 embedding / vector DB
8. 不新增大型依赖（除非对应 spec 明确授权并解释必要性）
9. 不 tag/release
10. 不 force push
11. 不 auto approve
12. 不破坏 explicit approval / human_approved 语义

## Gate Evidence Rule（全阶段生效）

每个 gate 必须报告：exact command、timeout yes/no、real exit code、failure summary。

禁止：tail/head/truncated output、timeout 当 pass、无可见 exit code 当 pass、无证据说 pre-existing。

## Context Policy（全阶段生效）

- context ≥ 15%: 正常执行
- context < 15%: 不开大型新实现单元
- context < 10%: 只完成当前单元、跑 gate、写 handoff、commit/push
- context < 5%: 立即写 handoff、跑最小 gate、commit/push、HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN

## 外部技术启发（design inspiration only）

### GraphRAG
- 借鉴：structured graph data + unstructured document context、community hierarchy、community summaries、local/global search
- 不做：完整 GraphRAG、RAG answering、真实 LLM、embedding/vector DB
- MindForge 适配：deterministic community/topic layer、explainable context composer

### CodeGraph / CodexGraph
- 借鉴：pre-indexed local knowledge graph、structure-aware retrieval、multi-hop navigation
- MindForge 图类型：KnowledgeCard / SourceDocument / WikiSection / Tag / Concept / ApprovalState / ExportPackage / ImportSource
- 目标：让系统知道"知识为什么相关"和"从哪里来"

### Local-first Software
- 借鉴：用户拥有数据、可离线、本地优先、隐私、长期保存、可迁移
- MindForge 坚持：local-first personal knowledge workbench

### SQLite FTS5 / DuckDB FTS
- 借鉴：local lexical full-text search 绕开 embedding
- 优先：SearchIndexPort / RetrievalPort 边界设计
- 已有 ADR-001 决策（保持 BM25）

### Kuzu / Embedded Graph DB
- 借鉴：embedded property graph database 复杂图查询
- 已有 ADR-002 决策（保持 In-Memory）
- 仅作为 optional isolated spike

## 现有 ADR 参考

- `docs/adr/2026-05-24-001-retrieval-backend.md` — BM25 vs SQLite FTS5 vs DuckDB FTS（保持 BM25）
- `docs/adr/2026-05-24-002-kuzu-graph-backend.md` — In-Memory vs Kuzu（保持 In-Memory）
- v2.2/v2.3 的 spike 评估已和这两份 ADR 对齐，不推翻已有决策
