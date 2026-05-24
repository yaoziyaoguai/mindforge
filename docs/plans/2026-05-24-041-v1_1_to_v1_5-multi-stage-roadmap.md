---
title: MindForge v1.1–v1.5 Multi-Stage Auto-run Roadmap
type: roadmap
status: active
date: 2026-05-24
parent: 2026-05-24-039-v1_0-completion-review.md
supersedes: 2026-05-24-026-v0_7-v1_0-multi-stage-roadmap.md
---

# v1.1–v1.5: 从 Knowledge Workbench 到 Deep Knowledge System

## 0. 路线总览

```
v1.1                      v1.2                       v1.3                      v1.4                       v1.5
Quality & Reliability →   Graph / Retrieval      →   Local Backend         →   Personal Knowledge      →   Safe Integration &
Hardening                  Depth Expansion            Architecture Spike         Workbench UX                 Import/Export Expansion
(clean gates)              (explainable graph)        (isolated eval)            (coherent UX)                (safe boundaries)
```

### 核心设计原则（贯穿 v1.1–v1.5）

1. **Knowledge Workbench, not Search Engine** — 个人知识工作台，不是搜索页
2. **Deterministic & Explainable** — 所有关系、检索、推荐均可解释
3. **No RAG Answering, No Embedding, No Vector DB** — 始终以确定性规则 + lexical retrieval 为基础
4. **ai_draft / human_approved 不变** — AI 只创建草稿，人类显式审批
5. **Local & Lightweight** — 不引入大型生产依赖，新依赖必须在 spec 中明确授权后才合入 main
6. **Graph-First Navigation** — 图是知识导航的主界面
7. **Gate Evidence Integrity** — exit code 1 就是 1，pre-existing 必须有证据

---

## 1. Technology Inspiration & Repo Fit Review

以下外部技术为设计启发来源，**不直接引入为依赖**。每个启发必须映射到 MindForge 的实际架构能力，而不是照搬实现。

### 1.1 GraphRAG (Microsoft)

**GraphRAG 核心价值**:
- Graph extraction (entity/relation from text via LLM)
- Community hierarchy (Leiden algorithm on entity graph)
- Community summaries (LLM-generated descriptions per community)
- Local search (traverse entity graph around query entities)
- Global search (use community summaries for broad questions)

**MindForge 可吸收**:
- **分层图/社区聚合**: MindForge 已有 deterministic 图（source/tag/section → cards），可视为"知识社区"的确定性版本。卡片共享 source document = 同一"来源社区"；共享 tag = 同一"主题社区"；共享 wiki section = 同一"概念社区"。
- **Context composer**: v0.6 R6 已实现 `DiscoveryContext`，按 relation type 分组、strength 排序。可增强为按"社区"聚合（同 source 卡片群、同 tag 卡片群）。
- **可解释检索路径**: 当前 `graph_api` 返回 edge/reason/evidence，用户可理解"为什么相关"。
- **不做**: LLM entity extraction、LLM summarization、Leiden community detection、RAG answering。

**MindForge 映射**:

| GraphRAG 概念 | MindForge 对应 |
|--------------|---------------|
| Entity graph | KnowledgeCard / SourceDocument / WikiSection / Tag 节点图 |
| Community | 共享 source/tag/section 的卡片群（deterministic cluster） |
| Community summary | 卡片群统计（来源文档名、卡片数、标签列表）— 非 LLM 生成 |
| Local search | BM25 lexical search + graph expansion (1-hop/2-hop neighbors) |
| Global search | 通过 wiki section 结构 + tag 分布做主题导航 |
| Source citation | Provenance Trail — card → source → related cards 链路 |

### 1.2 CodeGraph / CodexGraph

**核心价值**: 为 coding agent 提供预索引的代码结构图（symbol graph），减少反复 grep/read，让 agent 知道"哪些代码相关"。

