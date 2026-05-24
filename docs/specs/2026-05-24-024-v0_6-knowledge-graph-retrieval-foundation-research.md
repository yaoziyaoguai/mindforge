---
title: MindForge v0.6 — Knowledge Graph & Retrieval Foundation Research
type: research
status: draft
date: 2026-05-24
roadmap: V0_6_KNOWLEDGE_GRAPH_RETRIEVAL_FOUNDATION
parent: 2026-05-24-022-v0_6-next-phase-planning-review.md
supersedes: 2026-05-24-023-v0_6-search-discovery-spec.md
---

# v0.6 Knowledge Graph & Retrieval Foundation — Research & Architecture Review

## 1. 为什么不继续 Search & Discovery (Direction C)

Search & Discovery (S1-S5: 搜索过滤/分组/排序/Wiki 搜索/UX Polish) 是可用但过于常规的候选方向。它的本质问题是：

1. **仍是 card-first, 不是 graph-first** — 搜索过滤/分组/排序只是让 Library 列表更易浏览，但没有改变知识导航的根本范式。用户仍然在"列表里找卡片"，而不是"沿关系链探索知识"。
2. **已有基础设施未被充分利用** — v0.4 已经建立了完整的确定性关系计算引擎（`compute_related_cards`、`build_card_centered_graph`、`build_wiki_section_centered_graph`），但 RelationReason 枚举、GraphNode/GraphEdge 模型、LocalGraph 结构只被用于卡片详情页的侧边栏展示。它们完全可以成为知识导航的主界面。
3. **搜索能力可以被 graph-aware discovery 内置** — 过滤/分组/排序这些能力不应该是 v0.6 的主线，而应该是 Graph-aware Discovery UI 的后续内置子能力。当用户沿 graph 探索时，过滤和排序自然内建于导航交互中。

**处理方式**: Direction C 的 Search & Discovery spec 标记为 parked/superseded，不删除。其 S1-S5 能力可以作为 v0.6 graph-aware UI 的子能力在后续吸收。

## 2. 外部技术启发（Design Inspiration Only, No Direct Dependency）

### 2.1 Microsoft GraphRAG

**关键概念吸收**:
- **Graph Extraction**: 从非结构化文本中提取 entities + relationships 形成知识图谱。MindForge 已有确定性来源（Card metadata、Wiki sections、Tags、Source documents），不需要 LLM extraction。
- **Community Hierarchy**: 在 graph 中检测社区结构（Leiden algorithm），生成多级社区层级。MindForge 可以吸收"社区 = 共享 source / tag / wiki section 的卡片群"这个概念，用已有 metadata 做确定性分组。
- **Community Summaries**: 为每个社区生成摘要描述。MindForge 可以不依赖 LLM 生成摘要，而是用 wiki section 标题 + 卡片统计 + 共享 tag 作为"社区描述"。
- **Local/Global Search**: GraphRAG 的 local search（基于实体的邻居信息回答）和 global search（基于社区摘要回答）提供了 graph-aware retrieval 的两种范式。MindForge 可吸收其结构但不同实现——local = 当前卡片的 1-hop/2-hop graph context；global = wiki section 作为 knowledge cluster 的入口。

**不做的事**: 完整 GraphRAG pipeline（LLM extraction、community summarization via LLM、RAG answering from graph context）。MindForge 不做 RAG answering。

### 2.2 LightRAG

**关键概念吸收**:
- **Document Indexing into Graph**: LightRAG 将文档索引为 graph 结构而非 chunk embedding。这与 MindForge 的 deterministic approach 精神一致——卡片本身就是 graph nodes，wiki sections 是 cluster nodes，来源文档是 root nodes。
- **Knowledge Graph Exploration UI**: LightRAG 的查询界面让用户通过 graph 探索而非仅关键词搜索。这是 MindForge v0.6 的 UI 方向——graph-first discovery 而非 search-first filtering。
- **RAG Query UI product form reference**: LightRAG 的产品形态（graph + retrieval + explanation）可作为 MindForge"Discovery Context Composer"的参考——但 MindForge 不做 RAG answering，只做 retrieval context assembly。

**不做的事**: LightRAG 的 server/Web/LLM/embedding/RAG stack。MindForge 不引入其任何代码或依赖。

### 2.3 CodeGraph / CodexGraph

**关键概念吸收**:
- **Pre-indexed Local Knowledge Graph**: CodexGraph 将代码符号图预索引为可查询的 graph。MindForge 可以吸收"预索引"概念——将卡片关系图在 scan/approve 时就增量构建，而非每次请求时重新计算。
- **Graph Schema**: 明确定义的 node types 和 edge types schema。MindForge 需要类似的明确 schema，但 node types 是 Card/SourceDocument/WikiSection/Tag/Concept，不是代码符号。
- **Structure-Aware Retrieval**: 检索时利用 graph 结构（邻居、路径、社区）来增强结果。MindForge 的 discovery context composer 应该 graph-structure-aware。
- **Multi-hop Reasoning/Navigation**: 支持沿 graph 多跳导航。MindForge 当前只有 1-hop，v0.6 可扩展到 2-hop 并支持路径追溯。

