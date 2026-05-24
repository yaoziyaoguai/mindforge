---
title: MindForge v0.7–v1.0 Multi-Stage Roadmap
type: roadmap
status: active
date: 2026-05-24
parent: 2026-05-24-025-v0_6-knowledge-graph-retrieval-foundation-spec.md
supersedes: 2026-05-24-022-v0_6-next-phase-planning-review.md
---

# v0.7–v1.0: 从 Knowledge Graph Foundation 到 Knowledge Workbench

## 0. 路线总览

```
v0.6 (done)               v0.7                     v0.8                       v0.9                     v1.0
Knowledge Graph     →    Graph Quality      →    Lexical Retrieval      →    Local Graph Backend    →    Knowledge Workbench
& Retrieval               & Evidence               Foundation                  Spike (isolated)            Experience
Foundation                Hardening                (no embedding)              (Kuzu eval only)
```

### 核心设计原则（贯穿 v0.7–v1.0）

1. **Knowledge Workbench, not Search Engine** — 目标是个人知识工作台，不是另一个搜索页
2. **Deterministic & Explainable** — 所有关系、检索、推荐都必须可解释，无黑盒
3. **No RAG Answering, No Embedding, No Vector DB** — 始终以确定性规则 + lexical retrieval 为基础
4. **ai_draft / human_approved 不变** — AI 只创建草稿，人类显式审批
5. **Local & Lightweight** — 不引入大型生产依赖，新依赖必须在 spec 中明确授权
6. **Graph-First Navigation** — 图是知识导航的主界面，不是侧边栏的辅助视图

---

## 1. v0.7 — Graph Quality & Evidence Hardening

### 1.1 目标

修复和强化 v0.6 图/关系/发现上下文的质量、解释性和 gate evidence。重点不是新功能，而是让已有能力可信、可理解、可维护。

### 1.2 动机

v0.6 R1-R6 在 5 个 commit 中交付了完整的 Knowledge Graph & Retrieval Foundation，但快速迭代留下了质量债务：

- **Evidence 文本质量不足** — `_local_graph_edge_to_graph_edge()` 生成的 evidence 是 `"same_source: card_1 ↔ card_2"` 这种机器格式，不是用户可理解的解释
- **Relation reason 粒度不足** — 当前只按 EdgeType 分组，但同一个 `RELATED_BY_SOURCE` 下缺乏细分（same_source_document vs source_location_neighbor）
- **UI copy 未审计** — GraphNavigationPanel/GraphExplorer 的 relation 展示文案需要中文学习型说明优化
- **缺失测试** — 错误路径（无效 card_id、缺失参数、depth 越界）、API schema 边界验证、2-hop 确定性 golden fixture
- **Browser smoke 未执行** — R5/R6 的 graph-aware UI 和 discovery context API 通过了 npm build 和 pytest，但没有浏览器端到端验证
- **Gate evidence 规范化** — 上一轮 post-merge audit 发现 E501 误报问题，需要建立 gate evidence 规范

### 1.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | Evidence 文本质量升级 | 所有 relation evidence 对用户可读（中文场景），不再有 `↔` 机器格式 |
| G2 | Relation reason 细分 | same_source_document / shared_tag / same_wiki_section / source_location_neighbor 在 evidence 中可区分 |
| G3 | UI copy audit & polish | GraphNavigationPanel / GraphExplorer 文案 i18n 完整，relation 说明中文可理解 |
| G4 | 测试补全 | 错误路径测试、API schema 边界验证、2-hop golden fixture、relation evidence 内容验证 |
| G5 | Browser smoke | Graph-aware UI 和 discovery context API 浏览器端到端验证 |
| G6 | Gate evidence 规范 | 建立 gate evidence 审计规范，防止 E501 误报类问题再次发生 |

### 1.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | 新 API endpoint | v0.7 不新增 API，只强化已有 API 质量 |
| 2 | 新 UI 组件 | 不新增组件，只审计和优化已有组件 |
| 3 | 图算法升级 | 不修改 graph builder 核心算法 |
| 4 | 性能优化 | 不优化 graph 构建性能（当前规模足够） |
| 5 | 新依赖 | 不引入任何新依赖 |

### 1.5 Implementation Units

