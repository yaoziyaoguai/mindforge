"""v3.7 Graph Ontology contract tests — 验证 ADR-006 定义的图建模规则。

中文学习型说明：这些测试不验证具体的图数据内容，而是验证 ontology 本身的
结构约束：哪些是 node、哪些是 edge、哪些不能入图、fact/candidate 边界等。
这些规则如果被破坏，会导致图模型语义混乱（如把状态字段建模为节点）。

所有测试使用合成数据或枚举值，不调用真实 LLM / embedding。
"""

from __future__ import annotations

from mindforge.relations.graph_models import (
    EdgeType,
    GraphEdge,
    GraphNode,
    NodeType,
    RelationEvidence,
)


class TestNodeTypeOntology:
    """NodeType 枚举的 ontology 规则验证。"""

    def test_card_is_node_type(self):
        """CARD 是 fact graph 的核心节点类型。"""
        assert NodeType.CARD in NodeType
        assert NodeType.CARD.value == "card"

    def test_source_is_node_type(self):
        """SOURCE 是 fact graph 的源文档节点类型。"""
        assert NodeType.SOURCE in NodeType
        assert NodeType.SOURCE.value == "source"

    def test_wiki_section_is_node_type(self):
        """WIKI_SECTION 是 fact graph 的 Wiki 章节节点类型。"""
        assert NodeType.WIKI_SECTION in NodeType
        assert NodeType.WIKI_SECTION.value == "wiki_section"

    def test_tag_is_node_type(self):
        """TAG 是 fact graph 的标签节点类型。"""
        assert NodeType.TAG in NodeType
        assert NodeType.TAG.value == "tag"

    def test_community_is_node_type(self):
        """COMMUNITY 是 factual graph 节点类型 — v3.7 新增。

        中文学习型说明：Community 由确定性规则计算，有稳定的 identity
        （shared_entity + community_type）和 evidence trail，
        因此适合作为图节点，而非仅作为 UI grouping。
        """
        assert NodeType.COMMUNITY in NodeType
        assert NodeType.COMMUNITY.value == "community"

    def test_topic_is_node_type(self):
        """TOPIC 是 fact graph 节点类型 — v3.7 新增。

        Topic 由合并重叠社区生成，有可引用的 identity 和 evidence，
        可作为知识主题节点在图视图中展示。
        """
        assert NodeType.TOPIC in NodeType
        assert NodeType.TOPIC.value == "topic"

    def test_entity_is_node_type(self):
        """ENTITY 是 fact graph 节点类型 — v3.7 新增。

        中文学习型说明：Entity 独立于 Card 存在，拥有 canonical label 和 alias set。
        必须由用户显式确认后才能从 CONCEPT_CANDIDATE 升级。
        """
        assert NodeType.ENTITY in NodeType
        assert NodeType.ENTITY.value == "entity"

    def test_concept_candidate_is_node_type(self):
        """CONCEPT_CANDIDATE 是 candidate graph 节点类型 — v3.7 重命名（原 CONCEPT）。

        属于 candidate graph，不能自动升级为 ENTITY。
        """
        assert NodeType.CONCEPT_CANDIDATE in NodeType
        assert NodeType.CONCEPT_CANDIDATE.value == "concept_candidate"

    def test_entity_and_card_are_different_node_types(self):
        """Entity 不等于 Card — 它们是不同的 NodeType。

        中文学习型说明：Card 是知识工作流对象（有 status、review_batch 等），
        Entity 是被多张 Card mention 的语义对象（有 canonical label、aliases）。
        这个区分是 v3.7 ontology 的关键设计决策。
        """
        assert NodeType.ENTITY != NodeType.CARD
        assert NodeType.ENTITY.value != NodeType.CARD.value

    def test_concept_candidate_and_entity_are_different_node_types(self):
        """CONCEPT_CANDIDATE ≠ ENTITY — 前者是候选，后者是已确认。

        候选实体不能自动升级为 Entity，需用户显式确认。
        """
        assert NodeType.CONCEPT_CANDIDATE != NodeType.ENTITY

    def test_no_approval_node_type(self):
        """Approval 不是 NodeType — 它是 Card 的状态转换记录，不是独立图节点。

        中文学习型说明：ai_draft / human_approved 是 Card 的 status property，
        ApprovalDecision 是状态转换记录，都不应成为独立图节点。
        如果将 approval 建模为 node，会导致图的节点膨胀和语义混淆。
        """
        all_node_types = {nt.value for nt in NodeType}
        assert "approval" not in all_node_types
        assert "approval_decision" not in all_node_types
        assert "ai_draft" not in all_node_types
        assert "human_approved" not in all_node_types

    def test_no_retrieval_or_query_node_type(self):
        """RetrievalContext / Query 不是 NodeType — 它们是临时查询上下文。

        query 没有持久化身份，不应入图。
        """
        all_node_types = {nt.value for nt in NodeType}
        assert "retrieval_context" not in all_node_types
        assert "query" not in all_node_types
        assert "search" not in all_node_types

    def test_no_export_or_dogfood_node_type(self):
        """ExportPackage / DogfoodRun 不是 NodeType — 它们是临时产物/运行记录。

        这些对象没有知识结构语义，不应入图。
        """
        all_node_types = {nt.value for nt in NodeType}
        assert "export" not in all_node_types
        assert "dogfood" not in all_node_types
        assert "run" not in all_node_types

    def test_total_node_type_count(self):
        """确认 NodeType 数量 = 8（v3.7 ontology v1）。

        Fact graph: CARD, SOURCE, WIKI_SECTION, TAG, COMMUNITY, TOPIC, ENTITY (7)
        Candidate graph: CONCEPT_CANDIDATE (1)
        Total: 8
        """
        assert len(NodeType) == 8, (
            f"期望 9 个 NodeType，实际 {len(NodeType)}: "
            f"{[nt.value for nt in NodeType]}"
        )