**迁移到 MindForge 的关键差异**: 不是代码符号图，而是 Card/SourceDocument/WikiSection/Tag/Concept/ApprovalState graph。导航目标不是"理解代码结构"，而是"发现相关知识"。

### 2.4 Kuzu — Embedded Property Graph Database

**候选分析**:
- Kuzu 是 embeddable property graph database (C++/Python)，支持 Cypher-like query language、结构化 property graph、ACID 事务、无外部 server 依赖。
- MindForge 当前用 in-memory dict 构建关系索引。如果卡片数增长到 1000+，每次请求重新构建索引的成本会上升。
- Kuzu 可以作为 future spike 评估，但**当前不得直接引入为生产依赖**。原因：(a) 新大型依赖需要专门 spec 授权；(b) in-memory deterministic computation 在 v0.6 的卡片规模下仍然足够；(c) 引入 graph DB 需要在 abstraction boundary (GraphPort/GraphRepository) 下进行，不能直接散落到业务代码中。

**使用策略**: R7 Optional Spike 可在 isolated branch 中实验 Kuzu，但不合入 main 直到后续 spec 明确授权。

### 2.5 DuckDB FTS / SQLite FTS5 — Full-Text Retrieval Candidates

**候选分析**:
- DuckDB FTS extension 和 SQLite FTS5 提供 BM25 级别的全文检索，可以作为现有纯 Python BM25 的替换或补充。
- 优势：更快的索引构建、成熟的 FTS 引擎、可持久化索引文件。
- MindForge 当前 BM25 实现（`lexical_index.py`/`recall_service.py`）已经工作正常，替换引擎的收益有限。

**使用策略**: 优先基于现有 BM25 / lexical / deterministic relation。DuckDB/SQLite FTS 作为未来优化候选，不作为 v0.6 主线。

## 3. v0.6 核心判断

### 3.1 架构判断

| 问题 | 判断 | 原因 |
|------|------|------|
| Embedding 是否第一步必需？ | **否** | 确定性关系（same source、shared tag、same wiki section、title/body term overlap）在 v0.4 已证明足够构建有意义的图 |
| Graph DB 是否第一步必需？ | **否** | 先定义 GraphPort/GraphRepository interface 作为抽象边界，默认实现用 in-memory deterministic computation（复用现有代码） |
| 是否先做 deterministic graph + lexical retrieval？ | **是** | 这些已有基础设施。v0.6 的工作是升级它们的角色——从"卡片详情的 side feature"到"知识导航的 main surface" |
| Kuzu/DuckDB/SQLite FTS 如何处理？ | isolated spike | R7 在隔离分支实验，不合入 main 直到后续 spec 授权 |
| 是否做 RAG answering？ | **否** | v0.6 只做 retrieval context composer / discovery context composer，不做任何形式的 question answering |

### 3.2 当前基础设施评估

v0.4 已有的关系基础设施：

| 组件 | 位置 | 当前角色 | v0.6 升级 |
|------|------|---------|----------|
| `compute_related_cards()` | `relations/related_cards.py` | card detail 侧边栏数据源 | graph edge 构建的基础引擎 |
| `build_card_centered_graph()` | `relations/local_graph.py` | 1-hop graph preview | graph navigation 的入口点，扩展到 2-hop |
| `build_wiki_section_centered_graph()` | `relations/local_graph.py` | 仅 API 返回 | Wiki 页面的 graph navigation 入口 |
| `compute_wiki_related_sections()` | `wiki_service.py` | section 间 Jaccard link | graph 中的 section-section edge |
| `filter_cards()` / `sort_cards()` | `cards.py` | Library 页面的过滤 | 被 graph-aware discovery 吸收为内置能力 |
| BM25 recall | `recall_service.py` | `/api/recall` 端点 | graph-aware retrieval 的 lexical 组件 |

## 4. MindForge 图模型初稿

### 4.1 Node Types

| Node | 数据来源 | 唯一标识 | 属性 |
|------|---------|---------|------|
| **KnowledgeCard** | `CardSummary` from vault | `card_id` | title, status, quality_score, tags, source_id, created_at, approved_at |
| **SourceDocument** | `source_id` from CardSummary | `source_id` | source_path, source_type, source_title |
| **WikiSection** | `WikiSectionView` from wiki | `section_id` (anchor) | title, level, card_count |
| **Tag** | `tags` from CardSummary | tag name (normalized) | card_count |
| **ConceptCandidate** | title/body term extraction (deterministic) | normalized term | card_count, source_sections |