#### U1: Evidence Text Quality Upgrade

**Goal**: 所有 relation evidence 文本从机器格式升级为用户可理解的自然语言。

**Scope**:
- `graph_builder.py` `_local_graph_edge_to_graph_edge()`: evidence 从 `f"{ge.reason}: {center_id} ↔ {ge.target_id}"` 改为描述性文本
- `graph_builder.py` `_source_centered_graph()` / `_tag_centered_graph()`: evidence 格式统一
- 每条 evidence 包含: what relation + why + shared entity name
- 示例: 旧 `"same_source: card_1 ↔ card_2"` → 新 `"来自同一来源文档: reading-notes/ai-ml.md"`
- `discovery_context.py` `assemble_discovery_context()`: 所有卡片 ref 的 evidence 字段已由 graph builder 填充，确认证据链完整

**Files**: `src/mindforge/relations/graph_builder.py`, `src/mindforge/relations/discovery_context.py`

**Test scenarios**:
- evidence 文本包含共享实体名称（source path / tag name / section title）
- evidence 不包含 `↔` 机器格式
- evidence 不包含裸 `card_id`（除非必要）

#### U2: Relation Reason Granularity Audit

**Goal**: 确保每个 EdgeType 下的实际 reason 可细分追溯，不丢失确定性信息。

**Scope**:
- 审计 `_REASON_TO_EDGE_TYPE` 映射：`SAME_SOURCE` 和 `SOURCE_LOCATION_NEIGHBOR` 都映射到 `RELATED_BY_SOURCE`，丢失了细分信息
- 在 `RelationEvidence.detail` dict 中保留原始 `RelationReason`，供 UI 细分展示
- 确认 `compute_related_cards()` 返回的 `RelationReason` 完整传递到 edge evidence

**Files**: `src/mindforge/relations/graph_builder.py`, `src/mindforge/relations/graph_models.py` (detail 字段已存在，确认使用)

**Test scenarios**:
- SAME_SOURCE reason 的 edge 在 detail 中可区分于 SOURCE_LOCATION_NEIGHBOR
- SAME_REVIEW_BATCH reason 的 edge 不丢失来源信息

#### U3: Graph UI Copy Audit & Polish

**Goal**: GraphNavigationPanel / GraphExplorer / discovery UI 文案完整且中文可理解。

**Scope**:
- 审计 `web/src/lib/i18n.ts` 中所有 graph 相关 key 的 zh/en 文案
- 补充缺失的 i18n key（如有）
- 优化 edge type label 映射（`edgeTypeLabel()` 或类似函数），确保中文展示友好
- GraphNavigationPanel: 折叠组标题、evidence 展开文案、strength 指示器 tooltip
- GraphExplorer: 搜索 placeholder、空状态引导、错误状态文案

**Files**: `web/src/lib/i18n.ts`, `web/src/components/GraphNavigationPanel.tsx`, `web/src/components/GraphExplorer.tsx`

**Test scenarios**:
- `npm run build` 通过
- `python -m pytest tests/test_web_product_copy.py -q` 通过
- 所有 graph i18n key 有 zh/en 双值
- 无硬编码中英混用

#### U4: Test Gap Characterization & Closure

**Goal**: 补全 v0.6 关系/图/发现上下文的测试覆盖缺口。

**Scope**:
- **错误路径**: 无效 card_id（404）、缺失参数（400）、depth 越界（422 或 clamp）
- **API schema 边界**: edge response 中 evidence 字段非 null、reason 非空、strength 在 [0, 1]
- **2-hop golden fixture**: 已知卡片集的 2-hop graph 结构验证（固定输入 → 固定输出）
- **Discovery context 内容验证**: evidence 文本不包含机器格式、relation_reason 有意义
- **Edge case**: 空卡片集、单卡片、重复卡片 ID

**Files**: `tests/relations/test_graph_api.py`, `tests/relations/test_discovery_context.py`, `tests/relations/test_graph_builder.py` (按需新增)

**Test scenarios**:
- 每个新增测试类别至少 2 个用例
- 现有 84 个测试全部通过
- 新增测试数 ≥ 10

#### U5: Browser Smoke — Graph-aware UI

**Goal**: 浏览器端到端验证 GraphNavigationPanel、GraphExplorer、discovery context API。

