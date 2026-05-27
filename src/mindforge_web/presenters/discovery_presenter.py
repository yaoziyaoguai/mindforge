"""Discovery context response builders — 将检索发现上下文转换为 Web API response。

中文学习型说明：此模块处理 v2.1 增强的 Discovery Context，将 core 层的
DiscoveryContext domain 对象（含 direct_matches、neighbor_cards、wiki_sections、
shared_tags、shared_sources、communities）转换为 Pydantic response 类型。

所有函数都是纯数据变换，无 IO，无副作用。
"""

from __future__ import annotations

from mindforge.relations.discovery_context import (
    DiscoveryCommunityRef,
    DiscoveryContext,
)
from mindforge_web.schemas import (
    DiscoveryCardRefResponse,
    DiscoveryCommunityRefResponse,
    DiscoveryContextResponse,
    DiscoverySectionRefResponse,
    DiscoverySourceRefResponse,
    DiscoveryTagRefResponse,
    ProvenanceTrailRelatedSource,
)


def build_discovery_context_response(ctx: DiscoveryContext) -> DiscoveryContextResponse:
    """将内部 DiscoveryContext 转换为 API response — v2.1 增强。"""
    return DiscoveryContextResponse(
        center_card_id=ctx.center_card_id,
        center_card_title=ctx.center_card_title,
        reasoning=ctx.reasoning,
        estimated_token_count=ctx.estimated_token_count,
        direct_matches=[
            DiscoveryCardRefResponse(
                card_id=ref.card_id,
                title=ref.title,
                relation_reason=ref.relation_reason,
                relation_strength=ref.relation_strength,
                evidence=ref.evidence,
            )
            for ref in ctx.direct_matches
        ],
        neighbor_cards=[
            DiscoveryCardRefResponse(
                card_id=ref.card_id,
                title=ref.title,
                relation_reason=ref.relation_reason,
                relation_strength=ref.relation_strength,
                evidence=ref.evidence,
            )
            for ref in ctx.neighbor_cards
        ],
        wiki_sections=[
            DiscoverySectionRefResponse(
                section_title=s.section_title,
                card_count=s.card_count,
            )
            for s in ctx.wiki_sections
        ],
        shared_tags=[
            DiscoveryTagRefResponse(tag=t.tag, card_count=t.card_count)
            for t in ctx.shared_tags
        ],
        shared_sources=[
            DiscoverySourceRefResponse(source_id=s.source_id, card_count=s.card_count)
            for s in ctx.shared_sources
        ],
        communities=[
            DiscoveryCommunityRefResponse(
                community_type=c.community_type,
                shared_entity=c.shared_entity,
                member_count=c.member_count,
                description=c.description,
            )
            for c in ctx.communities
        ],
    )


def get_center_card_communities(
    center_card_id: str,
    cards: list[dict[str, object]],
) -> tuple[DiscoveryCommunityRef, ...]:
    """检测中心卡片所属的知识社区（v1.2 U4）。

    对所有卡片运行 detect_communities，筛选出包含 center_card_id 的社区，
    返回 DiscoveryCommunityRef 元组。
    """
    from mindforge.relations.community import detect_communities

    all_communities = detect_communities(cards, min_members=2)
    result: list[DiscoveryCommunityRef] = []
    for c in all_communities:
        if center_card_id in c.member_card_ids:
            result.append(DiscoveryCommunityRef(
                community_type=c.community_type,
                shared_entity=c.shared_entity,
                member_count=c.member_count,
                description=c.description,
            ))
    return tuple(result)


def compute_related_sources(
    source_id: str | None,
    approved: list,
) -> list[ProvenanceTrailRelatedSource]:
    """找出与给定 source 通过共享 tags/wiki_sections 关联的其他 source（v1.2 U5）。

    双向探索的关键：从当前 card → source → 找到"哪些其他 source 有相似的知识"。
    """
    if not source_id:
        return []

    # 收集当前 source 的所有 tags 和 wiki_sections
    source_tags: set[str] = set()
    source_sections: set[str] = set()
    for c in approved:
        if c.source_id == source_id:
            for t in c.tags:
                source_tags.add(t)
            for s in c.wiki_sections:
                source_sections.add(s)

    if not source_tags and not source_sections:
        return []

    # 统计其他 source 与当前 source 的共享情况
    related: dict[str, dict] = {}  # source_id → {tags: set, sections: set, cards: set}
    for c in approved:
        sid = c.source_id
        if not sid or sid == source_id:
            continue
        if sid not in related:
            related[sid] = {"tags": set(), "sections": set(), "cards": set(), "title": c.source_title}
        related[sid]["cards"].add(c.id or c.rel_path)
        for t in c.tags:
            if t in source_tags:
                related[sid]["tags"].add(t)
        for s in c.wiki_sections:
            if s in source_sections:
                related[sid]["sections"].add(s)

    # 排序：共享 tag + section 总数降序
    scored = [
        (sid, info) for sid, info in related.items()
        if info["tags"] or info["sections"]
    ]
    scored.sort(key=lambda x: len(x[1]["tags"]) + len(x[1]["sections"]), reverse=True)

    result: list[ProvenanceTrailRelatedSource] = []
    for sid, info in scored[:5]:
        result.append(ProvenanceTrailRelatedSource(
            source_id=sid,
            source_title=info["title"],
            card_count=len(info["cards"]),
            shared_tags=sorted(info["tags"]),
            shared_wiki_sections=sorted(info["sections"]),
        ))

    return result