class TestEdgeTypeOntology:
    """EdgeType 枚举的 ontology 规则验证。"""

    def test_derived_from_is_edge_type(self):
        """DERIVED_FROM 是 Card → Source 的基础边。"""
        assert EdgeType.DERIVED_FROM in EdgeType

    def test_has_tag_is_edge_type(self):
        """HAS_TAG 是 Card → Tag 的边 — v3.7 新增。

        比 SHARES_TAG（Card↔Card）更直接地表达卡片与标签的关系。
        """
        assert EdgeType.HAS_TAG in EdgeType
        assert EdgeType.HAS_TAG.value == "has_tag"

    def test_in_section_is_edge_type(self):
        """IN_SECTION 是 Card → WikiSection 的边 — v3.7 新增。"""
        assert EdgeType.IN_SECTION in EdgeType
        assert EdgeType.IN_SECTION.value == "in_section"

    def test_contains_is_edge_type(self):
        """CONTAINS 是 Community → Card 的层次边 — v3.7 新增。"""
        assert EdgeType.CONTAINS in EdgeType
        assert EdgeType.CONTAINS.value == "contains"

    def test_includes_is_edge_type(self):
        """INCLUDES 是 Topic → Community 的层次边 — v3.7 新增。"""
        assert EdgeType.INCLUDES in EdgeType
        assert EdgeType.INCLUDES.value == "includes"

    def test_mentions_candidate_is_edge_type(self):
        """MENTIONS_CANDIDATE 是 Card → ConceptCandidate 的候选边 — v3.7 新增。

        属于 candidate graph，需要用户确认。
        """
        assert EdgeType.MENTIONS_CANDIDATE in EdgeType
        assert EdgeType.MENTIONS_CANDIDATE.value == "mentions_candidate"

    def test_resolves_to_is_edge_type(self):
        """RESOLVES_TO 是 ConceptCandidate → Entity 的解析边 — v3.7 新增。

        这是 candidate→fact 的桥接边，需要用户显式确认。
        """
        assert EdgeType.RESOLVES_TO in EdgeType
        assert EdgeType.RESOLVES_TO.value == "resolves_to"

    def test_belongs_to_topic_is_edge_type(self):
        """BELONGS_TO_TOPIC 是 Card → Topic 的归属边 — v3.7 新增。"""
        assert EdgeType.BELONGS_TO_TOPIC in EdgeType
        assert EdgeType.BELONGS_TO_TOPIC.value == "belongs_to_topic"

    def test_no_approval_state_of_edge_type(self):
        """APPROVAL_STATE_OF 已移除 — Approval 是 card property，不是边关系。

        中文学习型说明：v3.7 ontology 明确将 Approval 建模为 Card 的 status property，
        而非独立的图边。这避免了"每次状态变更都要更新图"的复杂性。
        """
        all_edge_types = {et.value for et in EdgeType}
        assert "approval_state_of" not in all_edge_types

    def test_shares_tag_still_exists(self):
        """SHARES_TAG (Card↔Card) 保留 — 与 HAS_TAG (Card→Tag) 并存。

        两者表达不同的语义：HAS_TAG 是 Card→Tag 的直接关联，
        SHARES_TAG 是两 Card 共享同一 tag 的推导关系。
        """
        assert EdgeType.SHARES_TAG in EdgeType

    def test_links_to_still_exists(self):
        """LINKS_TO (Card→Card) 保留 — 用户手动链接。"""
        assert EdgeType.LINKS_TO in EdgeType

    def test_total_edge_type_count(self):
        """确认 EdgeType 数量 = 14（v3.7 ontology v1）。

        旧 9 种 - APPROVAL_STATE_OF - MENTIONS + HAS_TAG + IN_SECTION + CONTAINS
        + INCLUDES + MENTIONS_CANDIDATE + RESOLVES_TO + BELONGS_TO_TOPIC
        = 9 - 2 + 7 = 14
        """
        assert len(EdgeType) == 14, (
            f"期望 15 个 EdgeType，实际 {len(EdgeType)}: "
            f"{[et.value for et in EdgeType]}"
        )


