"""Lab/Internal web service — graph, sensemaking, discovery, community, topic.

中文学习型说明：这个 service 包含来自 web_facade 的 lab/internal 方法。
分离目的是物理隔离主路径代码和 lab 代码，使 web_facade 成为干净的
orchestration facade。

所有方法标记 LAB/INTERNAL — 不是主路径产品功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mindforge.config import MindForgeConfig
    from mindforge_web.schemas import (
        DiscoveryContextResponse,
        GraphEdgeDetailResponse,
        GraphResponse,
        KnowledgeCommunitiesResponse,
        KnowledgeTopicsResponse,
        SensemakingResponse,
    )


class WebLabService:
    """Lab/Internal web service — graph, sensemaking, discovery, community, topic.

    中文学习型说明：此 service 从 web_facade 中提取。所有方法标记 LAB/INTERNAL。
    Router 不应直接调用此 service；通过 web_facade 委托。
    """

    def __init__(self, cfg: MindForgeConfig) -> None:
        self._cfg = cfg

    # -- Knowledge Communities ---------------------------------------------------

    def knowledge_communities(self) -> KnowledgeCommunitiesResponse:
        """检测知识社区（source/tag/wiki_section 分组）— v2.1 增强。"""
        from mindforge.relations.community import detect_communities
        from mindforge_web.schemas import (
            KnowledgeCommunitiesResponse,
            KnowledgeCommunityResponse,
            SubCommunityRefResponse,
            CommunityOverlapResponse,
        )
        from mindforge_web.presenters import build_graph_builder

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return KnowledgeCommunitiesResponse(communities=[])

        communities = detect_communities(builder._cards, min_members=2)
        return KnowledgeCommunitiesResponse(
            communities=[
                KnowledgeCommunityResponse(
                    community_type=c.community_type,
                    shared_entity=c.shared_entity,
                    member_count=c.member_count,
                    member_card_ids=list(c.member_card_ids),
                    description=c.description,
                    sub_communities=[
                        SubCommunityRefResponse(
                            community_type=s.community_type,
                            shared_entity=s.shared_entity,
                            member_count=s.member_count,
                        )
                        for s in c.sub_communities
                    ],
                    overlap_with=[
                        CommunityOverlapResponse(
                            community_type=o.community_type,
                            shared_entity=o.shared_entity,
                            shared_member_count=o.shared_member_count,
                            shared_member_ids=list(o.shared_member_ids),
                        )
                        for o in c.overlap_with
                    ],
                    quality_score=c.quality_score,
                    representative_card_ids=list(c.representative_card_ids),
                    source_coverage=c.source_coverage,
                    evidence_detail=c.evidence_detail,
                )
                for c in communities
            ],
        )

    # -- Knowledge Topics --------------------------------------------------------

    def knowledge_topics(self) -> KnowledgeTopicsResponse:
        """合成知识主题（v3.3 交叉社区合并为更宽泛主题）。"""
        from mindforge.relations.community import detect_communities
        from mindforge.relations.topic import detect_topics
        from mindforge_web.schemas import (
            KnowledgeTopicsResponse,
            KnowledgeTopicResponse,
            TopicMemberCommunityResponse,
        )
        from mindforge_web.presenters import build_graph_builder

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return KnowledgeTopicsResponse(topics=[])

        communities = detect_communities(builder._cards, min_members=2)
        topics = detect_topics(communities, builder._cards)
        return KnowledgeTopicsResponse(
            topics=[
                KnowledgeTopicResponse(
                    topic_id=t.topic_id,
                    topic_name=t.topic_name,
                    community_count=t.community_count,
                    total_card_count=t.total_card_count,
                    card_ids=list(t.card_ids),
                    member_communities=[
                        TopicMemberCommunityResponse(
                            community_type=mc.community_type,
                            shared_entity=mc.shared_entity,
                            member_count=mc.member_count,
                            quality_score=mc.quality_score,
                        )
                        for mc in t.member_communities
                    ],
                    representative_card_ids=list(t.representative_card_ids),
                    evidence=t.evidence,
                )
                for t in topics
            ],
        )

    # -- Graph API ---------------------------------------------------------------

    def get_graph_node(self, ref: str, *, depth: int = 2) -> GraphResponse | None:
        """以卡片为中心的图。"""
        from mindforge.relations.graph_models import NodeType
        from mindforge_web.presenters import (
            build_graph_builder,
            build_graph_response,
            resolve_card_id,
        )

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return None
        card_id = resolve_card_id(self._cfg, ref)
        if card_id is None:
            return None
        graph = builder.get_graph(card_id, NodeType.CARD, depth=depth)
        return build_graph_response(graph)

    def get_graph_explore(
        self, node_type: str, node_id: str, *, depth: int = 1,
    ) -> GraphResponse | None:
        """以已支持的 NodeType 为中心的图浏览（v4.2 truth reset）。"""
        from mindforge.relations.graph_models import NodeType
        from mindforge_web.presenters import (
            build_graph_builder,
            build_graph_response,
        )

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return None
        try:
            nt = NodeType(node_type)
        except ValueError:
            return None
        if nt not in {
            NodeType.CARD,
            NodeType.SOURCE,
            NodeType.TAG,
            NodeType.WIKI_SECTION,
        }:
            return None
        graph = builder.get_graph(node_id, nt, depth=depth)
        return build_graph_response(graph)

    def get_graph_edge(
        self, source: str, target: str,
    ) -> GraphEdgeDetailResponse | None:
        """查询两节点间的所有边及其可解释证据。"""
        from mindforge_web.schemas import GraphEdgeDetailResponse
        from mindforge_web.presenters import (
            build_graph_builder,
            build_graph_edge_response,
        )

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return None
        edges = builder.get_edges(source, direction="outgoing")
        matching = [e for e in edges if e.target_id == target]
        if not matching:
            return None
        return GraphEdgeDetailResponse(
            source_id=source,
            target_id=target,
            edges=[build_graph_edge_response(e) for e in matching],
        )

    # -- Sensemaking -------------------------------------------------------------

    def get_sensemaking(self, ref: str) -> SensemakingResponse | None:
        """获取以卡片为中心的综合 sensemaking 分析（v4.0）。"""
        from mindforge.relations.sensemaking import analyze_sensemaking
        from mindforge_web.schemas import (
            SensemakingBridgeNodeResponse,
            SensemakingCardEvolutionResponse,
            SensemakingCardEvolutionStepResponse,
            SensemakingCommunitySubgraphResponse,
            SensemakingEvidenceTrailItemResponse,
            SensemakingEvidenceTrailResponse,
            SensemakingOrphanIslandResponse,
            SensemakingResponse,
            SensemakingSourceInfluenceResponse,
        )
        from mindforge_web.presenters import (
            build_graph_builder,
            resolve_card_id,
        )

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return None
        card_id = resolve_card_id(self._cfg, ref)
        if card_id is None:
            return None

        analysis = analyze_sensemaking(card_id, builder._cards)
        if analysis is None:
            return None

        return SensemakingResponse(
            center_card_id=analysis.center_card_id,
            center_card_title=analysis.center_card_title,
            bridge_nodes=[
                SensemakingBridgeNodeResponse(
                    card_id=b.card_id,
                    card_title=b.card_title,
                    connecting_communities=list(b.connecting_communities),
                    community_count=b.community_count,
                )
                for b in analysis.bridge_nodes
            ],
            orphan_islands=[
                SensemakingOrphanIslandResponse(
                    card_ids=list(o.card_ids),
                    card_titles=list(o.card_titles),
                    size=o.size,
                    is_true_orphan=o.is_true_orphan,
                )
                for o in analysis.orphan_islands
            ],
            evidence_trails=[
                SensemakingEvidenceTrailResponse(
                    source_id=t.source_id,
                    source_title=t.source_title,
                    target_id=t.target_id,
                    target_title=t.target_title,
                    trail_items=[
                        SensemakingEvidenceTrailItemResponse(
                            evidence_type=ti.evidence_type,
                            evidence_label=ti.evidence_label,
                            description=ti.description,
                        )
                        for ti in t.trail_items
                    ],
                    total_shared_entities=t.total_shared_entities,
                )
                for t in analysis.evidence_trails
            ],
            source_influence=(
                SensemakingSourceInfluenceResponse(
                    source_id=analysis.source_influence.source_id,
                    source_label=analysis.source_influence.source_label,
                    direct_cards=list(analysis.source_influence.direct_cards),
                    direct_card_titles=list(analysis.source_influence.direct_card_titles),
                    influenced_cards=list(analysis.source_influence.influenced_cards),
                    influenced_card_titles=list(analysis.source_influence.influenced_card_titles),
                    total_reach=analysis.source_influence.total_reach,
                )
                if analysis.source_influence else None
            ),
            card_evolution=(
                SensemakingCardEvolutionResponse(
                    source_id=analysis.card_evolution.source_id,
                    source_label=analysis.card_evolution.source_label,
                    steps=[
                        SensemakingCardEvolutionStepResponse(
                            card_id=s.card_id,
                            card_title=s.card_title,
                            tags=list(s.tags),
                            wiki_sections=list(s.wiki_sections),
                        )
                        for s in analysis.card_evolution.steps
                    ],
                    step_count=analysis.card_evolution.step_count,
                )
                if analysis.card_evolution else None
            ),
            community_subgraphs=[
                SensemakingCommunitySubgraphResponse(
                    community_type=sg.community_type,
                    community_label=sg.community_label,
                    member_card_ids=list(sg.member_card_ids),
                    member_card_titles=list(sg.member_card_titles),
                    member_count=sg.member_count,
                    internal_edge_count=sg.internal_edge_count,
                    bridge_card_ids=list(sg.bridge_card_ids),
                )
                for sg in analysis.community_subgraphs
            ],
            total_cards_analyzed=analysis.total_cards_analyzed,
        )

    # -- Discovery Context -------------------------------------------------------

    def get_discovery_context(self, ref: str) -> DiscoveryContextResponse | None:
        """获取以卡片为中心的 graph-aware 发现上下文（R6）。"""
        from mindforge.relations.discovery_context import assemble_discovery_context
        from mindforge.relations.graph_models import NodeType
        from mindforge_web.presenters import (
            build_discovery_context_response,
            build_graph_builder,
            get_center_card_communities,
            resolve_card_id,
        )

        builder = build_graph_builder(self._cfg)
        if builder is None:
            return None
        card_id = resolve_card_id(self._cfg, ref)
        if card_id is None:
            return None
        graph = builder.get_graph(card_id, NodeType.CARD, depth=2)
        communities = get_center_card_communities(card_id, builder._cards)
        ctx = assemble_discovery_context(graph, communities=communities)
        return build_discovery_context_response(ctx)