**不在 v0.6 scope**:
- ProjectContextCandidate — 仅在 project/track management 已存在时考虑
- ApprovalState — 当前 approval state 已经有独立 UI，不需要被建模为 graph node

### 4.2 Edge Types

| Edge | 来源 | 确定性 | Evidence |
|------|------|--------|----------|
| `DERIVED_FROM` | Card `source_id` → SourceDocument | ✅ 确定性 | card.source_id == source.id |
| `MENTIONS` | Card body references another card/section | ✅ 如果显式引用 | `[[wikilink]]` 或显式 ID 引用 |
| `SHARES_TAG` | 两卡共享同一 tag | ✅ | tag in card_a.tags ∩ card_b.tags |
| `RELATED_BY_SOURCE` | 两卡来自同一 source | ✅ | card_a.source_id == card_b.source_id |
| `RELATED_BY_WIKI_SECTION` | 两卡属于同一 wiki section | ✅ | section.title in card_a.wiki_sections ∩ card_b.wiki_sections |
| `SIMILAR_TITLE_OR_TERM` | 标题或关键术语 overlap | ⚠️ 需阈值 | Jaccard(title_tokens) > threshold |
| `APPROVAL_STATE_OF` | Draft → Approved 卡片版本关系 | ✅ | card.status 关系 |
| `LINKS_TO` | 卡片 → WikiSection（卡片被 section 引用） | ✅ | card in section.card_refs |
| `DUPLICATES_OR_CONTRADICTS` | Title/body 高 overlap | ⚠️ 需确定性证据 | >0.8 title similarity + same source |

## 5. Relation Reason / Evidence 设计

每条边必须携带可解释的 `reason` + `evidence`，不可有"黑盒相似度"。

### 5.1 Reason Catalog

| reason | evidence 格式 | 确定性级别 |
|--------|-------------|-----------|
| `same_source_document` | `"source: {source_path}"` | deterministic |
| `shared_tag` | `"tag: {tag_name}"` | deterministic |
| `same_wiki_section` | `"section: {section_title}"` | deterministic |
| `title_term_overlap` | `"terms: [{shared_terms}], score: {jaccard}"` | threshold-based |
| `body_term_overlap` | `"key_terms: [{shared_terms}], sections: [{section_names}]"` | threshold-based |
| `existing_related_section` | `"wiki_section: {title}, overlap: {count} cards"` | deterministic (Jaccard) |
| `approval_state_relation` | `"draft → approved: {card_id}"` | deterministic |
| `manually_confirmed_future_only` | `"manual: confirmed by user"` | future |

### 5.2 Evidence 展示规则

- 每条边在 API 中必须返回 `reason` (枚举值) + `evidence` (人类可读字符串)
- 前端可据此展示 "为什么相关": "同一来源: reading-notes/ai-ml.md"、"共享标签: #llm"、"同一 Wiki Section: LLM 基础"、"标题重叠: 共享术语 [transformer, attention], 相似度 0.6"
- 不可展示为 "相关度 85%" 这种无解释的数字

## 6. v0.6 推荐 Unit Plan

### R1 — External Research & Repo Fit Review (本文档)

**产出**: 本 research 文档 (`docs/specs/2026-05-24-024-v0_6-knowledge-graph-retrieval-foundation-research.md`)

### R2 — MindForge Graph Domain Model SPEC

**产出**: 正式 v0.6 SPEC (`docs/specs/2026-05-24-025-v0_6-knowledge-graph-retrieval-foundation-spec.md`)

**内容**: graph domain model 定稿、relation evidence model、GraphPort/GraphRepository interface 设计、API/UI boundaries、R3-R7 的详细 scope

### R3 — Deterministic Relationship Builder

**目标**: 将现有 `compute_related_cards()` + `build_card_centered_graph()` 重构为统一的 `GraphBuilder`，支持增量构建和 2-hop 扩展。

**Scope**:
- 定义 `GraphPort` interface（抽象 graph 构建和查询）
- 实现 `DeterministicGraphBuilder`（基于现有 in-memory computation）
- 支持 `build_graph(center_id, *, depth=2)` — 2-hop graph
- 每条 edge 附带 `RelationEvidence`
- 增量更新：卡片 approve 后只更新受影响节点的边

**Files**: `src/mindforge/relations/graph_port.py` (new), `src/mindforge/relations/graph_builder.py` (new), `src/mindforge/relations/graph_models.py` (new)

### R4 — Explainable Relationship API

**目标**: 新增 graph-first API endpoints，返回可解释的关系数据。