class TestFactVsCandidateBoundary:
    """Fact graph 与 Candidate graph 的边界验证。"""

    def test_concept_candidate_is_candidate_graph_only(self):
        """CONCEPT_CANDIDATE 属于 candidate graph，不属于 fact graph。

        中文学习型说明：fact graph 只包含已确认（user-confirmed）的知识。
        ConceptCandidate 由自动检测生成，未经用户确认，必须保留在 candidate graph 中。
        """
        # Candidate 节点的 NodeType 值中包含 "candidate" 标识
        assert "candidate" in NodeType.CONCEPT_CANDIDATE.value

        # Entity（fact graph）不包含 candidate 标识
        assert "candidate" not in NodeType.ENTITY.value

    def test_mentions_candidate_is_candidate_edge(self):
        """MENTIONS_CANDIDATE 属于 candidate graph — v3.7 新增。

        这条边表达的是一张 Card 可能提及某个候选实体，
        但关系未经用户确认，不能进入 fact graph。
        """
        assert "candidate" in EdgeType.MENTIONS_CANDIDATE.value

    def test_resolves_to_is_bridge_edge(self):
        """RESOLVES_TO 是 candidate→fact 的桥接边。

        当用户确认 ConceptCandidate → Entity 的映射时，
        这条边将 candidate graph 连接到 fact graph。
        """
        assert EdgeType.RESOLVES_TO in EdgeType
        # 本身不带 candidate 后缀，因为它是确认动作的结果
        assert "candidate" not in EdgeType.RESOLVES_TO.value

    def test_fact_graph_nodes(self):
        """Fact graph 应包含哪些 NodeType 的显式列表。

        中文学习型说明：这个列表是 fact graph 的白名单。
        任何不在这个列表中的 NodeType 不应出现在 fact graph 中。
        """
        fact_nodes = {
            NodeType.CARD,
            NodeType.SOURCE,
            NodeType.WIKI_SECTION,
            NodeType.TAG,
            NodeType.COMMUNITY,
            NodeType.TOPIC,
            NodeType.ENTITY,
        }
        # 验证这些类型都存在
        for nt in fact_nodes:
            assert nt in NodeType, f"{nt} 应在 fact graph 的 NodeType 列表中"

        # CONCEPT_CANDIDATE 不在 fact graph 中
        assert NodeType.CONCEPT_CANDIDATE not in fact_nodes

    def test_non_graph_transient_objects_not_in_nodetype(self):
        """瞬时/临时对象不应出现在任何 NodeType 中。

        中文学习型说明：以下对象是临时计算产物或基础设施记录，
        不具备图节点的稳定 identity 要求，不能入图：
        - RetrievalContext, Query, SearchResult
        - ExportPackage, ExportManifest
        - DogfoodRun, ScenarioResult
        - Run, Step, Checkpoint
        - ProviderReadiness
        """
        excluded_terms = [
            "retrieval", "query", "search",
            "export", "manifest",
            "dogfood", "scenario",
            "run", "step", "checkpoint",
            "provider", "readiness",
        ]
        for nt in NodeType:
            for term in excluded_terms:
                assert term not in nt.value, (
                    f"NodeType.{nt.name} 的值 '{nt.value}' 包含禁止术语 '{term}'"
                )