**MindForge 可吸收**:
- **不是代码符号图，而是知识结构图**: KnowledgeCard / SourceDocument / WikiSection / Tag / Concept / ApprovalState 的预索引图。
- **让系统/用户知道"知识为什么相关"**: 不是通过语义相似度，而是通过结构关系（同一来源、同一标签、同一 wiki 章节、同一批次创建）。
- **减少盲目搜索**: 当前 BM25 搜索是扁平的，结合 graph 结构可以按相关度分组。

**MindForge 映射**:

| CodeGraph 概念 | MindForge 对应 |
|---------------|---------------|
| Symbol graph (pre-indexed code structure) | Knowledge graph (pre-built deterministic relations) |
| Call graph (function A → function B) | Relation graph (card A → card B via shared source/tag/section) |
| Context assembly for agent | DiscoveryContext — 1-hop/2-hop context for card browsing |

### 1.3 SQLite FTS5

**核心价值**: Python stdlib 自带、零额外依赖、BM25/OKAPI 评分、持久化索引、前缀查询、phrase query、snippet 生成。

**当前状态**: v0.8 ADR-001 已决策"条件采用 SQLite FTS5，当前保持 Python BM25"。触发条件未满足（卡片规模 < 500）。

**MindForge 评估** (v1.3 重新评估):

| 维度 | Python BM25 (当前) | SQLite FTS5 |
|------|-------------------|-------------|
| 依赖 | 零（自实现） | 零（sqlite3 stdlib） |
| 索引持久化 | 不支持（每次重建） | 支持（文件持久化） |
| 查询延迟 (100 卡片) | < 10ms | < 5ms |
| 中文分词 | 字符级 bigram | 默认字符切分（可配 ICU tokenizer） |
| Snippet/highlight | 不支持 | 内置 snippet() 函数 |
| Phrase query | 不支持 | 内置 phrase query |
| 迁移风险 | 无 | 需测试召回质量 parity |

**v1.3 Decision**: 重新评估 FTS5 的触发条件。如果当前卡片数 > 500 或索引构建时间 > 1s，触发 FTS5 迁移。

### 1.4 Kuzu Embedded Graph Database

**核心价值**: 嵌入式 property graph DB、Cypher 查询语言、ACID 事务、零外部 server 依赖。

**当前状态**: v0.9 ADR-002 已决策"暂不引入 Kuzu，保持 In-Memory DeterministicGraphBuilder"。GraphPort 已就绪。

**MindForge 评估** (v1.3 重新评估):

| 维度 | In-Memory GraphBuilder (当前) | Kuzu |
|------|------------------------------|------|
| 依赖 | 零 | C++ 编译扩展（~50MB wheel） |
| 查询语言 | Python 遍历 | Cypher |
| 性能 (200 卡片, 2-hop) | < 50ms | < 10ms |
| 持久化 | 不支持 | 内置 |
| 复杂查询 | 有限（手动遍历） | Cypher 原生支持路径查询、聚合 |
| 维护成本 | 低 | 中（schema 映射、类型系统） |

**v1.3 Decision**: 重新评估。如果 2-hop 查询延迟 > 200ms 或图遍历复杂度超过当前 Python 实现的合理维护边界，触发 Kuzu spike。

### 1.5 与硬红线的交叉审计

| 外部技术 | 是否触碰硬红线 | 理由 |
|---------|--------------|------|
| GraphRAG | **触碰** (LLM extraction/summarization, RAG answering) | 仅吸收"分层图/社区聚合"概念，不做 LLM step |
| CodeGraph | 不触碰 | 启发来源，映射到 MindForge 知识结构图 |
| SQLite FTS5 | 不触碰 | stdlib，零额外依赖，lexical 非 semantic |
| Kuzu | **潜在触碰** (大型编译依赖) | v1.3 spike 严格隔离，不合入 main 除非 ADR 明确授权 |
| LightRAG | **触碰** (LLM/embedding) | 仅参考 graph exploration UI，不做 RAG |

---

## 2. v1.1 — Quality & Reliability Hardening

### 2.1 目标

Clean gates. 零 pre-existing failures. 可信 gate reporting. 为后续迭代建立可靠的质量基线。

### 2.2 动机

