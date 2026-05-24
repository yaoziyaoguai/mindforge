"""M3 Related Cards computation — SDD §7, TDD §5。

确定性关系发现：基于 source_id, tags, wiki_sections, run_id,
source_location_index 的字段匹配。
不做 semantic similarity，不引入 embedding，全部 in-memory。

v1.2 升级：引入多因子加权评分（共享实体数量、时效性）。
v2.1 升级：multi-hop BFS 遍历（可配置深度）、路径可见、强度随跳数衰减。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from collections import defaultdict

from mindforge.relations.scoring import (
    RelationWeights,
    compute_tag_strength,
    compute_wiki_strength,
    compute_recency_bonus,
    compute_multi_factor_strength,
)


class RelationReason(str, enum.Enum):
    SAME_SOURCE = "same_source"
    SAME_TAG = "same_tag"
    SAME_WIKI_SECTION = "same_wiki_section"
    SAME_REVIEW_BATCH = "same_review_batch"
    SOURCE_LOCATION_NEIGHBOR = "source_location_neighbor"
    MANUAL_LINK = "manual_link"  # reserved — 当前不发出此边类型


# Base strength weights (v1.2: 基础权重，实际计算由 scoring 模块完成)
_STRENGTH: dict[RelationReason, float] = {
    RelationReason.SAME_SOURCE: 0.8,
    RelationReason.SAME_TAG: 0.5,
    RelationReason.SAME_WIKI_SECTION: 0.7,
    RelationReason.SAME_REVIEW_BATCH: 0.3,
    RelationReason.SOURCE_LOCATION_NEIGHBOR: 0.4,
    RelationReason.MANUAL_LINK: 1.0,
}

# v2.1 multi-hop strength decay: 每增加 1 跳，强度乘以 decay 因子
_HOP_DECAY: float = 0.7


@dataclass(frozen=True)
class RelatedCardEdge:
    source_card_id: str
    target_card_id: str
    reason: RelationReason
    reason_detail: str = ""
    strength: float = 0.5
    # v2.1: multi-hop 信息
    hop_distance: int = 1
    via_path: tuple[str, ...] = field(default_factory=tuple)


def compute_related_cards(
    card_id: str,
    all_cards: list[dict[str, object]],
    *,
    context: str = "library",
) -> list[RelatedCardEdge]:
    """计算单张卡片的确定性 related cards（1-hop，向后兼容）。

    Args:
        card_id: 查询卡片 ID
        all_cards: 所有卡片记录列表，每条为 dict
        context: "library" → 仅 human_approved；"review" → 包含 pending

    Returns:
        RelatedCardEdge 列表，按 strength 降序排列，每种 reason ≤ 5 条。
    """
    return compute_multi_hop_related_cards(card_id, all_cards, context=context, max_depth=1)


# ── v2.1 Multi-hop BFS ──────────────────────────────────────────────


def compute_multi_hop_related_cards(
    card_id: str,
    all_cards: list[dict[str, object]],
    *,
    context: str = "library",
    max_depth: int = 2,
) -> list[RelatedCardEdge]:
    """BFS 多层关系发现（v2.1）。

    从中心卡片出发，逐跳发现关联卡片，每跳强度按 _HOP_DECAY 衰减。
    同一卡片在多跳可达时，保留最短路径。

    Args:
        card_id: 查询卡片 ID
        all_cards: 所有卡片记录列表
        context: "library" → 仅 human_approved；"review" → 包含 pending
        max_depth: 最大跳数（默认 2，即发现 2-hop 邻居）

    Returns:
        RelatedCardEdge 列表，按 (hop_distance, strength) 排序，
        每种 reason ≤ 5 条（per hop）。
    """
    center = _find_card(card_id, all_cards)
    if center is None:
        return []

    card_map: dict[str, dict[str, object]] = {str(c["id"]): c for c in all_cards}

    # 预建索引（一次建好，所有 hop 共用）
    idx = _build_indexes(all_cards, context, exclude_id=card_id)

    # BFS 状态
    # all_edges_by_target: 记录每张目标卡片在最短跳数下的所有 reason edges
    all_edges_by_target: dict[str, list[RelatedCardEdge]] = defaultdict(list)
    visited_for_expansion: set[str] = {card_id}
    # paths[card] = 从 center 到该 card 的完整路径（含 center 和自身）
    paths: dict[str, tuple[str, ...]] = {card_id: (card_id,)}
    # 当前层：需从这些卡片出发发现下一跳邻居
    current_level: set[str] = {card_id}

    for hop in range(1, max_depth + 1):
        next_level: set[str] = set()
        for source_id in current_level:
            source_card = card_map.get(source_id)
            if source_card is None:
                continue
            neighbors = _find_neighbors(source_card, idx, card_map)
            for edge in neighbors:
                # 跳过自引用（intermediate card 匹配自身）和回退到 center 的边
                if edge.target_card_id in (source_id, card_id):
                    continue
                decay = _HOP_DECAY ** (hop - 1)
                # via_path = 从 center 到 source 的路径中，去掉 center 之后的部分
                via = paths.get(source_id, ())[1:]
                hop_edge = RelatedCardEdge(
                    source_card_id=source_id,
                    target_card_id=edge.target_card_id,
                    reason=edge.reason,
                    reason_detail=edge.reason_detail,
                    strength=round(edge.strength * decay, 4),
                    hop_distance=hop,
                    via_path=via,
                )
                # 允许同一 target 有多个 reason edge，但只以最短 hop 扩展
                if edge.target_card_id not in visited_for_expansion:
                    visited_for_expansion.add(edge.target_card_id)
                    next_level.add(edge.target_card_id)
                    paths[edge.target_card_id] = paths.get(source_id, ()) + (edge.target_card_id,)
                all_edges_by_target[edge.target_card_id].append(hop_edge)
        current_level = next_level
        if not current_level:
            break

    # 展平：每个 target 可能有多个 reason edge
    all_edges: list[RelatedCardEdge] = []
    for edges in all_edges_by_target.values():
        all_edges.extend(edges)

    # 按 hop_distance 升序，再按 strength 降序
    all_edges.sort(key=lambda e: (e.hop_distance, -e.strength))

    # 每种 reason 最多 5 条
    reason_counts: dict[RelationReason, int] = defaultdict(int)
    capped: list[RelatedCardEdge] = []
    for e in all_edges:
        if reason_counts[e.reason] < 5:
            capped.append(e)
            reason_counts[e.reason] += 1

    return capped


# ── Index helpers ───────────────────────────────────────────────────


@dataclass(frozen=True)
class _RelationIndex:
    """关系发现所需的预建索引（v2.1 从 compute_related_cards 提取为共享结构）。"""
    source_index: dict[str, list[str]]
    tag_index: dict[str, list[str]]
    section_index: dict[str, list[str]]
    batch_index: dict[str, list[str]]
    location_index: dict[tuple[str, int], list[str]]


def _build_indexes(
    all_cards: list[dict[str, object]],
    context: str,
    exclude_id: str,
) -> _RelationIndex:
    """预建关系发现所需的所有索引。"""
    source_index: dict[str, list[str]] = defaultdict(list)
    tag_index: dict[str, list[str]] = defaultdict(list)
    section_index: dict[str, list[str]] = defaultdict(list)
    batch_index: dict[str, list[str]] = defaultdict(list)
    location_index: dict[tuple[str, int], list[str]] = defaultdict(list)

    for c in all_cards:
        cid = str(c["id"])
        if cid == exclude_id:
            continue
        if context == "library" and c.get("status") != "human_approved":
            continue
        sid = c.get("source_id")
        if sid:
            source_index[str(sid)].append(cid)
        for tag in (c.get("tags") or []):
            tag_index[str(tag)].append(cid)
        for sec in (c.get("wiki_sections") or []):
            section_index[str(sec)].append(cid)
        batch_id = c.get("run_id") or c.get("review_batch")
        if batch_id:
            batch_index[str(batch_id)].append(cid)
        loc_idx = _int_or_none(c.get("source_location_index"))
        if sid and loc_idx is not None:
            location_index[(str(sid), loc_idx)].append(cid)

    return _RelationIndex(
        source_index=source_index,
        tag_index=tag_index,
        section_index=section_index,
        batch_index=batch_index,
        location_index=location_index,
    )


def _find_neighbors(
    center: dict[str, object],
    idx: _RelationIndex,
    card_map: dict[str, dict[str, object]],
) -> list[RelatedCardEdge]:
    """为单张卡片查找直接邻居（1-hop），复用预建索引。

    中文学习型说明：这是从 compute_related_cards 抽取的纯逻辑层。
    不新建索引，只使用传入的 idx 做 O(1) 查找。
    """
    edges: list[RelatedCardEdge] = []
    center_src = center.get("source_id")
    center_tags = set(center.get("tags") or [])
    center_sections = set(center.get("wiki_sections") or [])
    center_batch = center.get("run_id") or center.get("review_batch")
    center_location_index = _int_or_none(center.get("source_location_index"))

    # same_source
    if center_src:
        w = RelationWeights()
        for target in idx.source_index.get(str(center_src), []):
            target_card = card_map.get(target, {})
            recency = compute_recency_bonus(
                str(target_card.get("created_at")) if target_card.get("created_at") else None,
                weights=w,
            )
            strength = compute_multi_factor_strength(
                _STRENGTH[RelationReason.SAME_SOURCE], recency_bonus=recency,
            )
            edges.append(RelatedCardEdge(
                source_card_id=str(center["id"]),
                target_card_id=target,
                reason=RelationReason.SAME_SOURCE,
                reason_detail=f"same source: {center_src}",
                strength=strength,
            ))

    # same_tag
    tag_target_counts: dict[str, int] = defaultdict(int)
    tag_target_first: dict[str, str] = {}
    for tag in center_tags:
        for target in idx.tag_index.get(str(tag), []):
            tag_target_counts[target] += 1
            if target not in tag_target_first:
                tag_target_first[target] = str(tag)

    for target, shared_count in tag_target_counts.items():
        w = RelationWeights()
        tag_strength = compute_tag_strength(shared_count, w)
        target_card = card_map.get(target, {})
        recency = compute_recency_bonus(
            str(target_card.get("created_at")) if target_card.get("created_at") else None,
            weights=w,
        )
        strength = compute_multi_factor_strength(tag_strength, recency_bonus=recency)
        detail = (
            f"shared tags ({shared_count}): #{tag_target_first[target]}"
            if shared_count > 1
            else f"shared tag: #{tag_target_first[target]}"
        )
        edges.append(RelatedCardEdge(
            source_card_id=str(center["id"]),
            target_card_id=target,
            reason=RelationReason.SAME_TAG,
            reason_detail=detail,
            strength=strength,
        ))

    # same_wiki_section
    section_target_counts: dict[str, int] = defaultdict(int)
    section_target_first: dict[str, str] = {}
    for sec in center_sections:
        for target in idx.section_index.get(str(sec), []):
            section_target_counts[target] += 1
            if target not in section_target_first:
                section_target_first[target] = str(sec)

    for target, shared_count in section_target_counts.items():
        w = RelationWeights()
        section_strength = compute_wiki_strength(shared_count, w)
        target_card = card_map.get(target, {})
        recency = compute_recency_bonus(
            str(target_card.get("created_at")) if target_card.get("created_at") else None,
            weights=w,
        )
        strength = compute_multi_factor_strength(section_strength, recency_bonus=recency)
        detail = (
            f"same wiki sections ({shared_count}): {section_target_first[target]}"
            if shared_count > 1
            else f"same wiki section: {section_target_first[target]}"
        )
        edges.append(RelatedCardEdge(
            source_card_id=str(center["id"]),
            target_card_id=target,
            reason=RelationReason.SAME_WIKI_SECTION,
            reason_detail=detail,
            strength=strength,
        ))

    # same_review_batch
    if center_batch:
        for target in idx.batch_index.get(str(center_batch), []):
            edges.append(RelatedCardEdge(
                source_card_id=str(center["id"]),
                target_card_id=target,
                reason=RelationReason.SAME_REVIEW_BATCH,
                reason_detail=f"same review batch: {center_batch}",
                strength=_STRENGTH[RelationReason.SAME_REVIEW_BATCH],
            ))

    # source_location_neighbor
    if center_src and center_location_index is not None:
        seen_location_targets: set[str] = set()
        for nearby in (center_location_index - 1, center_location_index + 1):
            for target in idx.location_index.get((str(center_src), nearby), []):
                if target not in seen_location_targets:
                    seen_location_targets.add(target)
                    edges.append(RelatedCardEdge(
                        source_card_id=str(center["id"]),
                        target_card_id=target,
                        reason=RelationReason.SOURCE_LOCATION_NEIGHBOR,
                        reason_detail=f"nearby source location: {nearby}",
                        strength=_STRENGTH[RelationReason.SOURCE_LOCATION_NEIGHBOR],
                    ))

    return edges


# ── Utility ─────────────────────────────────────────────────────────


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except ValueError:
        return None


def _find_card(
    card_id: str,
    all_cards: list[dict[str, object]],
) -> dict[str, object] | None:
    for c in all_cards:
        if str(c["id"]) == card_id:
            return c
    return None