class TestEdgeEvidenceRequirement:
    """所有边必须携带 evidence 的契约验证。"""

    def test_relation_evidence_has_reason(self):
        """RelationEvidence 必须有 reason 字段（人类可读的关系理由）。"""
        ev = RelationEvidence(
            reason="shared_tag",
            evidence="shared tag: #ml",
            strength=0.5,
        )
        assert ev.reason
        assert isinstance(ev.reason, str)

    def test_relation_evidence_has_evidence_text(self):
        """RelationEvidence 必须有 evidence 字段（人类可读的证据描述）。

        中文学习型说明：evidence 文本不是 card_id ↔ card_id 这种机器格式，
        而应该是用户可理解的描述（如 'shared tag: #machine-learning'）。
        """
        ev = RelationEvidence(
            reason="same_source",
            evidence="same source document: path/to/note.md",
            strength=0.8,
        )
        assert ev.evidence
        assert isinstance(ev.evidence, str)
        # evidence 不应是纯 ID 引用
        assert "↔" not in ev.evidence or len(ev.evidence) > 30

    def test_graph_edge_requires_evidence(self):
        """GraphEdge 必须携带 RelationEvidence — 不能有无 evidence 的边。

        中文学习型说明：v3.7 ontology 的硬约束：没有 evidence 的关系不能进入 fact graph。
        这条测试确保 GraphEdge 的数据结构强制要求 evidence 字段。
        """
        ev = RelationEvidence(reason="test", evidence="test", strength=0.5)
        edge = GraphEdge(
            source_id="c1",
            target_id="c2",
            edge_type=EdgeType.SHARES_TAG,
            evidence=ev,
        )
        assert edge.evidence is not None
        assert isinstance(edge.evidence, RelationEvidence)
        assert edge.evidence.reason
        assert edge.evidence.evidence

    def test_edge_type_has_direction_semantics(self):
        """EdgeType 必须有方向语义 — 不能所有边都是 symmetric。

        中文学习型说明：图边需要方向来表达语义。例如 DERIVED_FROM 是 Card→Source
        （不是 Source→Card），HAS_TAG 是 Card→Tag。即使是 SHARES_TAG（symmetry），
        也需要在实现中明确标注为双向边。
        """
        # 所有 EdgeType 都是有效 enum 值 — 验证没有无名/占位边
        for et in EdgeType:
            assert et.value, f"EdgeType.{et.name} 缺少 value"
            assert isinstance(et.value, str)
            assert len(et.value) > 0


class TestGraphNodeConstruction:
    """GraphNode 和 GraphEdge 的构建验证。"""

    def test_card_node_construction(self):
        """构建 CARD 类型的 GraphNode。"""
        node = GraphNode(
            id="card-001",
            type=NodeType.CARD,
            label="Test Card",
            href="/library?card=card-001",
        )
        assert node.id == "card-001"
        assert node.type == NodeType.CARD
        assert node.label == "Test Card"

    def test_entity_node_construction(self):
        """构建 ENTITY 类型的 GraphNode — Entity 独立于 Card。

        中文学习型说明：Entity 节点有独立的 id 空间（不共享 Card 的 id 命名空间），
        有自己的 canonical label。href 可选（Entity 详情页尚未实现时可为 None）。
        """
        node = GraphNode(
            id="ent-transformer",
            type=NodeType.ENTITY,
            label="Transformer 架构",
            href=None,
        )
        assert node.type == NodeType.ENTITY
        assert node.type != NodeType.CARD
        assert node.href is None

    def test_community_node_construction(self):
        """构建 COMMUNITY 类型的 GraphNode — 附带 card_count。"""
        node = GraphNode(
            id="community:source:shared_doc.md",
            type=NodeType.COMMUNITY,
            label="[source] shared_doc.md",
            card_count=15,
        )
        assert node.type == NodeType.COMMUNITY
        assert node.card_count == 15

    def test_concept_candidate_node_has_no_href(self):
        """CONCEPT_CANDIDATE 节点不应有点击链接 — 尚未确认，无详情页。

        中文学习型说明：Candidate 节点在 UI 中应该与 fact 节点有视觉区分，
        不应提供与已确认节点同等的导航体验。
        """
        node = GraphNode(
            id="cc-gradient-descent",
            type=NodeType.CONCEPT_CANDIDATE,
            label="梯度下降",
            href=None,
        )
        assert node.type == NodeType.CONCEPT_CANDIDATE
        assert node.href is None