v1.0 结束时 `pytest tests/` exit code = 1（1 pre-existing）、`ruff check` exit code = 1（17 pre-existing）。这些 pre-existing failures 长期被忽略、被报告为 "all gates passed"。v1.1 的第一步就是诚实面对质量现状并修复。

### 2.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | ruff check clean | `ruff check src tests` exit code = 0 |
| G2 | pytest full clean | `python -m pytest tests/ -q` exit code = 0 |
| G3 | Gate evidence integrity | 所有 gate 报告包含 exact command + real exit code + no truncation |
| G4 | Product copy test coverage | 保持 65+ product copy tests, no regression |
| G5 | Quality baseline document | 可追踪的 quality dashboard，记录已知问题和改进 |

### 2.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | 新增功能 | v1.1 仅修复质量，不加功能 |
| 2 | 性能优化 | 不在此阶段范围 |
| 3 | 架构重构 | 不触动 backend/graph/retrieval 架构 |
| 4 | 新增依赖 | 不引入任何新依赖 |
| 5 | 大范围代码清理 | 只清理导致 gate failure 的问题 |

### 2.5 Implementation Units

#### U1: Fix ruff F821 — Missing `Literal` import

**Goal**: 修复 6 个 F821 错误。

**Root Cause**: `src/mindforge_web/services/web_config_service.py` 使用 `Literal["fake", "real"]` 但未从 `typing` 导入 `Literal`。

**Fix**: 在 `from typing import Any` 行添加 `Literal`。

**Files**: `src/mindforge_web/services/web_config_service.py`

**Verification**: `ruff check src/mindforge_web/services/web_config_service.py` exit code = 0

#### U2: Fix ruff F841 — Unused variable `en`

**Goal**: 修复 1 个 F841 错误。

**Root Cause**: `tests/test_web_product_copy.py:345` 中 `en = _read_i18n_en()` 赋值但未使用。原意图可能是做 en 相关断言但未实现。

**Fix**: 如果只需 zh，移除 `en =` 行；如果需要 en 断言，补充断言。

**Files**: `tests/test_web_product_copy.py`

**Verification**: `ruff check tests/test_web_product_copy.py --select F841` exit code = 0

#### U3: Fix ruff invalid-syntax — Update target-version to py312

**Goal**: 修复 10 个 invalid-syntax 错误。

**Root Cause**: `pyproject.toml` 中 ruff `target-version = "py311"` 但实际 Python 3.12.2。测试中使用的 f-string 语法（嵌套引号复用、f-string 内转义）是 3.12 特性。

**Fix**: 更新 `pyproject.toml` 中 ruff `target-version` 从 `"py311"` 到 `"py312"`。

**Files**: `pyproject.toml`

**Verification**: `ruff check tests/test_web_product_copy.py` exit code = 0

#### U4: Fix pre-existing pytest failure

**Goal**: 修复 `test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy`。

**Root Cause**: 测试断言 `?? source.path` 不在 SourcesPage.tsx 中，但实际代码 `play_path ?? source.path ?? "-"` 包含此 fallback 模式。这是合理的 UI fallback 逻辑。

**Fix**: 更新测试的 `forbidden_fragments` 列表，移除 `"?? source.path"` 或替换为更精确的断言。已有的 fallback 模式是设计意图，不是回归。

**Files**: `tests/test_web_api.py`

**Verification**: `python -m pytest tests/test_web_api.py::test_sources_page_uses_source_path_view_not_raw_path_for_display_or_copy -q` exit code = 0

#### U5: Gate Evidence Reporting Hardening

**Goal**: 确保 `/mf-autopilot` 和日常开发中的 gate 报告格式符合 gate evidence rule (§7.1)。

**Fix**:
- 审计 `scripts/check.sh`（如果存在），确保传递真实 exit code
- 在 implementation notes 中记录当前 gate reporting 模板
- 不需要代码改动（规范已在 mf-autopilot.md 中定义）

**Files**: `scripts/check.sh` (审计), docs implementation notes

**Verification**: 手动验证下一轮 gate 报告的完整性

#### U6: Quality Baseline Document

**Goal**: 建立可追踪的 quality dashboard。