**Scope**:
- 启动 Web server + 准备 fake dogfood 数据 (`scripts/fake_dogfood.sh`)
- 打开 Library 页面，验证 GraphExplorer 入口可见
- 打开卡片详情，验证 GraphNavigationPanel 渲染、按 EdgeType 分组、evidence 展示
- 验证 2-hop 切换按钮功能
- 打开 Wiki 页面，验证 section graph nav
- 检查 console error、network 4xx/5xx
- 记录发现（P0-P4），P0/P1 立即修复

**Files**: 无代码改动（纯 browser smoke），可能需要修复 smoke 发现的问题

**Test scenarios**: 按 smoke checklist 逐项验证

### 1.6 Test Plan

| Test File | Existing | v0.7 Target |
|-----------|---------|-------------|
| `tests/relations/test_graph_models.py` | ~5 | +3 (evidence content, detail field) |
| `tests/relations/test_graph_builder.py` | ~10 | +5 (2-hop golden, edge cases, evidence format) |
| `tests/relations/test_discovery_context.py` | 10 | +3 (evidence content, deterministic, edge cases) |
| `tests/relations/test_graph_api.py` | 14 | +5 (error paths, schema boundaries) |

### 1.7 Gate Matrix

| Unit | ruff F+E | pytest (relations) | pytest (full) | pytest (product copy) | npm build | git diff --check | browser smoke |
|------|---------|-------------------|---------------|----------------------|-----------|-----------------|---------------|
| U1 Evidence Text | ✓ | ✓ | ✓ | — | — | ✓ | — |
| U2 Reason Granularity | ✓ | ✓ | ✓ | — | — | ✓ | — |
| U3 UI Copy | ✓ | — | — | ✓ | ✓ | ✓ | ✓ |
| U4 Test Closure | ✓ | ✓ | ✓ | — | — | ✓ | — |
| U5 Browser Smoke | — | — | — | — | — | — | ✓ |

### 1.8 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| 需要新依赖 | HARD_STOP_LARGE_DEPENDENCY |
| 需要修改 graph 核心算法 | HARD_STOP_PRODUCT_DECISION |
| P0/P1 smoke 发现无法在 2 轮回退内关闭 | HARD_STOP_P0_P1_RETRY_EXCEEDED |
| Context < 5% | HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN |

---

## 2. v0.8 — Lexical Retrieval Foundation (No Embedding)

### 2.1 目标

调研并实现不依赖 embedding 的本地全文检索增强。当前 BM25 实现（`lexical_index.py` / `recall_service.py`）工作正常，v0.8 的目标不是替换它，而是评估和实验更高效的 local FTS 方案。

### 2.2 动机

- 当前 BM25 是纯 Python 实现，1000+ 卡片时索引构建和查询延迟需要测量
- SQLite FTS5 是 Python 标准库自带（`sqlite3` 模块），零额外依赖
- SQLite FTS5 提供成熟的 BM25/OKAPI 评分、前缀查询、phrase query、snippet 生成
- 可以持久化索引文件，避免每次启动重建索引
- 不做 embedding/vector DB — 这是硬红线

### 2.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | FTS 技术调研 | 输出 SQLite FTS5 / DuckDB FTS 与当前 BM25 的对比分析 |
| G2 | RetrievalPort abstraction | 定义抽象检索接口，解耦 BM25 实现与 recall API |
| G3 | SQLite FTS5 spike | 在隔离分支实验 SQLite FTS5 全文检索 |
| G4 | Performance benchmark | 100/500/1000 卡片的索引构建时间、查询延迟、召回质量对比 |
| G5 | ADR 文档 | 输出 Architecture Decision Record：是否采用 FTS5、如何迁移、风险 |

### 2.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | Embedding / semantic search | 硬红线 |
| 2 | Elasticsearch / Meilisearch | 外部服务依赖 |
| 3 | 替换现有 BM25（默认） | 除非 ADR 明确授权，BM25 保持默认 |
| 4 | Vector DB | 硬红线 |
| 5 | DuckDB 作为生产依赖 | 仅调研和 spike |

### 2.5 Implementation Units

#### U1: RetrievalPort Abstraction

**Goal**: 定义 `RetrievalPort` 抽象接口，解耦检索实现与 API 层。

