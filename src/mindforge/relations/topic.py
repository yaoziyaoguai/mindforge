"""v3.3 Topic Synthesis — 确定性知识主题合成。

中文学习型说明：借鉴 GraphRAG 的 community hierarchy / topic summaries，
但纯确定性实现，不调用 LLM，不做 embedding。

"主题"（Topic）不同于"社区"（Community）：
- Community = 共享同一具体属性（source/tag/wiki_section）的卡片群
- Topic = 一组相互重叠的社区合并而成的更宽泛知识主题

合成策略：
1. 构建社区重叠图：节点=社区，边=共享成员 ≥ min_overlap 的社区对
2. 找连通分量 → 每个分量 = 一个 Topic
3. Topic 命名：取成员社区中最核心的 shared_entity + 类型标签
4. 代表性卡片：从所有成员社区的代表性卡片中精选
5. 全部确定性计算，每个 Topic 附带 evidence
"""

from __future__ import annotations

from dataclasses import dataclass

from mindforge.relations.community import (
    KnowledgeCommunity,
    select_representative_cards,
)


@dataclass(frozen=True)
class TopicMemberCommunity:
    """Topic 内的成员社区引用。"""

    community_type: str
    shared_entity: str
    member_count: int
    quality_score: float


@dataclass(frozen=True)
class KnowledgeTopic:
    """确定性知识主题（v3.3）。

    属性：
        topic_id: 主题唯一标识
        topic_name: 主题名称（确定性生成）
        community_count: 成员社区数量
        total_card_count: 去重后的总卡片数
        card_ids: 去重后的卡片 ID 集合
        member_communities: 成员社区列表
        representative_card_ids: 代表性卡片（从成员社区中精选）
        evidence: 证据文本（解释为什么这些社区构成一个主题）
    """

    topic_id: str
    topic_name: str
    community_count: int
    total_card_count: int
    card_ids: tuple[str, ...]
    member_communities: tuple[TopicMemberCommunity, ...]
    representative_card_ids: tuple[str, ...]
    evidence: str


def detect_topics(
    communities: list[KnowledgeCommunity],
    cards: list[dict[str, object]],
    *,
    min_overlap: int = 1,
    min_communities: int = 2,
) -> list[KnowledgeTopic]:
    """从社区列表中合成知识主题。

    纯确定性算法：
    1. 构建社区重叠图（共享成员 ≥ min_overlap 的社区对相连）
    2. 并查集找连通分量 → 每个分量 = 一个 Topic
    3. 每个 Topic 选择代表性卡片 + 生成 evidence

    Args:
        communities: 通过 detect_communities() 获得的知识社区列表
        cards: 原始卡片记录（用于选择代表性卡片）
        min_overlap: 两社区相连所需的最小共享成员数
        min_communities: Topic 至少包含的社区数（< min_communities 会被过滤）

    Returns:
        KnowledgeTopic 列表，按 total_card_count 降序排列。
    """
    if len(communities) < min_communities:
        return []

    n = len(communities)

    # 构建邻接表（社区重叠图）
    adj: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        members_i = set(communities[i].member_card_ids)
        for j in range(i + 1, n):
            # 同类型社区不直接相连（它们共享的是同类型属性，不是交叉关系）
            if communities[i].community_type == communities[j].community_type:
                continue
            shared = members_i & set(communities[j].member_card_ids)
            if len(shared) >= min_overlap:
                adj[i].append(j)
                adj[j].append(i)

    # 并查集找连通分量
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in adj[i]:
            union(i, j)

    # 按根节点分组
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # 构建 Topic
    topics: list[KnowledgeTopic] = []
    for root, indices in groups.items():
        if len(indices) < min_communities:
            continue

        member_comms = [communities[i] for i in indices]

        # 去重卡片 ID
        all_card_ids: set[str] = set()
        for mc in member_comms:
            all_card_ids.update(mc.member_card_ids)

        # 收集代表性卡片（从成员社区的代表性卡片 + 额外精选）
        rep_candidates: set[str] = set()
        for mc in member_comms:
            rep_candidates.update(mc.representative_card_ids)
        # 如果代表性卡片不够，从全部成员卡片中补充
        if len(rep_candidates) < 3:
            extra = select_representative_cards(
                "topic",
                list(all_card_ids - rep_candidates),
                cards,
                max_count=3 - len(rep_candidates),
            )
            rep_candidates.update(extra)

        # 主题名称：取最大社区的 shared_entity + 类型标签
        largest = max(member_comms, key=lambda mc: mc.member_count)
        type_label = {"source": "来源", "tag": "标签", "wiki_section": "章节"}.get(
            largest.community_type, largest.community_type
        )
        topic_name = f"「{largest.shared_entity}」{type_label}主题"

        # Topic ID：取成员社区 ID 的排序拼接哈希
        sorted_keys = sorted(_community_key(mc) for mc in member_comms)
        topic_id = "topic-" + str(hash("|".join(sorted_keys)) % 1000000)

        # Evidence
        community_descriptions = [
            f"{mc.community_type}:{mc.shared_entity}({mc.member_count}张)"
            for mc in sorted(member_comms, key=lambda mc: mc.member_count, reverse=True)
        ]
        evidence = (
            f"主题包含 {len(member_comms)} 个交叉社区，共 {len(all_card_ids)} 张卡片。"
            f"成员社区: {'; '.join(community_descriptions[:5])}"
            f"{'...' if len(community_descriptions) > 5 else ''}"
        )

        topics.append(KnowledgeTopic(
            topic_id=topic_id,
            topic_name=topic_name,
            community_count=len(member_comms),
            total_card_count=len(all_card_ids),
            card_ids=tuple(sorted(all_card_ids)),
            member_communities=tuple(
                TopicMemberCommunity(
                    community_type=mc.community_type,
                    shared_entity=mc.shared_entity,
                    member_count=mc.member_count,
                    quality_score=mc.quality_score,
                )
                for mc in sorted(member_comms, key=lambda mc: mc.member_count, reverse=True)
            ),
            representative_card_ids=tuple(sorted(rep_candidates)[:5]),
            evidence=evidence,
        ))

    topics.sort(key=lambda t: t.total_card_count, reverse=True)
    return topics


def _community_key(c: KnowledgeCommunity) -> str:
    """社区唯一标识键。"""
    return f"{c.community_type}:{c.shared_entity}"


__all__ = [
    "KnowledgeTopic",
    "TopicMemberCommunity",
    "detect_topics",
]