**Content**:
- 当前 quality baseline: test counts, ruff status, known issues
- Pre-existing issues 追踪表（ID, file, issue, priority, target version, status）
- Gate pass/fail 历史

**Files**: `docs/plans/2026-05-24-042-v1_1-quality-baseline.md` (NEW)

### 2.6 Test Plan

| Test File | Current | v1.1 Target |
|-----------|---------|-------------|
| `tests/test_web_product_copy.py` | 65 pass | 65 pass (no regression) |
| `tests/test_web_api.py` | ~140 pass, 1 fail | all pass |
| Full pytest | 1 fail | 0 fail |

### 2.7 Gate Matrix

| Unit | npm build | product copy | full pytest | ruff check | git diff --check |
|------|-----------|-------------|-------------|------------|-----------------|
| U1 F821 fix | — | — | — | ✓ | ✓ |
| U2 F841 fix | — | — | — | ✓ | ✓ |
| U3 py312 | — | — | — | ✓ | ✓ |
| U4 pytest fix | — | — | ✓ | — | ✓ |
| U5 gate evidence | — | — | — | — | ✓ |
| U6 quality doc | — | — | — | — | ✓ |

### 2.8 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| Fix 引入新 regression | HARD_STOP_P0_P1_RETRY_EXCEEDED (if >2 rounds) |
| Context < 5% | HARD_STOP_CONTEXT_LOW_HANDOFF_WRITTEN |

### 2.9 v1.1 → v1.2 Transition

当所有 5 个 gate 的 exit code = 0 时，v1.1 完成，自动进入 v1.2。

---

## 3. v1.2 — Graph / Retrieval Depth Expansion

### 3.1 目标

深化 v0.6-v0.8 已有 graph/retrieval 能力。增强 relation reason 颗粒度、relation scoring、graph community 概念（deterministic version），但不做 RAG answering。

### 3.2 动机

v0.6-v0.7 建立了基础的 graph/retrieval 框架，但能力停留在"基础可用"：
- Relation reason 只有 3 个 EdgeType，缺失细分
- Relation scoring 仅基于 shared entity count，无权重调整
- 没有"知识社区"概念（同 source/tag/section 的卡片群）
- Retrieval context 仅按 EdgeType 分组，无主题聚合
- Provenance trail 链路完整但无交互式探索

### 3.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | Relation reason granularity | same_source_document / shared_tag / same_wiki_section / source_location_neighbor / same_review_batch 在 evidence 中可区分 |
| G2 | Relation scoring enhancement | 加权评分：source overlap + tag overlap + wiki section proximity + recency |
| G3 | Knowledge community concept | 同 source/tag/section 卡片群作为可导航的"知识社区"（deterministic, non-LLM） |
| G4 | Retrieval context composer enhancement | discovery context 按主题社区聚合，而非仅按 EdgeType 分组 |
| G5 | Provenance trail interactivity | 来源链可交互跳转，支持双向探索 |
| G6 | Evidence quality | 所有 relation evidence 对用户可读，中文场景友好 |

### 3.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | 新增 embedding/vector DB | 硬红线 |
| 2 | 新增 LLM-based relation extraction | 硬红线 |
| 3 | 引入社区检测算法 (Leiden/Louvain) | 外部依赖，当前规模不需要 |
| 4 | 新增 API endpoint（默认） | 优先增强已有 API，仅当已有 API 无法承载时新增 |
| 5 | Graph visualization canvas (d3/cytoscape) | 结构化导航优于大图可视化 |
| 6 | 性能优化（大规模） | 当前规模 (< 200 卡片) 下性能足够 |

### 3.5 Implementation Units

#### U1: Relation Reason Granularity

**Goal**: 细分 EdgeType 下的 reason 颗粒度，保留原始 RelationReason 到 evidence detail。

**Scope**:
- `graph_builder.py`: `_REASON_TO_EDGE_TYPE` 映射中保留细分 reason 到 `RelationEvidence.detail`
- 新增 `RELATED_BY_TAG` EdgeType（当前 shared tag 归类到 RELATED_BY_SOURCE 或 generic）
- 确认 `compute_related_cards()` 的每个 RelationReason 都能追溯到 specific entity