**Scope**:
- 定义 `RetrievalPort` Protocol/ABC: `search(query, limit, filters) → list[SearchHit]`
- 定义 `SearchHit` frozen dataclass（统一 BM25 / FTS5 返回格式）
- 当前 `Bm25RetrievalEngine` 实现 `RetrievalPort`
- `recall_service.py` 依赖 `RetrievalPort` 而非具体实现
- `SearchIndexPort` 可选：索引构建/更新接口

**Files**: `src/mindforge/retrieval/retrieval_port.py` (NEW), `src/mindforge/retrieval/bm25_engine.py` (extract), `src/mindforge/recall/recall_service.py` (refactor to use port)

**Test scenarios**:
- BM25 engine 通过 RetrievalPort 接口返回正确结果
- 替换 engine 不需要修改 recall_service.py

#### U2: SQLite FTS5 Research & Spike

**Goal**: 在隔离分支实验 SQLite FTS5 全文检索。

**Scope**:
- 创建 `spike/sqlite-fts5/` 分支（不合入 main）
- 实现 `SqliteFts5Engine(RetrievalPort)`: 建表、插入文档、BM25 查询、snippet 生成
- 支持中文分词处理（SQLite FTS5 默认按字符切分，需评估中文效果）
- 性能对比：索引构建时间、查询延迟、内存占用 vs 纯 Python BM25
- 召回质量对比：相同 query 的 top-10 结果 overlap 率

**Files**: spike branch only (NOT merged to main)

**Test scenarios**:
- FTS5 索引创建/查询基本功能
- 中文文本召回可用性评估
- 性能 benchmark 数据

#### U3: Retrieval Architecture Decision Record

**Goal**: 基于调研和 spike 结果，编写 ADR。

**Scope**:
- 对比方案: 纯 Python BM25（现状）vs SQLite FTS5 vs DuckDB FTS
- 评估维度: 性能、中文支持、维护成本、依赖复杂度、持久化
- 明确决策: 采用 / 不采用 / 条件采用
- 如果采用: 迁移路径、fallback 策略、测试策略
- 如果不采用: 现有 BM25 的优化方向

**Files**: `docs/adr/2026-05-24-001-retrieval-backend.md` (NEW)

### 2.6 Gate Matrix

| Unit | ruff F+E | pytest | git diff --check |
|------|---------|--------|-----------------|
| U1 RetrievalPort | ✓ | ✓ | ✓ |
| U2 FTS5 Spike | — | — | — (spike branch) |
| U3 ADR | — | — | ✓ (docs only) |

### 2.7 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| DuckDB 被提议为生产依赖 | HARD_STOP_LARGE_DEPENDENCY |
| Embedding/vector DB 被引入 | HARD_STOP_RAG_EMBEDDING |
| 需要真实 LLM 做 relevance 评分 | HARD_STOP_REAL_LLM |

---

## 3. v0.9 — Local Graph Backend Spike (Isolated Only)

### 3.1 目标

在严格隔离条件下实验 Kuzu 嵌入式图数据库作为 graph backend 的可行性。不合入 main 直到后续 spec 明确授权。

### 3.2 动机

- 当前 `DeterministicGraphBuilder` 是纯 in-memory Python 实现，100-200 卡片规模表现良好
- 如果卡片数增长到 1000+，每次请求重建索引和 2-hop 遍历的成本需要评估
- Kuzu 是 embeddable property graph database（C++/Python），支持 Cypher-like query、ACID、零外部依赖
- 但引入 Kuzu 意味着：新大型编译依赖（C++ 扩展）、新查询语言学习成本、schema 映射维护、调试复杂度
- v0.9 的 spike 严格隔离——只在 spike 分支实验，评估后写 ADR，**不乱入 main**

### 3.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | Kuzu spike | 在隔离分支实现基本的 node/edge 导入和 Cypher 查询 |
| G2 | GraphPort 适配评估 | 评估 Kuzu backend 实现 GraphPort 的工作量和复杂度 |
| G3 | 性能对比 | 与 DeterministicGraphBuilder 对比：图构建、2-hop 查询、路径查找 |
| G4 | ADR 文档 | 是否引入 Kuzu、何时引入、风险和替代方案 |

