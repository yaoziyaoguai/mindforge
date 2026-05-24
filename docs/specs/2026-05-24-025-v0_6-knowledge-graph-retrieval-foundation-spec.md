---
title: MindForge v0.6 — Knowledge Graph & Retrieval Foundation Spec
type: feat
status: spec
date: 2026-05-24
roadmap: V0_6_KNOWLEDGE_GRAPH_RETRIEVAL_FOUNDATION
parent: 2026-05-24-024-v0_6-knowledge-graph-retrieval-foundation-research.md
supersedes: 2026-05-24-023-v0_6-search-discovery-spec.md
---

# v0.6: Knowledge Graph & Retrieval Foundation

## 1. Background

v0.4 已经建立了完整的确定性关系计算引擎：`compute_related_cards()`、`build_card_centered_graph()`、`build_wiki_section_centered_graph()`。但关系数据只被用于卡片详情页的侧边栏展示（RelatedCardsPanel、LocalGraphPreview），不是知识导航的主界面。

v0.6 的核心命题：将 graph 从"卡片详情的 side feature"升级为"知识导航的 main surface"。建立轻量、本地、可解释、deterministic、non-embedding、non-RAG 的知识关系图层和 retrieval foundation。

## 2. Goals

1. **Graph Domain Model** — 定义统一的 node types、edge types、relation evidence model
2. **Deterministic Graph Builder** — 统一现有关系计算引擎，支持 2-hop graph、增量构建、GraphPort abstraction
3. **Explainable Relationship API** — graph-first API endpoints，每条边附带 `reason` + `evidence`
4. **Graph-aware Discovery UI** — Card/Wiki/Library 升级为 graph-first navigation
5. **Retrieval Context Composer (non-RAG)** — graph-aware context assembly for recall/discovery
6. **Graph Backend Spike (optional)** — 隔离实验 Kuzu/SQLite FTS/DuckDB FTS

## 3. Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | RAG answering | v0.6 只做 retrieval context assembly |
| 2 | Embedding / semantic similarity | 确定性关系 + lexical retrieval 足够 |
| 3 | Vector DB | 无 embedding 需求 |
| 4 | Real LLM calls | fake provider 始终为默认 |
| 5 | Force-directed graph canvas / d3 / cytoscape | 不做大图可视化 |
| 6 | Global full graph | 始终以节点为中心，不做全局毛线球 |
| 7 | New large dependencies (in main) | Kuzu/DuckDB 仅在 R7 spike 隔离 |
| 8 | Auto approve / 破坏 human_approved 语义 | 不改变审批模型 |
| 9 | Real private data / Obsidian write / mail | 不涉及 |

## 4. Safety Constraints (Inviolable)

| # | Constraint | Verification |
|---|-----------|-------------|
| S1 | 不做 RAG answering — R6 只 assemble context, 不 generate answer | code review |
| S2 | 不做 embedding / vector DB | code review |
| S3 | 不调用真实 LLM | code review + test |
| S4 | Graph 构建只读已有 metadata，不修改卡片状态 | code review + test |
| S5 | ai_draft / human_approved 语义不变 | code review + test |
| S6 | 所有 relation 必须有 `reason` + `evidence`，无黑盒相似度 | code review + API smoke |
| S7 | 不读取 .env / secrets | code review |
| S8 | 不新增大型依赖 (R7 spike 除外，不合入 main) | code review |
| S9 | Graph API 响应不泄露卡片 body 内容（仅返回元数据摘要） | code review + test |

## 5. Graph Domain Model

### 5.1 Node Types

```python
class NodeType(str, Enum):
    CARD = "card"
    SOURCE = "source"
    WIKI_SECTION = "wiki_section"
    TAG = "tag"
    CONCEPT = "concept"  # 确定性术语提取
```

| Node | Identity | Key Properties |
|------|----------|---------------|
| CARD | `card_id` | title, status, quality_score, tags, source_id, created_at, approved_at |
| SOURCE | `source_id` | source_path, source_type, source_title, card_count |
| WIKI_SECTION | section anchor | title, level, card_count |
| TAG | normalized tag name | card_count |
| CONCEPT | normalized term | card_count, source_sections |

### 5.2 Edge Types