**Files**: `src/mindforge/relations/graph_builder.py`, `src/mindforge/relations/graph_models.py`

#### U2: Relation Scoring Enhancement

**Goal**: 加权 relation strength，不只基于 shared entity count。

**Scope**:
- `scoring.py` (NEW): 加权评分公式
  - `base_score = shared_entity_count / max_possible`
  - `source_overlap_weight = 0.4` (同源文档最强信号)
  - `tag_overlap_weight = 0.3`
  - `wiki_section_weight = 0.2`
  - `recency_bonus = 0.1` (近期卡片加权)
- `graph_builder.py`: 集成新 scoring，替换简单 count-based

**Files**: `src/mindforge/relations/scoring.py` (NEW), `src/mindforge/relations/graph_builder.py`

#### U3: Knowledge Community Concept

**Goal**: 定义"知识社区"的确定性版本 — 共享 source/tag/section 的卡片群。

**Scope**:
- `community.py` (NEW): `KnowledgeCommunity` dataclass
  - `community_type: Literal["source", "tag", "wiki_section"]`
  - `shared_entity: str` (source path / tag name / section title)
  - `member_count: int`
  - `member_card_ids: list[str]`
  - `description: str` (deterministic, non-LLM: e.g. "来自 {source} 的 {n} 张卡片")
- `community_service.py` (NEW): `detect_communities(cards) -> list[KnowledgeCommunity]`
- API: `GET /api/knowledge/communities` 或扩展现有 graph endpoint

**Files**: `src/mindforge/relations/community.py` (NEW), `src/mindforge_web/routers/library.py`

#### U4: Retrieval Context Composer Enhancement

**Goal**: discovery context 按知识社区聚合，不只是按 EdgeType 分组。

**Scope**:
- `discovery_context.py`: `DiscoveryContextSection` 新增 `community_ref: str | None`
- 同一 source 的卡片 grouped under "来自同一来源文档: xxx.md"
- 同一 tag 的卡片 grouped under "共享标签: #concept"
- 同一 wiki section 的卡片 grouped under "同一章节: §2.1 概念定义"

**Files**: `src/mindforge/relations/discovery_context.py`, `web/src/components/GraphNavigationPanel.tsx`

#### U5: Provenance Trail Interactivity

**Goal**: 来源链支持双向交互（card → source → related cards → ...）。

**Scope**:
- `ProvenanceTrail` 组件增强: 点击 source 可跳转 source 页面，点击 related card 可跳转卡片
- `SourceLocationBadge`: 在卡片详情中展示 source location，点击可导航
- GraphNavigationPanel 集成 provenance 路径高亮

**Files**: `web/src/components/ProvenanceTrail.tsx`, `web/src/components/SourceLocationBadge.tsx`, `web/src/components/GraphNavigationPanel.tsx`

### 3.6 Test Plan

重点测试领域:
- Relation reason 不丢失细分信息
- Scoring 公式确定性（same input → same score）
- Community detection 正确分组
- Discovery context 按社区聚合正确
- Provenance trail 双向链接正确

### 3.7 Gate Matrix

| Unit | npm build | product copy | full pytest | ruff check | git diff --check | browser smoke |
|------|-----------|-------------|-------------|------------|-----------------|---------------|
| U1 Relation Reason | — | — | ✓ | ✓ | ✓ | — |
| U2 Scoring | — | — | ✓ | ✓ | ✓ | — |
| U3 Community | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| U4 Context Composer | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| U5 Provenance Trail | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

### 3.8 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| Community detection 引入外部算法依赖 | HARD_STOP_LARGE_DEPENDENCY |
| LLM-based relation extraction 被引入 | HARD_STOP_REAL_LLM |
| Embedding/vector similarity 被引入 | HARD_STOP_RAG_EMBEDDING |
| P0/P1 > 2 round retry | HARD_STOP_P0_P1_RETRY_EXCEEDED |

### 3.9 v1.2 → v1.3 Transition

v1.2 全部 units 完成且所有 gate exit code = 0 后，自动进入 v1.3。