### 3.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | Kuzu 合入 main | 严格隔离，不合入 |
| 2 | Kuzu 作为默认 graph backend | 仅评估 |
| 3 | 数据迁移到 Kuzu | 仅 spike，不涉及真实数据 |
| 4 | 替换 DeterministicGraphBuilder | 不替换，仅评估替代方案 |

### 3.5 Implementation Units

#### U1: Kuzu Spike

**Goal**: 在 `spike/kuzu-graph-backend/` 分支实验 Kuzu。

**Scope**:
- 安装 `kuzu` Python package（spike 分支内）
- 创建 node tables (Card, Source, WikiSection, Tag) 和 edge tables
- 从 CardSummary 数据导入节点和边
- 实现基本 Cypher 查询: 1-hop neighbors、2-hop path、shared-tag cards
- 与 GraphPort interface 对照，评估适配工作量

**Files**: spike branch only

#### U2: Kuzu ADR

**Goal**: 编写 Kuzu graph backend Architecture Decision Record。

**Scope**:
- Kuzu 优势: 嵌入式图查询、Cypher 支持、持久化、无外部 server
- Kuzu 代价: C++ 编译依赖、新查询语言、schema 维护、调试复杂度
- 当前 in-memory 方案是否够用？什么时候需要 Kuzu？
- 决策: 暂不引入 / 条件引入 / 立即引入
- 如果条件引入: 触发条件是什么（卡片数 > 500？查询延迟 > 500ms？）

**Files**: `docs/adr/2026-05-24-002-kuzu-graph-backend.md` (NEW)

### 3.6 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| Kuzu 被提议合入 main（未经 spec 授权） | HARD_STOP_LARGE_DEPENDENCY |
| Kuzu 替代 DeterministicGraphBuilder（未经授权） | HARD_STOP_PRODUCT_DECISION |

---

## 4. v1.0 — Knowledge Workbench Experience

### 4.1 目标

把 v0.6-v0.9 的 graph/retrieval/discovery/quality 能力整合为真正的个人知识工作台体验。用户打开 MindForge 不是来"搜索卡片"，而是来"在知识中思考和发现"。

### 4.2 设计愿景

v1.0 的 MindForge 不是一个工具集合，而是一个 coherent 的知识工作台：

- **关系地图**: 不只是 RelatedCards 侧边栏，而是可交互的知识关系地图（结构化列表 + 跳转，非 canvas）
- **来源溯源链**: 从任意卡片追溯到其 source document、同源卡片、审批历史
- **可见的审核-批准循环**: 不再隐藏 ai_draft → human_approved 的状态转换，而是作为知识成长的可视化叙事
- **知识质量仪表盘**: Card Quality / Wiki Quality 从后台报告变为前台仪表盘
- **本地 Dogfood 工作区**: 一键启动 fake dogfood，验证完整流程
- **安全导出**: 人类可读的审查报告、知识摘要
- **不破坏安全模型**: AI 只创建 ai_draft，human_approved 需要显式人类批准

### 4.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | Relationship Map | 交互式知识关系导航，沿关系链探索不迷路 |
| G2 | Source Provenance Trail | 从卡片追溯到 sources，看完整来源链 |
| G3 | Review-to-Approve Visibility | ai_draft → human_approved 的完整状态转换可视化 |
| G4 | Knowledge Quality Dashboard | Card/Wiki Quality 报告作为前台仪表盘，不是一个后台脚本 |
| G5 | Local Dogfood Workspace | 一键 fake dogfood 启动，验证完整工作流 |
| G6 | Safe Export | 人类可读的知识审查报告导出 |

### 4.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | Force-directed graph canvas (d3/cytoscape) | 大图可视化不是个人知识工作台的核心 |
| 2 | 实时协作 | 个人工具，不做多用户 |
| 3 | 移动端 | 桌面优先 |
| 4 | 自动审批 | 永远不做 |
| 5 | RAG answering / LLM summary | 硬红线 |

### 4.5 Draft Implementation Units（详细 spec 在 v0.9 后制定）

