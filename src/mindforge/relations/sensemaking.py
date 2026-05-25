"""v4.0 Graph-backed Sensemaking — 基于图分析的知识理解工具。

中文学习型说明：本模块提供 sensemaking workspace 所需的分析原语：
- bridge node detection（连接多个社区的桥接卡片）
- orphan island detection（无共享关系的孤立卡片群）
- evidence trail（边的完整溯源链）
- source influence path（源文档的影响传播路径）
- card evolution path（同源卡片的知识演化）

所有分析基于确定性规则（集合运算 + 图遍历），不调用 LLM / embedding / vector DB。
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


# ── Data Types ─────────────────────────────────────


@dataclass(frozen=True)
class BridgeNode:
    """连接多个知识社区的桥接卡片。

    中文学习型说明：当一张卡片同时属于 2+ 个不同的 source/tag/wiki_section
    社区时，它是桥接节点 — 连接不同知识领域的关键卡片。
    """

    card_id: str
    card_title: str
    connecting_communities: tuple[str, ...]
    """桥接卡片所属的社区标识列表（如 source path、tag name、section title）。"""
    community_count: int
    """桥接的社区数量。"""


@dataclass(frozen=True)
class OrphanIsland:
    """孤立卡片群 — 与其他卡片无共享关系的卡片组。

    中文学习型说明：orphan island 有两种形式：
    - 真正的孤儿：单张卡片，没有任何共享 tag/wiki_section/source
    - 孤立孤岛：2-3 张卡片的小群组，组内有关联但组外完全孤立
    """

    card_ids: tuple[str, ...]
    card_titles: tuple[str, ...]
    size: int
    is_true_orphan: bool
    """True 表示单张卡片完全孤立（无任何边）。"""


@dataclass(frozen=True)
class EvidenceTrailItem:
    """边的证据溯源项。

    中文学习型说明：每条边可能对应多种共享实体（shared_tags、shared_sections、
    shared_source），每一项都记录着这条关系的"为什么"。
    """

    evidence_type: str  # "shared_tag" | "shared_source" | "shared_wiki_section" | ...
    evidence_label: str  # 人类可读的共享实体名称
    description: str  # 溯源说明


@dataclass(frozen=True)
class EvidenceTrail:
    """两节点间关系的完整溯源链。"""

    source_id: str
    source_title: str
    target_id: str
    target_title: str
    trail_items: tuple[EvidenceTrailItem, ...]
    total_shared_entities: int


@dataclass(frozen=True)
class SourceInfluencePath:
    """源文档的影响传播路径。

    中文学习型说明：展示从 Source → 直接派生 Card → 间接关联 Card 的
    知识影响传播链。每一层卡片通过 shared_tag/wiki_section 关联。
    """

    source_id: str
    source_label: str
    direct_cards: tuple[str, ...]
    """直接从该 source 派生的卡片 ID 列表。"""
    direct_card_titles: tuple[str, ...]
    influenced_cards: tuple[str, ...]
    """被直接卡片间接影响的卡片 ID 列表（通过共享 tag/wiki_section）。"""
    influenced_card_titles: tuple[str, ...]
    total_reach: int
    """影响传播的总卡片数（直接 + 间接）。"""


@dataclass(frozen=True)
class CardEvolutionStep:
    """同源卡片的知识演化步骤。

    中文学习型说明：来自同一 source 的卡片按某种顺序排列，
    展示知识如何从源文档逐步演化。
    """

    card_id: str
    card_title: str
    tags: tuple[str, ...]
    wiki_sections: tuple[str, ...]


@dataclass(frozen=True)
class CardEvolutionPath:
    """同源卡片的知识演化路径。"""

    source_id: str
    source_label: str
    steps: tuple[CardEvolutionStep, ...]
    step_count: int


@dataclass(frozen=True)
class CommunitySubgraph:
    """社区/主题子图摘要。

    中文学习型说明：以某个社区（source/tag/wiki_section）为中心的
    聚合视图 — 展示该社区包含的卡片及它们之间的关系密度。
    """

    community_type: str  # "source" | "tag" | "wiki_section"
    community_label: str
    member_card_ids: tuple[str, ...]
    member_card_titles: tuple[str, ...]
    member_count: int
    internal_edge_count: int
    """社区内部卡片间的关系边数。"""
    bridge_card_ids: tuple[str, ...]
    """同时属于其他社区的桥接卡片。"""


@dataclass(frozen=True)
class SensemakingAnalysis:
    """以某张卡片为中心的综合 sensemaking 分析结果。

    中文学习型说明：包含桥接节点、孤立岛屿、证据溯源、源影响路径、
    卡片演化路径、社区子图等全部 sensemaking 维度的分析结果。
    """

    center_card_id: str
    center_card_title: str

    bridge_nodes: tuple[BridgeNode, ...]
    orphan_islands: tuple[OrphanIsland, ...]
    evidence_trails: tuple[EvidenceTrail, ...]
    source_influence: SourceInfluencePath | None
    card_evolution: CardEvolutionPath | None
    community_subgraphs: tuple[CommunitySubgraph, ...]

    total_cards_analyzed: int


# ── Community Detection Helpers ──────────────────────


def _build_communities(
    cards: list[dict[str, object]],
) -> dict[str, dict[str, list[str]]]:
    """构建三类社区索引：source / tag / wiki_section → card_ids。

    返回: {"source": {source_id: [card_ids]}, "tag": {...}, "wiki_section": {...}}
    """
    communities: dict[str, dict[str, list[str]]] = {
        "source": defaultdict(list),
        "tag": defaultdict(list),
        "wiki_section": defaultdict(list),
    }

    for card in cards:
        cid = str(card.get("id", ""))
        if not cid:
            continue

        sid = card.get("source_id")
        if sid:
            communities["source"][str(sid)].append(cid)

        for tag in (card.get("tags") or []):
            communities["tag"][str(tag)].append(cid)

        for sec in (card.get("wiki_sections") or []):
            communities["wiki_section"][str(sec)].append(cid)

    return communities


# ── Bridge Node Detection ────────────────────────────


def detect_bridge_nodes(
    cards: list[dict[str, object]],
    *,
    min_communities: int = 2,
) -> list[BridgeNode]:
    """检测连接多个知识社区的桥接卡片。

    中文学习型说明：一张卡片如果属于 2+ 个不同的 source/tag/wiki_section
    社区，它就是桥接节点。这些卡片是知识图谱中的关键连接点。
    """
    communities = _build_communities(cards)

    # card_id → set of community keys ("source:xxx", "tag:yyy", "wiki_section:zzz")
    card_communities: dict[str, set[str]] = defaultdict(set)

    for ctype, groups in communities.items():
        for entity, member_ids in groups.items():
            community_key = f"{ctype}:{entity}"
            for cid in member_ids:
                card_communities[cid].add(community_key)

    # 构建 card_id → title 映射
    card_titles: dict[str, str] = {}
    for card in cards:
        cid = str(card.get("id", ""))
        if cid:
            card_titles[cid] = str(card.get("title", cid))

    bridge_nodes: list[BridgeNode] = []
    for cid, comm_keys in card_communities.items():
        if len(comm_keys) >= min_communities:
            bridge_nodes.append(BridgeNode(
                card_id=cid,
                card_title=card_titles.get(cid, cid),
                connecting_communities=tuple(sorted(comm_keys)),
                community_count=len(comm_keys),
            ))

    bridge_nodes.sort(key=lambda b: -b.community_count)
    return bridge_nodes


# ── Orphan Island Detection ──────────────────────────


def detect_orphan_islands(
    cards: list[dict[str, object]],
    *,
    max_island_size: int = 3,
) -> list[OrphanIsland]:
    """检测无共享关系的孤立卡片群。

    中文学习型说明：通过分析卡片间的共享关系（tag/wiki_section/source），
    找出完全孤立或仅在小群组内连接的卡片。这些是需要用户关注的"知识孤岛"。

    算法：
    1. 构建卡片邻接图（共享 tag/wiki_section/source 即视为相邻）
    2. 找出孤立节点（度为 0）
    3. 找出小连通分量（大小 ≤ max_island_size）
    """
    if not cards:
        return []

    card_ids = [str(c.get("id", "")) for c in cards]
    card_ids = [cid for cid in card_ids if cid]
    card_titles = {
        str(c.get("id", "")): str(c.get("title", c.get("id", "")))
        for c in cards if c.get("id")
    }

    # 构建邻接表
    adjacency: dict[str, set[str]] = {cid: set() for cid in card_ids}

    # 共享 source 的卡片彼此相邻
    source_groups: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        sid = card.get("source_id")
        cid = str(card.get("id", ""))
        if sid and cid:
            source_groups[str(sid)].append(cid)

    for group in source_groups.values():
        for i, cid1 in enumerate(group):
            for cid2 in group[i + 1:]:
                adjacency[cid1].add(cid2)
                adjacency[cid2].add(cid1)

    # 共享 tag 的卡片彼此相邻
    tag_groups: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        cid = str(card.get("id", ""))
        if not cid:
            continue
        for tag in (card.get("tags") or []):
            tag_groups[str(tag)].append(cid)

    for group in tag_groups.values():
        for i, cid1 in enumerate(group):
            for cid2 in group[i + 1:]:
                adjacency[cid1].add(cid2)
                adjacency[cid2].add(cid1)

    # 共享 wiki_section 的卡片彼此相邻
    section_groups: dict[str, list[str]] = defaultdict(list)
    for card in cards:
        cid = str(card.get("id", ""))
        if not cid:
            continue
        for sec in (card.get("wiki_sections") or []):
            section_groups[str(sec)].append(cid)

    for group in section_groups.values():
        for i, cid1 in enumerate(group):
            for cid2 in group[i + 1:]:
                adjacency[cid1].add(cid2)
                adjacency[cid2].add(cid1)

    # DFS 找连通分量
    visited: set[str] = set()
    components: list[list[str]] = []

    for cid in card_ids:
        if cid in visited:
            continue
        # BFS/DFS
        stack = [cid]
        component: list[str] = []
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    stack.append(neighbor)
        components.append(component)

    # 筛选孤立和小连通分量
    # 如果所有卡片都在一个连通分量中，则不视为孤岛（整体连通图）
    total_cards = len(card_ids)
    orphan_islands: list[OrphanIsland] = []
    for comp in components:
        if len(comp) < total_cards and len(comp) <= max_island_size:
            is_true_orphan = len(comp) == 1 and len(adjacency.get(comp[0], set())) == 0
            orphan_islands.append(OrphanIsland(
                card_ids=tuple(sorted(comp)),
                card_titles=tuple(
                    card_titles.get(cid, cid) for cid in sorted(comp)
                ),
                size=len(comp),
                is_true_orphan=is_true_orphan,
            ))

    orphan_islands.sort(key=lambda o: (not o.is_true_orphan, o.size))
    return orphan_islands


# ── Evidence Trail ───────────────────────────────────


def build_evidence_trail(
    card_a_id: str,
    card_b_id: str,
    cards: list[dict[str, object]],
) -> EvidenceTrail | None:
    """构建两卡片间关系的完整溯源链。

    中文学习型说明：对于两张卡片间的每条边，溯源其共享实体
    （tags、wiki_sections、source），生成可解释的证据链。
    """
    card_a = _find_card(card_a_id, cards)
    card_b = _find_card(card_b_id, cards)
    if card_a is None or card_b is None:
        return None

    items: list[EvidenceTrailItem] = []

    # 共享 source
    sid_a = card_a.get("source_id")
    sid_b = card_b.get("source_id")
    if sid_a and sid_b and str(sid_a) == str(sid_b):
        items.append(EvidenceTrailItem(
            evidence_type="shared_source",
            evidence_label=str(sid_a),
            description=f"同一源文档: {sid_a}",
        ))

    # 共享 tags
    tags_a = set(str(t) for t in (card_a.get("tags") or []))
    tags_b = set(str(t) for t in (card_b.get("tags") or []))
    shared_tags = tags_a & tags_b
    for tag in sorted(shared_tags):
        items.append(EvidenceTrailItem(
            evidence_type="shared_tag",
            evidence_label=tag,
            description=f"共享标签: #{tag}",
        ))

    # 共享 wiki_sections
    secs_a = set(str(s) for s in (card_a.get("wiki_sections") or []))
    secs_b = set(str(s) for s in (card_b.get("wiki_sections") or []))
    shared_secs = secs_a & secs_b
    for sec in sorted(shared_secs):
        items.append(EvidenceTrailItem(
            evidence_type="shared_wiki_section",
            evidence_label=sec,
            description=f"同一 Wiki 章节: {sec}",
        ))

    # 标题 token 重叠
    title_a = str(card_a.get("title", ""))
    title_b = str(card_b.get("title", ""))
    from mindforge.relations.entity_resolution import _tokenize
    tokens_a = set(_tokenize(title_a))
    tokens_b = set(_tokenize(title_b))
    shared_tokens = tokens_a & tokens_b
    for token in sorted(shared_tokens)[:5]:  # 最多 5 个
        items.append(EvidenceTrailItem(
            evidence_type="shared_title_token",
            evidence_label=token,
            description=f"标题共享关键词: {token}",
        ))

    if not items:
        return None

    return EvidenceTrail(
        source_id=card_a_id,
        source_title=title_a,
        target_id=card_b_id,
        target_title=title_b,
        trail_items=tuple(items),
        total_shared_entities=len(items),
    )


# ── Source Influence Path ────────────────────────────


def build_source_influence_path(
    source_id: str,
    cards: list[dict[str, object]],
) -> SourceInfluencePath | None:
    """构建源文档的影响传播路径。

    中文学习型说明：从 Source 出发，沿 DERIVED_FROM 边找到直接派生卡片，
    再通过共享 tag/wiki_section 找到间接影响的卡片。
    """
    # 直接派生卡片
    direct: list[dict[str, object]] = []
    all_cards_map: dict[str, dict[str, object]] = {}
    for card in cards:
        cid = str(card.get("id", ""))
        if cid:
            all_cards_map[cid] = card
        sid = card.get("source_id")
        if sid and str(sid) == source_id:
            direct.append(card)

    if not direct:
        return None

    direct_ids = [str(c.get("id", "")) for c in direct]
    direct_titles = [str(c.get("title", c.get("id", ""))) for c in direct]

    # 间接影响：与直接卡片共享 tag/wiki_section 的其他卡片
    influenced: set[str] = set()
    for d_card in direct:
        d_tags = set(str(t) for t in (d_card.get("tags") or []))
        d_secs = set(str(s) for s in (d_card.get("wiki_sections") or []))

        for other in cards:
            oid = str(other.get("id", ""))
            if not oid or oid in direct_ids:
                continue
            o_tags = set(str(t) for t in (other.get("tags") or []))
            o_secs = set(str(s) for s in (other.get("wiki_sections") or []))

            if (d_tags & o_tags) or (d_secs & o_secs):
                influenced.add(oid)

    influenced_ids = sorted(influenced)
    influenced_titles = [
        str(all_cards_map.get(oid, {}).get("title", oid))
        for oid in influenced_ids
    ]

    return SourceInfluencePath(
        source_id=source_id,
        source_label=source_id,
        direct_cards=tuple(direct_ids),
        direct_card_titles=tuple(direct_titles),
        influenced_cards=tuple(influenced_ids),
        influenced_card_titles=tuple(influenced_titles),
        total_reach=len(direct_ids) + len(influenced_ids),
    )


# ── Card Evolution Path ─────────────────────────────


def build_card_evolution_path(
    source_id: str,
    cards: list[dict[str, object]],
) -> CardEvolutionPath | None:
    """构建同源卡片的知识演化路径。

    中文学习型说明：来自同一 source 的卡片按 id 排序（作为简单代理），
    展示知识从源文档逐步演化的过程。未来可基于卡片创建时间或内容相似度排序。
    """
    source_cards: list[dict[str, object]] = []
    for card in cards:
        sid = card.get("source_id")
        if sid and str(sid) == source_id:
            source_cards.append(card)

    if not source_cards:
        return None

    # 按 card id 排序作为简单代理
    source_cards.sort(key=lambda c: str(c.get("id", "")))

    steps = tuple(
        CardEvolutionStep(
            card_id=str(c.get("id", "")),
            card_title=str(c.get("title", c.get("id", ""))),
            tags=tuple(sorted(str(t) for t in (c.get("tags") or []))),
            wiki_sections=tuple(sorted(str(s) for s in (c.get("wiki_sections") or []))),
        )
        for c in source_cards
    )

    return CardEvolutionPath(
        source_id=source_id,
        source_label=source_id,
        steps=steps,
        step_count=len(steps),
    )


# ── Community Subgraphs ──────────────────────────────


def build_community_subgraphs(
    center_card_id: str,
    cards: list[dict[str, object]],
) -> list[CommunitySubgraph]:
    """构建以中心卡片所属社区为核心的子图摘要。"""
    center_card = _find_card(center_card_id, cards)
    if center_card is None:
        return []

    communities = _build_communities(cards)
    bridge_nodes = detect_bridge_nodes(cards)
    bridge_ids = {b.card_id for b in bridge_nodes}

    subgraphs: list[CommunitySubgraph] = []

    # Source community
    sid = center_card.get("source_id")
    if sid:
        member_ids = communities["source"].get(str(sid), [])
        internal_edges = _count_internal_edges(member_ids, communities)
        bridge_in_community = [
            cid for cid in member_ids if cid in bridge_ids
        ]
        subgraphs.append(CommunitySubgraph(
            community_type="source",
            community_label=str(sid),
            member_card_ids=tuple(member_ids),
            member_card_titles=tuple(
                _card_title(cid, cards) for cid in member_ids
            ),
            member_count=len(member_ids),
            internal_edge_count=internal_edges,
            bridge_card_ids=tuple(bridge_in_community),
        ))

    # Tag communities
    center_tags = set(str(t) for t in (center_card.get("tags") or []))
    for tag in sorted(center_tags):
        member_ids = communities["tag"].get(tag, [])
        if len(member_ids) < 2:
            continue
        internal_edges = _count_internal_edges(member_ids, communities)
        bridge_in_community = [
            cid for cid in member_ids if cid in bridge_ids
        ]
        subgraphs.append(CommunitySubgraph(
            community_type="tag",
            community_label=tag,
            member_card_ids=tuple(member_ids),
            member_card_titles=tuple(
                _card_title(cid, cards) for cid in member_ids
            ),
            member_count=len(member_ids),
            internal_edge_count=internal_edges,
            bridge_card_ids=tuple(bridge_in_community),
        ))

    # Wiki section communities
    center_secs = set(str(s) for s in (center_card.get("wiki_sections") or []))
    for sec in sorted(center_secs):
        member_ids = communities["wiki_section"].get(sec, [])
        if len(member_ids) < 2:
            continue
        internal_edges = _count_internal_edges(member_ids, communities)
        bridge_in_community = [
            cid for cid in member_ids if cid in bridge_ids
        ]
        subgraphs.append(CommunitySubgraph(
            community_type="wiki_section",
            community_label=sec,
            member_card_ids=tuple(member_ids),
            member_card_titles=tuple(
                _card_title(cid, cards) for cid in member_ids
            ),
            member_count=len(member_ids),
            internal_edge_count=internal_edges,
            bridge_card_ids=tuple(bridge_in_community),
        ))

    return subgraphs


# ── Comprehensive Sensemaking Analysis ───────────────


def analyze_sensemaking(
    center_card_id: str,
    cards: list[dict[str, object]],
) -> SensemakingAnalysis | None:
    """以某张卡片为中心的综合 sensemaking 分析。

    中文学习型说明：聚合所有 sensemaking 维度（桥接节点、孤立岛屿、
    证据溯源、源影响路径、卡片演化、社区子图）为一次分析结果。
    """
    center_card = _find_card(center_card_id, cards)
    if center_card is None:
        return None

    center_title = str(center_card.get("title", center_card_id))

    # 桥接节点
    bridge_nodes = tuple(detect_bridge_nodes(cards))

    # 孤立岛屿
    orphan_islands = tuple(detect_orphan_islands(cards))

    # 证据溯源：为中心卡片与其每个关联卡片构建 trail
    trails: list[EvidenceTrail] = []
    related = _find_related_cards(center_card_id, cards)
    for related_id in related[:20]:  # 最多 20 条 trail
        trail = build_evidence_trail(center_card_id, related_id, cards)
        if trail:
            trails.append(trail)
    evidence_trails = tuple(trails)

    # 源影响路径
    sid = center_card.get("source_id")
    source_influence = None
    if sid:
        source_influence = build_source_influence_path(str(sid), cards)

    # 卡片演化路径
    card_evolution = None
    if sid:
        card_evolution = build_card_evolution_path(str(sid), cards)

    # 社区子图
    community_subgraphs = tuple(build_community_subgraphs(center_card_id, cards))

    return SensemakingAnalysis(
        center_card_id=center_card_id,
        center_card_title=center_title,
        bridge_nodes=bridge_nodes,
        orphan_islands=orphan_islands,
        evidence_trails=evidence_trails,
        source_influence=source_influence,
        card_evolution=card_evolution,
        community_subgraphs=community_subgraphs,
        total_cards_analyzed=len(cards),
    )


# ── Internal Helpers ────────────────────────────────


def _find_card(
    card_id: str,
    cards: list[dict[str, object]],
) -> dict[str, object] | None:
    for card in cards:
        if str(card.get("id", "")) == card_id:
            return card
    return None


def _card_title(card_id: str, cards: list[dict[str, object]]) -> str:
    card = _find_card(card_id, cards)
    if card:
        return str(card.get("title", card_id))
    return card_id


def _find_related_cards(
    card_id: str,
    cards: list[dict[str, object]],
) -> list[str]:
    """找出与指定卡片共享 tag/wiki_section/source 的所有卡片。"""
    center = _find_card(card_id, cards)
    if center is None:
        return []

    c_tags = set(str(t) for t in (center.get("tags") or []))
    c_secs = set(str(s) for s in (center.get("wiki_sections") or []))
    c_src = center.get("source_id")

    related: set[str] = set()
    for other in cards:
        oid = str(other.get("id", ""))
        if not oid or oid == card_id:
            continue

        o_tags = set(str(t) for t in (other.get("tags") or []))
        o_secs = set(str(s) for s in (other.get("wiki_sections") or []))
        o_src = other.get("source_id")

        if (c_tags & o_tags) or (c_secs & o_secs) or (c_src and o_src and str(c_src) == str(o_src)):
            related.add(oid)

    return sorted(related)


def _count_internal_edges(
    member_ids: list[str],
    communities: dict[str, dict[str, list[str]]],
) -> int:
    """计算社区内部的关系边数（基于共享 tag/wiki_section 的简单估计）。"""
    edge_count = 0
    member_set = set(member_ids)
    # 检查 tag 社区内的交叉
    for tag, tag_members in communities["tag"].items():
        tag_set = set(tag_members)
        overlap = member_set & tag_set
        if len(overlap) >= 2:
            n = len(overlap)
            edge_count += n * (n - 1) // 2

    # 检查 wiki_section 社区内的交叉
    for sec, sec_members in communities["wiki_section"].items():
        sec_set = set(sec_members)
        overlap = member_set & sec_set
        if len(overlap) >= 2:
            n = len(overlap)
            edge_count += n * (n - 1) // 2

    return edge_count


__all__ = [
    "BridgeNode",
    "OrphanIsland",
    "EvidenceTrailItem",
    "EvidenceTrail",
    "SourceInfluencePath",
    "CardEvolutionStep",
    "CardEvolutionPath",
    "CommunitySubgraph",
    "SensemakingAnalysis",
    "detect_bridge_nodes",
    "detect_orphan_islands",
    "build_evidence_trail",
    "build_source_influence_path",
    "build_card_evolution_path",
    "build_community_subgraphs",
    "analyze_sensemaking",
]