---

## 4. v1.3 — Local Backend Architecture Spike

### 4.1 目标

在严格隔离条件下重新评估 SQLite FTS5 和 Kuzu 的可行性。不做生产迁移，但产出更新的 ADR 和可运行的 spike code。

### 4.2 动机

v0.8-v0.9 的 ADR-001/002 已超过当前评估周期。v1.1-v1.2 的增强可能改变性能特征（更多 relation types、community detection、scoring），需要重新评估:
- 当前 In-Memory + Python BM25 是否仍然够用？
- 什么条件下需要 FTS5 / Kuzu？
- 迁移的成本收益比是否变化？

### 4.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | 性能基线测量 | 当前方案的性能数据: graph build time, 2-hop query latency, BM25 index/query, community detection |
| G2 | FTS5 spike (隔离) | 在 spike 分支实现 SQLite FTS5 engine，对比 BM25 |
| G3 | Kuzu spike (隔离) | 在 spike 分支实现 Kuzu graph backend，对比 DeterministicGraphBuilder |
| G4 | 更新 ADR | 基于新数据更新 ADR-001/002 |

### 4.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | FTS5/Kuzu 合入 main | 严格隔离，必须经过 ADR 授权 |
| 2 | 替换现有 backend | 仅评估，不替换 |
| 3 | 生产数据迁移 | 无异 |
| 4 | 引入生产依赖 | spike 依赖在 spike 分支，不合入 main |

### 4.5 Implementation Units

#### U1: Performance Baseline Measurement

**Goal**: 测量当前方案的完整性能基线。

**Scope**: 编写 benchmark script，测量: graph build (100/200/500 cards), 2-hop query, BM25 index/query, community detection, memory usage。

**Files**: `scripts/benchmark_baseline.py` (NEW), spike branch

#### U2: SQLite FTS5 Spike

**Goal**: 在 spike 分支实现 FTS5 RetrievalPort 实现，对比 BM25。

**Files**: spike branch only (`spike/sqlite-fts5-v1_3/`)

#### U3: Kuzu Graph Backend Spike

**Goal**: 在 spike 分支实现 Kuzu GraphPort 实现，对比 DeterministicGraphBuilder。

**Files**: spike branch only (`spike/kuzu-graph-v1_3/`)

#### U4: Updated ADRs

**Goal**: 基于性能数据和 spike 结果更新 ADR。

**Files**: `docs/adr/2026-05-24-001-retrieval-backend.md` (update), `docs/adr/2026-05-24-002-kuzu-graph-backend.md` (update)

### 4.6 Gate Matrix

| Unit | Location | Gate |
|------|---------|------|
| U1 Benchmark | main | `python -m pytest tests/ -q` + `git diff --check` |
| U2 FTS5 Spike | spike branch | spike-branch only tests |
| U3 Kuzu Spike | spike branch | spike-branch only tests |
| U4 ADR Update | main | `git diff --check` (docs only) |

### 4.7 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| FTS5/Kuzu 被提议合入 main 未经 ADR 授权 | HARD_STOP_LARGE_DEPENDENCY |
| Spike 需要真实数据/真实 API | HARD_STOP_PRIVATE_DATA / HARD_STOP_REAL_LLM |

### 4.8 v1.3 → v1.4 Transition

v1.3 完成 benchmark + spike + updated ADRs 后，自动进入 v1.4。

---

## 5. v1.4 — Personal Knowledge Workbench UX

### 5.1 目标

把 v1.1-v1.3 的质量/关系/社区/性能能力组织成真正可用的本地知识工作台 UX。不只是功能集合，而是 coherent 的知识工作体验。

### 5.2 设计愿景

v1.4 的 MindForge:
- **关系地图升级**: GraphNavigationPanel 从侧边栏辅助视图升级为主要的导航方式
- **知识社区浏览**: 按 source/tag/section 浏览卡片群，了解"这个主题下有哪些知识"
- **来源溯源链**: 从任意卡片追溯完整的信息来源链
- **知识体检仪表盘**: Card/Wiki Quality、Knowledge Health 从前台可见
- **Approval 生命周期可视化**: 知识从 ai_draft 到 human_approved 的完整叙事
- **Dogfood 报告 UX**: 本地 dogfood 结果可视化
- **安全导出审查**: 导出前预览、审查、确认