| Unit | Capability | Priority |
|------|-----------|----------|
| W1 | Relationship Map — 结构化 2-hop 导航面板升级 | P0 |
| W2 | Source Provenance Trail — Card → Source → Related Cards 链条视图 | P0 |
| W3 | Review Pipeline Visibility — ai_draft → human_approved 时间线 | P1 |
| W4 | Knowledge Quality Dashboard — Card/Wiki Quality 仪表盘 | P1 |
| W5 | Local Dogfood Workspace — 一键启动脚本 + browser smoke | P1 |
| W6 | Safe Export — Markdown/JSON 审查报告导出 | P2 |
| W7 | Workbench UI Polish — 统一的导航、空状态引导、loading skeleton | P1 |

### 4.6 v1.0 详细 SPEC

v1.0 的详细 SPEC 将在 v0.9 完成后制定（`docs/specs/2026-05-XX-v1_0-knowledge-workbench-experience-spec.md`），基于 v0.7-v0.9 的产出和发现进行调整。

---

## 5. External Technology Inspirations

以下技术为设计启发来源，**不作为直接依赖引入**。

### 5.1 Microsoft GraphRAG

- **启发**: graph extraction → community hierarchy → community summaries → local/global search
- **MindForge 吸收**: 社区检测概念（共享 source/tag/section 的卡片群作为"知识社区"）、local search（1-hop/2-hop graph context）、global search（wiki section 作为 knowledge cluster 入口）
- **不做**: LLM extraction、LLM summarization、RAG answering

### 5.2 SQLite FTS5

- **启发**: 零依赖全文检索、BM25 评分、持久化索引、snippet 生成
- **MindForge 评估**: 替换纯 Python BM25 的候选方案（v0.8 spike）
- **不做**: 盲目替换现有工作正常的 BM25

### 5.3 Kuzu Embedded Graph Database

- **启发**: Embedded property graph DB、Cypher query、ACID、零 server 依赖
- **MindForge 评估**: 大规模卡片时的 graph backend 候选（v0.9 spike）
- **不做**: 在评估完成前引入为生产依赖

### 5.4 LightRAG / CodexGraph

- **启发**: Document-as-graph indexing、graph-first exploration UI、structure-aware retrieval
- **MindForge 吸收**: 卡片即图节点、wiki section 即 cluster、检索时利用 graph structure
- **不做**: 服务器/Web/LLM/embedding stack

---

## 6. Self-Review Checklist

对照全局硬红线自审（每次进入新 version 前必须重审）：

- [ ] 是否退化成普通搜索页？ — **否**。v0.7-v1.0 始终坚持 graph-first discovery
- [ ] 是否偷偷变成 RAG answering？ — **否**。所有 context assembly 明确标记为 non-RAG
- [ ] 是否偷偷引入 embedding/vector DB？ — **否**。v0.8 明确限定 SQLite FTS5（lexical，非 semantic）
- [ ] 是否需要真实 LLM？ — **否**。fake provider 始终为默认
- [ ] 是否破坏 ai_draft / human_approved 语义？ — **否**。v1.0 W3 增强可见性但不改变语义
- [ ] 是否引入大型依赖？ — **否**。v0.8/v0.9 spike 严格隔离，不合入 main
- [ ] 是否让 Autopilot 每阶段停下来？ — **否**。每个 version 有明确的 units 和 gate，支持连续自动推进
- [ ] 是否给了足够材料支撑连续几小时自动推进？ — **是**。v0.7 5 个 units + v0.8 3 个 units + v0.9 2 个 units + 测试/gate/smoke 全部定义
- [ ] 每个阶段是否有 clear goals / non-goals / tests / smoke / stop conditions？ — **是**

---

## 7. References

- v0.6 Research: `docs/specs/2026-05-24-024-v0_6-knowledge-graph-retrieval-foundation-research.md`
- v0.6 SPEC: `docs/specs/2026-05-24-025-v0_6-knowledge-graph-retrieval-foundation-spec.md`
- v0.6 Post-Merge Audit: `docs/implementation-notes/2026-05-24-030-v0_6-post-merge-gate-audit.md`
- v0.6 R3-R6 Implementation Notes: `docs/implementation-notes/2026-05-24-026~029-*.md`
- Engineering Workflow: `docs/dev/engineering-workflow.md`
- Autopilot: `.claude/commands/mf-autopilot.md`
- Copy Policy: `docs/dev/copy-policy.md`
