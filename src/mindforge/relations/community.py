"""v3.3 Knowledge Community & Topic — 确定性知识社区检测与主题合成。

中文学习型说明：借鉴 GraphRAG 的 community hierarchy / topic summaries 概念，
但完全不使用 LLM、embedding 或社区检测算法。

v3.3 增强：
- 代表性卡片选择（基于质量 + 连接度的确定性启发式）
- 来源覆盖率统计
- 增强 evidence trail（社区归属理由更详细）
- Topic 合成：合并重叠社区为更宽泛知识主题

每个社区/主题附带纯文本证据（非 LLM 生成），让用户理解"为什么这些知识在一起"。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict


@dataclass(frozen=True)
class SubCommunityRef:
    """子社区引用（用于多层级分组）。

    当某个社区 A 的成员完全包含社区 B 的成员时，B 是 A 的子社区。
    层级方向：source → tag → wiki_section（source 最宽泛，wiki_section 最具体）。
    """

    community_type: str  # "source" | "tag" | "wiki_section"
    shared_entity: str
    member_count: int


@dataclass(frozen=True)
class CommunityOverlap:
    """社区重叠信息。

    两个不同类型的社区如果共享至少 1 个成员，即存在重叠。
    重叠信息记录共享成员详情，便于用户理解"知识之间的交叉关系"。
    """

    community_type: str
    shared_entity: str
    shared_member_count: int
    shared_member_ids: tuple[str, ...]


@dataclass(frozen=True)
class KnowledgeCommunity:
    """确定性知识社区（v3.3 增强）。

    属性：
        community_type: 社区类型（source / tag / wiki_section）
        shared_entity: 共享实体名称（source path / tag name / section title）
        member_count: 成员卡片数量
        member_card_ids: 成员卡片 ID 列表
        description: 确定性文本描述（非 LLM 生成）
        sub_communities: 子社区列表
        overlap_with: 重叠社区列表
        quality_score: 社区质量评分 0.0-1.0
        representative_card_ids: 代表性卡片（v3.3 质量+连接度启发式选择）
        source_coverage: 来源覆盖率 0.0-1.0（v3.3）
        evidence_detail: 增强证据文本（v3.3）
    """

    community_type: str  # "source", "tag", "wiki_section"
    shared_entity: str
    member_count: int
    member_card_ids: tuple[str, ...]
    description: str
    sub_communities: tuple[SubCommunityRef, ...] = field(default_factory=tuple)
    overlap_with: tuple[CommunityOverlap, ...] = field(default_factory=tuple)
    quality_score: float = 0.0
    representative_card_ids: tuple[str, ...] = field(default_factory=tuple)
    source_coverage: float = 0.0
    evidence_detail: str = ""


def _card_quality(card: dict[str, object]) -> float:
    """计算单张卡片的质量评分（0.0-1.0）。

    评分维度（纯确定性，不调用 LLM）：
    - 有来源文档（provenance）: +0.2
    - 有标签: +0.1/标签（最多 +0.3）
    - 有 Wiki 章节归属: +0.1/章节（最多 +0.3）
    - body 长度 > 100 字符: +0.2
    - status 为 human_approved: +0.2
    """
    score = 0.0

    if card.get("source_id"):
        score += 0.2

    tags = card.get("tags") or []
    if isinstance(tags, list):
        score += min(len(tags) * 0.1, 0.3)

    wiki_sections = card.get("wiki_sections") or []
    if isinstance(wiki_sections, list):
        score += min(len(wiki_sections) * 0.1, 0.3)

    body = card.get("body")
    if isinstance(body, str) and len(body) > 100:
        score += 0.2

    status = card.get("status")
    if status == "human_approved":
        score += 0.2

    return min(score, 1.0)


def _build_community_key(c: KnowledgeCommunity) -> str:
    """生成社区的唯一标识键（类型 + 实体名）。"""
    return f"{c.community_type}:{c.shared_entity}"


def _build_hierarchy(
    communities: list[KnowledgeCommunity],
) -> None:
    """为每个社区计算子社区列表（原地修改）。

    规则：社区 B 是社区 A 的子社区，当且仅当：
    - B.member_card_ids 是 A.member_card_ids 的子集
    - B.community_type ≠ A.community_type
    - 层级方向：source → tag → wiki_section（source 最宽泛）
    """
    if len(communities) < 2:
        return

    type_order = {"source": 0, "tag": 1, "wiki_section": 2}

    for i, parent in enumerate(communities):
        parent_members = set(parent.member_card_ids)
        sub_refs: list[SubCommunityRef] = []
        for j, child in enumerate(communities):
            if i == j:
                continue
            if child.community_type == parent.community_type:
                continue
            # 只允许从宽泛到具体的层级方向
            if type_order.get(child.community_type, 99) <= type_order.get(parent.community_type, 0):
                continue
            child_members = set(child.member_card_ids)
            if child_members.issubset(parent_members) and child_members:
                sub_refs.append(SubCommunityRef(
                    community_type=child.community_type,
                    shared_entity=child.shared_entity,
                    member_count=child.member_count,
                ))
        if sub_refs:
            # 使用 object.__setattr__ 绕过 frozen=True
            object.__setattr__(parent, "sub_communities", tuple(sub_refs))


def _detect_overlaps(
    communities: list[KnowledgeCommunity],
) -> None:
    """为每个社区检测重叠社区（原地修改）。

    规则：两个社区 A、B 存在重叠，当且仅当：
    - A 和 B 是不同类型的社区
    - A 和 B 共享至少 1 个成员卡片
    """
    if len(communities) < 2:
        return

    for i, comm_a in enumerate(communities):
        members_a = set(comm_a.member_card_ids)
        overlaps: list[CommunityOverlap] = []
        for j, comm_b in enumerate(communities):
            if i == j:
                continue
            if comm_b.community_type == comm_a.community_type:
                continue
            shared = members_a & set(comm_b.member_card_ids)
            if shared:
                overlaps.append(CommunityOverlap(
                    community_type=comm_b.community_type,
                    shared_entity=comm_b.shared_entity,
                    shared_member_count=len(shared),
                    shared_member_ids=tuple(sorted(shared)),
                ))
        if overlaps:
            object.__setattr__(comm_a, "overlap_with", tuple(overlaps))


def detect_communities(
    cards: list[dict[str, object]],
    *,
    min_members: int = 2,
) -> list[KnowledgeCommunity]:
    """从卡片列表中检测知识社区。

    v2.1 增强：自动计算多层级分组、社区质量评分、社区重叠检测。
    所有计算均为确定性算法，不调用 LLM，不做 embedding。

    Args:
        cards: 卡片记录列表，每张卡片至少包含 id 字段，
               可选包含 source_id、tags、wiki_sections、body、status。
        min_members: 最少成员数阈值（社区至少需要 N 张卡片）

    Returns:
        KnowledgeCommunity 列表，按 member_count 降序排列。
        每个社区附带 sub_communities（子社区层级）、
        overlap_with（重叠社区）和 quality_score（质量评分）。
    """
    communities: list[KnowledgeCommunity] = []

    # --- 成员卡片质量预处理 ---
    card_qualities: dict[str, float] = {
        str(c["id"]): _card_quality(c) for c in cards
    }

    # --- Source communities ---
    source_groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        sid = c.get("source_id")
        if sid:
            source_groups[str(sid)].append(str(c["id"]))

    for src, member_ids in source_groups.items():
        if len(member_ids) >= min_members:
            communities.append(KnowledgeCommunity(
                community_type="source",
                shared_entity=src,
                member_count=len(member_ids),
                member_card_ids=tuple(member_ids),
                description=_source_description(src, len(member_ids)),
                quality_score=_avg_quality(member_ids, card_qualities),
            ))

    # --- Tag communities ---
    tag_groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for tag in (c.get("tags") or []):
            tag_groups[str(tag)].append(str(c["id"]))

    for tag, member_ids in tag_groups.items():
        if len(member_ids) >= min_members:
            communities.append(KnowledgeCommunity(
                community_type="tag",
                shared_entity=f"#{tag}",
                member_count=len(member_ids),
                member_card_ids=tuple(member_ids),
                description=_tag_description(tag, len(member_ids)),
                quality_score=_avg_quality(member_ids, card_qualities),
            ))

    # --- Wiki section communities ---
    section_groups: dict[str, list[str]] = defaultdict(list)
    for c in cards:
        for sec in (c.get("wiki_sections") or []):
            section_groups[str(sec)].append(str(c["id"]))

    for sec, member_ids in section_groups.items():
        if len(member_ids) >= min_members:
            communities.append(KnowledgeCommunity(
                community_type="wiki_section",
                shared_entity=sec,
                member_count=len(member_ids),
                member_card_ids=tuple(member_ids),
                description=_section_description(sec, len(member_ids)),
                quality_score=_avg_quality(member_ids, card_qualities),
            ))

    communities.sort(key=lambda c: c.member_count, reverse=True)

    # --- v2.1: 多层级分组 & 重叠检测 ---
    _build_hierarchy(communities)
    _detect_overlaps(communities)

    # --- v3.3: 代表性卡片、来源覆盖率、增强证据 ---
    _enrich_communities(communities, cards)

    return communities


def _enrich_communities(
    communities: list[KnowledgeCommunity],
    cards: list[dict[str, object]],
) -> None:
    """v3.3 增强：为每个社区计算代表性卡片、来源覆盖率、证据详情（原地修改）。"""
    for i, comm in enumerate(communities):
        member_ids = list(comm.member_card_ids)

        rep_ids = select_representative_cards(
            comm.community_type, member_ids, cards, max_count=3
        )
        src_cov = _compute_source_coverage(member_ids, cards)
        evidence = _build_evidence_detail(
            community_type=comm.community_type,
            shared_entity=comm.shared_entity,
            member_count=comm.member_count,
            source_coverage=src_cov,
            representative_ids=rep_ids,
            sub_count=len(comm.sub_communities),
            overlap_count=len(comm.overlap_with),
        )

        object.__setattr__(communities[i], "representative_card_ids", tuple(rep_ids))
        object.__setattr__(communities[i], "source_coverage", src_cov)
        object.__setattr__(communities[i], "evidence_detail", evidence)


def _avg_quality(member_ids: list[str], qualities: dict[str, float]) -> float:
    """计算社区成员卡片质量的加权平均值。"""
    if not member_ids:
        return 0.0
    total = sum(qualities.get(mid, 0.0) for mid in member_ids)
    return round(total / len(member_ids), 4)


def _source_description(source_path: str, count: int) -> str:
    return f"来自来源文档「{source_path}」的 {count} 张知识卡片"


def _tag_description(tag: str, count: int) -> str:
    return f"共享标签 #{tag} 的 {count} 张知识卡片"


def _section_description(section: str, count: int) -> str:
    return f"属于 Wiki 章节「{section}」的 {count} 张知识卡片"


# ---------------------------------------------------------------------------
# v3.3 增强：代表性卡片、来源覆盖率、增强证据
# ---------------------------------------------------------------------------


def select_representative_cards(
    community_type: str,
    member_card_ids: list[str],
    cards: list[dict[str, object]],
    *,
    max_count: int = 3,
) -> list[str]:
    """为社区选择代表性卡片（基于质量 + 连接度的确定性启发式）。

    选择策略（无 LLM）：
    1. 计算每张卡片的质量分（_card_quality）
    2. 计算连接度分：卡片所在的其他社区数（标签/章节越多的卡片越"中枢"）
    3. 综合分 = 质量分 × 0.6 + 连接度分 × 0.4
    4. 取 top-N

    不调用 LLM，不做 embedding。
    """
    card_map: dict[str, dict[str, object]] = {str(c["id"]): c for c in cards}
    member_cards = [card_map[mid] for mid in member_card_ids if mid in card_map]
    if not member_cards:
        return []

    # 计算连接度（标签数 + wiki 章节数，归一化到 0-1）
    max_connectivity = 0
    scores: dict[str, float] = {}
    for c in member_cards:
        cid = str(c["id"])
        quality = _card_quality(c)
        tags_count = len(c.get("tags") or [])
        sections_count = len(c.get("wiki_sections") or [])
        connectivity = min((tags_count + sections_count) / 6.0, 1.0)
        max_connectivity = max(max_connectivity, connectivity)
        scores[cid] = quality * 0.6 + connectivity * 0.4

    # 按综合分降序取 top-N
    sorted_ids = sorted(scores, key=scores.get, reverse=True)  # type: ignore[arg-type,return-value]
    return sorted_ids[:max_count]


def _compute_source_coverage(
    member_card_ids: list[str],
    cards: list[dict[str, object]],
) -> float:
    """计算社区中具有来源归属的卡片比例。"""
    card_map = {str(c["id"]): c for c in cards}
    member_cards = [card_map[mid] for mid in member_card_ids if mid in card_map]
    if not member_cards:
        return 0.0
    with_source = sum(1 for c in member_cards if c.get("source_id"))
    return round(with_source / len(member_cards), 4)


def _build_evidence_detail(
    community_type: str,
    shared_entity: str,
    member_count: int,
    source_coverage: float,
    representative_ids: list[str],
    sub_count: int,
    overlap_count: int,
) -> str:
    """构建增强证据文本（确定性模板，非 LLM 生成）。

    解释社区为什么存在、卡片如何关联、质量如何。
    """
    type_label = {"source": "来源文档", "tag": "标签", "wiki_section": "Wiki 章节"}.get(
        community_type, community_type
    )

    parts = [f"社区类型: {type_label}「{shared_entity}」", f"成员: {member_count} 张卡片"]

    if representative_ids:
        parts.append(f"代表性卡片: {', '.join(representative_ids[:3])}")

    if source_coverage > 0:
        parts.append(f"来源覆盖率: {source_coverage:.0%}")

    if sub_count > 0:
        parts.append(f"含 {sub_count} 个子社区")

    if overlap_count > 0:
        parts.append(f"与 {overlap_count} 个社区有交叉")

    return " | ".join(parts)


def _detect_community_type_order(community_type: str) -> int:
    """社区类型层级序数（source=0 最宽泛 → wiki_section=2 最具体）。"""
    order = {"source": 0, "tag": 1, "wiki_section": 2}
    return order.get(community_type, 99)


__all__ = [
    "KnowledgeCommunity",
    "SubCommunityRef",
    "CommunityOverlap",
    "detect_communities",
    "select_representative_cards",
]