### 5.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | Relationship map UX | GraphNavigationPanel 作为卡片详情的主导航之一，支持按社区/类型分组，支持 2-hop 深度切换 |
| G2 | Knowledge community browser | 按 source/tag/section 浏览的"社区视图" |
| G3 | Source provenance trail UX | 完整来源链可视化，支持交互式跳转 |
| G4 | Knowledge health dashboard | Health Report 前台化，从"后台脚本"变为"前台仪表盘" |
| G5 | Approval lifecycle UX | ApprovalTimeline 增强，卡片 diff 视图（title/body 修改历史） |
| G6 | Dogfood report UX | fake dogfood 结果在 Web UI 中可视化展示 |
| G7 | Safe export review UX | 导出前预览、白名单过滤提示、导出记录 |

### 5.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | Force-directed graph canvas | 结构化导航 > 大图可视化 |
| 2 | Real-time collaboration | 个人工具 |
| 3 | Mobile UI | 桌面优先 |
| 4 | Auto-approve | 永久不做 |
| 5 | RAG answering | 硬红线 |
| 6 | 新增 LLM feature | fake provider only |

### 5.5 Implementation Units

详细 spec 在 v1.3 完成后制定（基于 v1.1-v1.3 的产出），以下为方向性框架:

| Unit | Capability | Priority |
|------|-----------|----------|
| W1 | Relationship Map UX 升级 | P0 |
| W2 | Knowledge Community Browser | P0 |
| W3 | Source Provenance Trail UX | P1 |
| W4 | Knowledge Health Dashboard 前台化 | P1 |
| W5 | Approval Lifecycle UX 增强 | P1 |
| W6 | Dogfood Report UX | P2 |
| W7 | Safe Export Review UX | P2 |

### 5.6 Gate Matrix

每 unit 需要: npm build + product copy + full pytest + ruff check + git diff --check + browser smoke (UI units)

### 5.7 Stop Conditions

所有通用 hard-stop 均适用。

### 5.8 v1.4 → v1.5 Transition

v1.4 全部 units 完成且所有 gate exit code = 0 后，自动进入 v1.5。

---

## 6. v1.5 — Safe Integration & Import/Export Expansion

### 6.1 目标

在不处理真实私人资料、不写真实 Obsidian vault、不调用真实外部服务的前提下，设计安全集成边界并实现 fake/local import/export adapters。

### 6.2 动机

v1.0 I3 实现了基础 Markdown 导出。v1.5 扩展集成边界:
- 更多导出格式（JSON、OPML）
- 导入适配器（Markdown file → 卡片、OPML → 卡片）
- Obsidian vault 互操作的 fake/local adapter（不写真实 vault）
- 定时/事件驱动的健康报告
- 但始终不碰硬红线

### 6.3 Goals

| # | Goal | Success Criteria |
|---|------|-----------------|
| G1 | Multi-format export | Markdown + JSON + OPML 导出 |
| G2 | Import adapters (fake/local) | 从本地 Markdown 文件创建卡片（fake dogfood 场景） |
| G3 | Obsidian binding design | 互操作设计文档（不写真实 vault） |
| G4 | Scheduled health report | 事件驱动的健康报告（本地定时检查） |
| G5 | Real provider opt-in docs | 用户自配置真实 LLM/Cubox/Upstage 的安全文档 |

### 6.4 Non-Goals

| # | Non-Goal | Reason |
|---|---------|--------|
| 1 | 真实 Obsidian vault 读写 | 硬红线 |
| 2 | 真实 Cubox/Upstage API 调用 | 硬红线 |
| 3 | 浏览器扩展 | 超出当前 scope |
| 4 | Webhook/网络回调 | 硬红线（外部服务依赖） |
| 5 | 真实邮件发送 | 硬红线 |

### 6.5 Implementation Units