**Scope**:
- `GET /api/graph/node?ref={card_id}&depth=2` — 以卡片为中心的 2-hop 图
- `GET /api/graph/explore?node_type={type}&node_id={id}` — 从任意节点类型出发的图探索
- `GET /api/graph/edge?source={id}&target={id}` — 两节点间的边详情（所有 reason + evidence）
- 响应中每个边包含 `reason` + `evidence` + `strength`

**Files**: `src/mindforge_web/routers/graph.py` (new), `src/mindforge_web/services/web_facade.py` (extend)

### R5 — Graph-aware Card / Wiki / Library UI

**目标**: 前端从 card-first 升级为 graph-first discovery。

**Scope**:
- GraphNavigationPanel: 替代简单 RelatedCards 列表，按 relation type 分组 + 可展开 evidence
- 2-hop graph 可视化（非 canvas，用结构化分组列表 + 跳转链接）
- Wiki 页面 section 间 graph navigation（利用已有 `compute_wiki_related_sections()`）
- Library 页面新增 "Graph Explorer" 入口（从任意卡片出发探索关系网络）

**Files**: `web/src/components/GraphNavigationPanel.tsx` (new), `web/src/pages/LibraryPage.tsx` (extend), `web/src/pages/WikiPage.tsx` (extend)

### R6 — Retrieval Context Composer (Non-RAG)

**目标**: 为 recall/discovery 提供 graph-aware context assembly，但不做 RAG answering。

**Scope**:
- `DiscoveryContext`: 给定 query/card_id，返回 (1) 直接匹配的卡片, (2) 1-hop 邻居卡片, (3) 所属 wiki sections, (4) shared tags/sources 的聚合视图
- `assemble_discovery_context(query_or_card_id)` — 确定性组装
- 增强 `/api/recall` 响应：在 BM25 结果之上附加 graph context
- **不做**: question answering、LLM summarization、RAG response generation

**Files**: `src/mindforge/relations/discovery_context.py` (new), `src/mindforge_web/routers/recall.py` (extend)

### R7 — Optional Local Graph Backend Spike

**目标**: 在隔离分支中实验 Kuzu / SQLite FTS / DuckDB FTS 作为潜在 graph backend。

**Scope**:
- 在 `spike/kuzu-graph-backend/` 分支中实验 Kuzu embeddable graph DB
- 在 `spike/fts-backend/` 分支中实验 SQLite FTS5 / DuckDB FTS
- 编写 spike report: 性能对比、集成复杂度、schema mapping
- **不合入 main**，除非后续 spec 明确授权

**Files**: spike branches only (not committed to main)

## 7. Non-Goals

| # | Non-Goal | 原因 |
|---|---------|------|
| 1 | RAG answering | v0.6 只做 retrieval context assembly，不做回答生成 |
| 2 | Embedding / semantic similarity | 确定性关系 + lexical retrieval 足够 |
| 3 | Vector DB | 无 embedding，无 vector DB 需求 |
| 4 | 真实 LLM 调用 | fake provider 始终为默认安全路径 |
| 5 | 真实 Cubox / Upstage | 不涉及外部服务 |
| 6 | 处理私人资料 | 不读取用户私人数据 |
| 7 | 写真实 Obsidian vault | 不修改外部文件 |
| 8 | mail / email / mail storage | 不涉及 |
| 9 | Auto approve | 不改变审批语义 |
| 10 | 破坏 human_approved 语义 | ai_draft vs human_approved 界限不变 |
| 11 | 大型依赖（默认） | Kuzu/DuckDB 仅在 R7 spike 隔离实验 |
| 12 | 生产 Kuzu/DuckDB 依赖 | 后续 spec 明确授权后才可合入 |
| 13 | Graph force-directed canvas 可视化 | 不做 d3/cytoscape 大图 |
| 14 | Full global graph | 始终以节点为中心，不做全局毛线球 |

## 8. 自审 Checkpoint

- [ ] 是否偷偷变成 RAG？ — 否。R6 明确标记为 "Retrieval Context Composer, non-RAG"，不做 answering
- [ ] 是否偷偷引入 embedding / vector DB？ — 否。所有 relation 基于确定性规则
- [ ] 是否需要真实 LLM？ — 否。graph 构建和检索都是 deterministic
- [ ] 是否破坏 ai_draft / human_approved 语义？ — 否。graph 只读已有 metadata，不修改卡片状态
- [ ] 是否引入大型依赖？ — 否。R7 是 isolated spike，不合入 main
- [ ] 是否只是普通搜索页换皮？ — 否。graph-first discovery 是范式转变，不是 UI 换皮
- [ ] 是否每条 relation 都可解释？ — 是。每条边有 `reason` + `evidence`
- [ ] 是否能从已有本地数据 deterministic 构建？ — 是。cards + wiki sections + tags + sources 全部来自本地 vault
- [ ] 是否能让 Auto Run 后续自动执行多 unit？ — 是。R3-R6 有清晰的依赖链和 scope 边界