```python
class EdgeType(str, Enum):
    DERIVED_FROM = "derived_from"            # Card → Source
    MENTIONS = "mentions"                     # Card → Card (explicit ref)
    SHARES_TAG = "shares_tag"                 # Card ↔ Card (same tag)
    RELATED_BY_SOURCE = "related_by_source"   # Card ↔ Card (same source)
    RELATED_BY_WIKI_SECTION = "related_by_wiki_section"  # Card ↔ Card
    SIMILAR_TITLE_OR_TERM = "similar_title_or_term"       # Card ↔ Card (threshold)
    APPROVAL_STATE_OF = "approval_state_of"   # Draft → Approved
    LINKS_TO = "links_to"                     # Card → WikiSection
```

### 5.3 Relation Evidence Model

```python
@dataclass(frozen=True)
class RelationEvidence:
    reason: str          # e.g. "same_source_document", "shared_tag"
    evidence: str        # human-readable, e.g. "source: reading-notes/ai-ml.md"
    strength: float      # 0.0 - 1.0, deterministic calculation
    detail: dict         # structured data for UI rendering
```

Every edge MUST carry `RelationEvidence`. No edge without explainable reason.

## 6. Service/API/UI Boundaries

### 6.1 Backend Architecture

```
┌─────────────────────────────────────────┐
│  Web Facade (orchestration)             │
│  ┌───────────────────────────────────┐  │
│  │  GraphBuilder (new)               │  │
│  │  - build_graph(center_id, depth)  │  │
│  │  - 复用 compute_related_cards()   │  │
│  │  - 复用 build_*_centered_graph() │  │
│  │  - 扩展 2-hop                    │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  GraphPort (abstract interface)   │  │
│  │  - get_node(id, type)             │  │
│  │  - get_edges(node_id, depth)      │  │
│  │  - get_path(source, target)       │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │  DiscoveryContext (R6, new)       │  │
│  │  - assemble(query/card_id)        │  │
│  │  - returns graph-aware context    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### 6.2 API Endpoints

| Method | Path | Description | Unit |
|--------|------|-------------|------|
| GET | `/api/graph/node?ref={card_id}&depth=2` | 2-hop graph centered on card | R4 |
| GET | `/api/graph/explore?node_type={type}&node_id={id}` | Graph exploration from any node type | R4 |
| GET | `/api/graph/edge?source={id}&target={id}` | Edge details with all reasons + evidence | R4 |
| GET | `/api/recall?q=...&context=graph` | Enhanced recall with graph context | R6 |
| GET | `/api/discovery/context?ref={card_id}` | Assembled discovery context | R6 |

### 6.3 UI Components

| Component | Description | Unit |
|-----------|-------------|------|
| `GraphNavigationPanel` | 替代 RelatedCardsPanel，按 relation type 分组 + 可展开 evidence | R5 |
| `GraphExplorer` | 从任意卡片出发的 2-hop graph 结构化导航 | R5 |
| `WikiGraphNav` | Wiki 页面 section 间 graph navigation | R5 |
| `DiscoveryContextView` | Recall 结果 + graph context 综合视图 | R5 |

## 7. Implementation Units

### R1 — External Research & Repo Fit Review ✓ (done)

产出: `docs/specs/2026-05-24-024-v0_6-knowledge-graph-retrieval-foundation-research.md`

### R2 — MindForge Graph Domain Model SPEC

**Goal**: 将 research 文档中的图模型和架构设计定稿为正式 SPEC。

**Scope**:
- Graph domain model 定稿 (node types, edge types, evidence model)
- GraphPort interface 定义
- API endpoints spec
- UI component spec
- Test plan + smoke plan

**产出**: 本文档 (`docs/specs/2026-05-24-025-v0_6-knowledge-graph-retrieval-foundation-spec.md`)

**Verification**: 对照 non-goals checklist 自审、对照 safety constraints 自审

### R3 — Deterministic Graph Builder

**Goal**: 将现有关系计算引擎统一为 GraphBuilder + GraphPort abstraction。

**Scope**:
- 定义 `GraphPort` abstract interface (`src/mindforge/relations/graph_port.py`)
- 定义 `GraphModels` — Node, Edge, RelationEvidence, Graph dataclasses (`src/mindforge/relations/graph_models.py`)
- 实现 `DeterministicGraphBuilder` (`src/mindforge/relations/graph_builder.py`):
  - 复用 `compute_related_cards()` (RelationReason → EdgeType 映射)
  - 复用 `build_card_centered_graph()` (1-hop graph)
  - 新增 2-hop graph 构建 (`build_graph(center_id, depth=2)`)
  - 每条 edge 附带 RelationEvidence
- 增量更新支持: 卡片 approve 后 recalculate affected edges only

**Files**:
- `src/mindforge/relations/graph_port.py` (NEW)
- `src/mindforge/relations/graph_models.py` (NEW)
- `src/mindforge/relations/graph_builder.py` (NEW)
- `src/mindforge/relations/__init__.py` (extend exports)

**Test scenarios**:
- GraphBuilder builds 1-hop graph matching existing compute_related_cards output
- 2-hop graph includes neighbor-of-neighbor nodes
- Every edge has non-null reason + evidence + strength
- Deterministic: same input → same output
- Performance: 1000-card graph builds < 2s
- Golden fixture: known graph structure verified

### R4 — Explainable Relationship API

**Goal**: 新增 graph-first API endpoints。

**Scope**:
- `GET /api/graph/node?ref={card_id}&depth=2` — 2-hop graph response
- `GET /api/graph/explore?node_type={type}&node_id={id}` — 从 source/tag/section 出发
- `GET /api/graph/edge?source={id}&target={id}` — 两节点间所有 reason + evidence
- API schema: `GraphResponse`, `GraphNodeResponse`, `GraphEdgeResponse`, `RelationEvidenceResponse`
- 集成到 Web Facade

**Files**:
- `src/mindforge_web/schemas.py` (extend: add graph response schemas)
- `src/mindforge_web/routers/graph.py` (NEW)
- `src/mindforge_web/services/web_facade.py` (extend: graph orchestration methods)
- `src/mindforge_web/app.py` (register graph router)

**Test scenarios**:
- `/api/graph/node` returns correct 2-hop structure for known card
- `/api/graph/explore?node_type=source` returns cards from that source
- `/api/graph/edge` returns all reasons for known related pair
- Every edge in response has `reason` + `evidence` fields populated
- API does not return card body content (metadata only)

### R5 — Graph-aware Discovery UI

**Goal**: 前端从 card-first 升级为 graph-first discovery。

**Scope**:
- `GraphNavigationPanel`: 替换现有 RelatedCardsPanel
  - 按 EdgeType 分组（Related by Source / Shared Tag / Same Wiki Section / Similar Title）
  - 每组可折叠，显示 card count + 第一条 evidence
  - 展开后显示卡片列表 + 每条 relation 的 evidence detail
- Graph Explorer 入口: Library 页面新增 "Explore Graph" 按钮/标签
- Wiki 页面的 section graph nav: 利用已有 `compute_wiki_related_sections()` 展示 section 间关系
- 2-hop 导航: 从卡片 A → 相邻卡片 B → B 的相邻卡片（非 canvas，用结构化列表）

**Files**:
- `web/src/components/GraphNavigationPanel.tsx` (NEW)
- `web/src/components/GraphExplorer.tsx` (NEW)
- `web/src/pages/LibraryPage.tsx` (extend)
- `web/src/pages/WikiPage.tsx` (extend)
- `web/src/api/graph.ts` (NEW)
- `web/src/api/types.ts` (extend: graph types)
- `web/src/lib/i18n.ts` (extend: new i18n keys)

**Test scenarios**:
- GraphNavigationPanel renders groups by EdgeType
- Evidence text displayed for each relation
- Click on neighbor card navigates correctly
- 2-hop navigation renders neighbor-of-neighbor
- Wiki section graph nav links work
- 0 console errors
- UX matches existing design system patterns

### R6 — Retrieval Context Composer (Non-RAG)

**Goal**: graph-aware context assembly for recall/discovery.

**Scope**:
- `DiscoveryContext` dataclass:
  - `direct_matches`: 直接匹配卡片
  - `neighbor_cards`: 1-hop 邻居
  - `wiki_sections`: 所属 wiki sections
  - `shared_tags`: 聚合 tag 视图
  - `shared_sources`: 聚合 source 视图
- `assemble_discovery_context(card_id_or_query)` — deterministic assembly
- 增强 `GET /api/recall?q=...&context=graph`: BM25 结果之上附加 graph context
- **不做**: 基于此 context 的 LLM answering、RAG generation

**Files**:
- `src/mindforge/relations/discovery_context.py` (NEW)
- `src/mindforge_web/services/web_facade.py` (extend)
- `src/mindforge_web/routers/recall.py` (extend)

**Test scenarios**:
- Discovery context for a known card includes its neighbors, sections, tags, sources
- Recall with context=graph enriches BM25 results with graph data
- Empty context for non-existent card_id returns graceful empty
- Context assembly is deterministic

### R7 — Optional Local Graph Backend Spike

**Goal**: 在隔离分支中实验 Kuzu/SQLite FTS/DuckDB FTS。

**Scope**:
- spike/kuzu-graph-backend: Kuzu embedded graph DB experiment
- spike/fts-backend: SQLite FTS5 / DuckDB FTS experiment
- Spike report: performance, integration complexity, schema mapping
- **不合入 main** (separate branch, not merged until explicit spec authorization)

**Verification**: Spike report written, performance numbers collected

## 8. Test Plan

### 8.1 Python Tests

| Test File | Scope |
|-----------|-------|
| `tests/relations/test_graph_models.py` | Node/Edge/Evidence 数据结构 |
| `tests/relations/test_graph_builder.py` | 1-hop/2-hop graph construction, golden fixtures |
| `tests/relations/test_graph_port.py` | GraphPort interface contract |
| `tests/relations/test_discovery_context.py` | Context assembly correctness |
| `tests/test_graph_api.py` | Graph API endpoint integration tests |

### 8.2 Product Copy Tests

- New i18n keys for graph navigation component labels
- zh/en coverage for all graph-related UI strings

### 8.3 Contract Tests

- API response schema validation for `/api/graph/*` endpoints
- RelationEvidence schema enforcement (reason + evidence non-null)

## 9. Smoke Plan

### 9.1 API Smoke

```bash
# Graph node endpoint
curl http://localhost:8766/api/graph/node?ref=<card_id>&depth=2

# Graph explore
curl http://localhost:8766/api/graph/explore?node_type=source&node_id=<source_id>

# Edge detail
curl http://localhost:8766/api/graph/edge?source=<id1>&target=<id2>

# Recall with graph context
curl http://localhost:8766/api/recall?q=test&context=graph
```

### 9.2 Browser Smoke

- [ ] `/library` — Graph Explorer 入口可见
- [ ] `/library/card?ref=...` — GraphNavigationPanel 替代旧 RelatedCardsPanel
- [ ] GraphNavigationPanel — 按 EdgeType 分组，evidence 可展开
- [ ] 2-hop navigation — 从卡片 A 跳转到邻接卡片 B
- [ ] `/wiki` — section graph nav 链接正常
- [ ] 0 console errors, 0 API 5xx

## 10. Gate Matrix

| Unit | ruff | pytest | npm build | product copy | git diff | browser smoke |
|------|------|--------|-----------|-------------|----------|---------------|
| R1 Research | — | — | — | — | ✓ | — |
| R2 SPEC | — | — | — | — | ✓ | — |
| R3 Graph Builder | ✓ | ✓ | — | — | ✓ | — |
| R4 Graph API | ✓ | ✓ | — | — | ✓ | ✓ (API) |
| R5 Graph UI | — | ✓ | ✓ | ✓ | ✓ | ✓ |
| R6 Discovery Context | ✓ | ✓ | — | — | ✓ | ✓ (API) |
| R7 Spike | — | — | — | — | — | — |

## 11. Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| 需要真实 API key / secrets | HARD_STOP_SECRET |
| 需要调用真实 LLM | HARD_STOP_REAL_LLM |
| 需要处理真实私人资料 | HARD_STOP_PRIVATE_DATA |
| 需要 RAG/embedding/vector DB | HARD_STOP_RAG_EMBEDDING |
| 需要新增大型框架/依赖（非 spike） | HARD_STOP_LARGE_DEPENDENCY |
| 破坏 human_approved 语义 | HARD_STOP_APPROVAL_SEMANTICS |
| P0/P1 无法在 2 轮回退内关闭 | HARD_STOP_P0_P1_RETRY_EXCEEDED |
| Context 低于 5% | HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN |

## 12. References

- Research: `docs/specs/2026-05-24-024-v0_6-knowledge-graph-retrieval-foundation-research.md`
- Superseded Search & Discovery: `docs/specs/2026-05-24-023-v0_6-search-discovery-spec.md`
- v0.5 Planning Review: `docs/specs/2026-05-24-010-v0_5-next-phase-planning-review.md`
- v0.4 Relationship Experience: `docs/specs/2026-05-24-009-v0_4-knowledge-relationship-experience-spec.md`
- Engineering Workflow: `docs/dev/engineering-workflow.md`
- Autopilot: `.claude/commands/mf-autopilot.md`