详细 spec 在 v1.4 完成后制定，以下为方向性框架:

| Unit | Capability | Priority |
|------|-----------|----------|
| I1 | JSON/OPML 导出格式 | P1 |
| I2 | Local Markdown file import adapter | P1 |
| I3 | Obsidian binding design doc | P2 |
| I4 | Structured export package (.zip) | P2 |
| I5 | Scheduled health check + report | P2 |
| I6 | Real provider opt-in safety docs | P2 |

### 6.6 Gate Matrix

每 unit 需要: npm build (UI units) + pytest + ruff check + git diff --check + browser smoke (UI units)

### 6.7 Stop Conditions

| Condition | HARD_STOP Code |
|-----------|---------------|
| 处理真实私人资料 | HARD_STOP_PRIVATE_DATA |
| 写真实 Obsidian vault | HARD_STOP_OBSIDIAN_WRITE |
| 调用真实外部 API | HARD_STOP_REAL_LLM |
| 新增 webhook/网络依赖 | HARD_STOP_LARGE_DEPENDENCY |

---

## 7. Self-Review Checklist

对照全局硬红线自审（每次进入新 version 前必须重审）:

- [ ] 是否退化成普通搜索页？ — **否**。v1.2 社区概念/v1.4 工作台都是 graph-first
- [ ] 是否偷偷变成 RAG answering？ — **否**。所有 context assembly 明确为 non-RAG
- [ ] 是否偷偷引入 embedding/vector DB？ — **否**。v1.3 FTS5 是 lexical，非 semantic
- [ ] 是否需要真实 LLM？ — **否**。fake provider 始终为默认
- [ ] 是否破坏 ai_draft / human_approved 语义？ — **否**。v1.4 增强可见性但不改变语义
- [ ] 是否引入大型依赖？ — **否**。v1.3 spike 严格隔离，需 ADR 授权才合入 main
- [ ] 是否让 Autopilot 每阶段停下来？ — **否**。每个 version 有明确的 units/gate/transition rules
- [ ] 是否给了足够材料支撑连续几小时自动推进？ — **是**。5 个 version × 多个 units × tests × gate × smoke = 足够
- [ ] 每个阶段是否有 clear goals / non-goals / tests / smoke / stop conditions？ — **是**
- [ ] 每个阶段是否有明确的 next-stage transition？ — **是**

---

## 8. Auto-run Continuation Rules

1. **v1.1 完成 → 自动进入 v1.2**: 当 ruff + pytest + product copy + npm build + diff check 全部 exit code = 0
2. **v1.2 完成 → 自动进入 v1.3**: 当 v1.2 全部 units 的 gate 通过
3. **v1.3 完成 → 自动进入 v1.4**: 当 benchmark + spike + updated ADRs 完成
4. **v1.4 完成 → 自动进入 v1.5**: 当 v1.4 全部 units 的 gate 通过
5. **v1.5 完成 → HARD_STOP_PRODUCT_DECISION**: 需要产品层面决策下一步方向

**commit/push 不是停止点，是检查点。** 每个 commit/push 后重新建立 repo facts → 判断 hard-stop → 无 hard-stop 则继续。

## 9. References

- v1.0 Completion Review: `docs/plans/2026-05-24-039-v1_0-completion-review.md`
- v1.0 Gate Evidence Audit: `docs/plans/2026-05-24-040-v1_0-gate-evidence-audit.md`
- v0.7-v1.0 Roadmap: `docs/specs/2026-05-24-026-v0_7-v1_0-multi-stage-roadmap.md` (superseded)
- v0.8-v0.9 ADR: `docs/implementation-notes/2026-05-24-035-v0_8-v0_9-retrieval-graph-adr.md`
- Retrieval ADR: `docs/adr/2026-05-24-001-retrieval-backend.md`
- Kuzu ADR: `docs/adr/2026-05-24-002-kuzu-graph-backend.md`
- Engineering Workflow: `docs/dev/engineering-workflow.md`
- Autopilot: `.claude/commands/mf-autopilot.md`
- Copy Policy: `docs/dev/copy-policy.md`
