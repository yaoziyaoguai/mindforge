# v3.7 Graph Ontology & Node/Edge Semantics — Implementation Notes

**日期**: 2026-05-25
**状态**: complete
**基于**: [v3.7-v4.1 Graph View Roadmap](../plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md)
**ADR**: [ADR-006 Graph Ontology v1](../adr/2026-05-25-006-graph-ontology-v1.md)

> **Status note (v4.6 docs simplification, 2026-05-26)**: This document is historical implementation evidence. Current product truth: Graph Ontology v1 defined 8 NodeType (card/source/tag/wiki_section/community/topic/entity/concept_candidate), but only 4 (card/source/tag/wiki_section) are formally supported in the product main path. Community/topic/entity/concept_candidate are lab/internal. See docs/README.md and docs/dev/docs-reset-index.md.

---

## 实现范围 (U1-U4)

### U1: Graph Ontology ADR
- 创建 `docs/adr/2026-05-25-006-graph-ontology-v1.md`，定义 MindForge graph ontology v1
- 回答 roadmap 中 13 个核心问题（Source → Entity 的 node/edge/property 分类）

### U2: NodeType / EdgeType 模型扩展
- 修改 `src/mindforge/relations/graph_models.py`
- NodeType: 5 → 8（新增 COMMUNITY, TOPIC, ENTITY；CONCEPT → CONCEPT_CANDIDATE 重命名）
- EdgeType: 9 → 14（移除 APPROVAL_STATE_OF, MENTIONS；新增 HAS_TAG, IN_SECTION, CONTAINS, INCLUDES, MENTIONS_CANDIDATE, RESOLVES_TO, BELONGS_TO_TOPIC）
- 每个 enum 值添加中文 docstring 解释建模理由

### U3: Ontology Contract Tests
- 创建 `tests/relations/test_graph_ontology.py`（39 个测试，5 个 test class）
- 覆盖：NodeType ontology (13)、EdgeType ontology (12)、Fact vs Candidate boundary (4)、Edge evidence (3)、GraphNode construction (4)

### U4: Implementation Notes + Gate + Commit/Push（本文件）

---

## 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `docs/adr/2026-05-25-006-graph-ontology-v1.md` | NEW | ADR-006 图本体定义 |
| `docs/plans/2026-05-25-080-v3_7_to_v4_1-graph-view-ontology-roadmap.md` | NEW | v3.7-v4.1 roadmap |
| `docs/implementation-notes/2026-05-25-081-v3_7-graph-ontology.md` | NEW | 本文件 |
| `src/mindforge/relations/graph_models.py` | MODIFIED | NodeType 5→8, EdgeType 9→14, 中文 docstring |
| `src/mindforge/relations/graph_builder.py` | MODIFIED | MENTIONS→LINKS_TO, 移除 APPROVAL_STATE_OF strength |
| `tests/relations/test_graph_ontology.py` | NEW | 39 ontology contract tests |
| `tests/relations/test_graph_models.py` | MODIFIED | EdgeType.MENTIONS→LINKS_TO (immutability test) |
| `tests/relations/test_graph_builder.py` | MODIFIED | CONCEPT→CONCEPT_CANDIDATE (test names/assertions) |
| `tests/test_review_approval_boundary.py` | MODIFIED | allowlist 新增 graph_models.py |

---

## 关键设计决策

### 1. Approval 不是 NodeType
**理由**: ai_draft / human_approved 是 Card 的 status property，ApprovalDecision 是状态转换记录。建模为 NodeType 会导致节点膨胀和语义混淆。这是 v3.7 ontology 最关键的安全边界 — 确保 APPROVAL_STATE_OF edge type 被移除。

### 2. Entity ≠ Card
**理由**: Card 是知识工作流对象（有 status、review_batch），Entity 是被多张 Card mention 的语义对象（有 canonical label、aliases）。分离两者后：Card 可以通 MENTIONS_CANDIDATE 指向 ConceptCandidate，ConceptCandidate 经用户确认后通过 RESOLVES_TO 升级为 Entity。

### 3. Fact graph vs Candidate graph 严格分离
**理由**: fact graph 只包含 human_approved 知识；candidate graph 包含自动检测的 ConceptCandidate，需用户显式确认。两者不能混淆 — CONCEPT_CANDIDATE 明确标注 "candidate" 后缀作为信号。

### 4. 所有边必须有 evidence
**理由**: GraphEdge 必须携带 RelationEvidence（reason + evidence text + strength）；不能有无 evidence 的边。这是 v3.7 ontology 的硬约束。

### 5. Community / Topic 是 NodeType（不是纯 UI）
**理由**: 两者由确定性规则计算，有 stable identity（shared_entity + community_type）和 evidence trail，因此适合作为图节点。

### 6. Retrieval / Export / Dogfood / Readiness 不入图
**理由**: 这些是临时查询上下文、导出产物、运行记录或基础设施诊断 — 没有持久知识结构语义。

---

## 安全性审计

- [x] 不读取 .env 或 secrets
- [x] 不调用真实 LLM、Cubox、Upstage
- [x] 不处理真实私人资料
- [x] 不写真实 Obsidian vault
- [x] 不做 RAG answering
- [x] 不做 embedding / vector DB
- [x] 不新增大型依赖
- [x] 不破坏 explicit approval / human_approved 语义
- [x] human_approved allowlist 已更新（graph_models.py 的 docstring 使用 human_approved 仅为 ontology 边界定义）

---

## Gate 结果

| Gate | 命令 | Timeout | Exit Code | 备注 |
|------|------|---------|-----------|------|
| ruff check | `ruff check src/ tests/ docs/` | no | 0 | clean |
| pytest full | `python -m pytest tests/ -q --tb=short` | no | 0 | ~3067 tests passed |
| npm build | `npm --prefix web run build` | no | 0 | build succeeded |
| product copy | `python -m pytest tests/test_web_product_copy.py -q --tb=short` | no | 0 | passed |

---

## 下一步

v3.8 Knowledge Graph View MVP — 基于 v3.7 ontology 构建图视图：
- 支持 subgraph 展示（非全量）
- 点击节点/边可查看 evidence/provenance
- 从 Card detail / Wiki / Workbench 进入 graph view
- 不引入大型可视化依赖
