"""M3 Related Cards computation — SDD §7, TDD §5。

确定性关系发现：基于 source_id, tags, wiki_sections, run_id,
source_location_index 的字段匹配。
不做 semantic similarity，不引入 embedding，全部 in-memory。

v1.2 升级：引入多因子加权评分（共享实体数量、时效性）。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
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
    MANUAL_LINK = "manual_link"  # reserved — v0.3 不发出此边类型


# Base strength weights (v1.2: 基础权重，实际计算由 scoring 模块完成)
_STRENGTH: dict[RelationReason, float] = {
    RelationReason.SAME_SOURCE: 0.8,
    RelationReason.SAME_TAG: 0.5,
    RelationReason.SAME_WIKI_SECTION: 0.7,
    RelationReason.SAME_REVIEW_BATCH: 0.3,
    RelationReason.SOURCE_LOCATION_NEIGHBOR: 0.4,
    RelationReason.MANUAL_LINK: 1.0,
}

# v1.2 共享实体计数缓存（避免重复计算交集）
_shared_entity_counts: dict[tuple[str, str, str], int] = {}


@dataclass(frozen=True)
class RelatedCardEdge:
    source_card_id: str
    target_card_id: str
    reason: RelationReason
    reason_detail: str = ""
    strength: float = 0.5


def compute_related_cards(
    card_id: str,
    all_cards: list[dict[str, object]],
    *,
    context: str = "library",
) -> list[RelatedCardEdge]:
    """计算单张卡片的确定性 related cards。

    Args:
        card_id: 查询卡片 ID
        all_cards: 所有卡片记录列表，每条为 dict
        context: "library" → 仅 human_approved；"review" → 包含 pending

    Returns:
        RelatedCardEdge 列表，按 strength 降序排列，每种 reason ≤ 5 条
    """
    # 找到目标卡片
    center = _find_card(card_id, all_cards)
    if center is None:
        return []

    # 预建索引
    source_index: dict[str, list[str]] = defaultdict(list)
    tag_index: dict[str, list[str]] = defaultdict(list)
    section_index: dict[str, list[str]] = defaultdict(list)
    batch_index: dict[str, list[str]] = defaultdict(list)
    location_index: dict[tuple[str, int], list[str]] = defaultdict(list)

    for c in all_cards:
        cid = str(c["id"])
        if cid == card_id:
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
        source_location_index = _int_or_none(c.get("source_location_index"))
        if sid and source_location_index is not None:
            location_index[(str(sid), source_location_index)].append(cid)

    edges: list[RelatedCardEdge] = []
    center_src = center.get("source_id")
    center_tags = set(center.get("tags") or [])
    center_sections = set(center.get("wiki_sections") or [])
    center_batch = center.get("run_id") or center.get("review_batch")
    center_location_index = _int_or_none(center.get("source_location_index"))

    # same_source (v1.2: recency bonus)
    if center_src:
        w = RelationWeights()
        for target in source_index.get(str(center_src), []):
            target_card = _find_card(target, all_cards)
            recency = compute_recency_bonus(
                str(target_card.get("created_at")) if target_card and target_card.get("created_at") else None,
                weights=w,
            )
            strength = compute_multi_factor_strength(_STRENGTH[RelationReason.SAME_SOURCE], recency_bonus=recency)
            edges.append(RelatedCardEdge(
                source_card_id=card_id,
                target_card_id=target,
                reason=RelationReason.SAME_SOURCE,
                reason_detail=f"same source: {center_src}",
                strength=strength,
            ))

    # same_tag (v1.2: 多标签加权)
    tag_target_counts: dict[str, int] = defaultdict(int)  # target → shared tag count
    tag_target_first: dict[str, str] = {}  # target → first shared tag
    for tag in center_tags:
        for target in tag_index.get(str(tag), []):
            tag_target_counts[target] += 1
            if target not in tag_target_first:
                tag_target_first[target] = str(tag)

    for target, shared_count in tag_target_counts.items():
        w = RelationWeights()
        tag_strength = compute_tag_strength(shared_count, w)
        target_card = _find_card(target, all_cards)
        recency = compute_recency_bonus(
            str(target_card.get("created_at")) if target_card and target_card.get("created_at") else None,
            weights=w,
        )
        strength = compute_multi_factor_strength(tag_strength, recency_bonus=recency)
        detail = (
            f"shared tags ({shared_count}): #{tag_target_first[target]}"
            if shared_count > 1
            else f"shared tag: #{tag_target_first[target]}"
        )
        edges.append(RelatedCardEdge(
            source_card_id=card_id,
            target_card_id=target,
            reason=RelationReason.SAME_TAG,
            reason_detail=detail,
            strength=strength,
        ))

    # same_wiki_section (v1.2: 多章节加权)
    section_target_counts: dict[str, int] = defaultdict(int)
    section_target_first: dict[str, str] = {}
    for sec in center_sections:
        for target in section_index.get(str(sec), []):
            section_target_counts[target] += 1
            if target not in section_target_first:
                section_target_first[target] = str(sec)

    for target, shared_count in section_target_counts.items():
        w = RelationWeights()
        section_strength = compute_wiki_strength(shared_count, w)
        target_card = _find_card(target, all_cards)
        recency = compute_recency_bonus(
            str(target_card.get("created_at")) if target_card and target_card.get("created_at") else None,
            weights=w,
        )
        strength = compute_multi_factor_strength(section_strength, recency_bonus=recency)
        detail = (
            f"same wiki sections ({shared_count}): {section_target_first[target]}"
            if shared_count > 1
            else f"same wiki section: {section_target_first[target]}"
        )
        edges.append(RelatedCardEdge(
            source_card_id=card_id,
            target_card_id=target,
            reason=RelationReason.SAME_WIKI_SECTION,
            reason_detail=detail,
            strength=strength,
        ))

    # same_review_batch
    if center_batch:
        for target in batch_index.get(str(center_batch), []):
            edges.append(RelatedCardEdge(
                source_card_id=card_id,
                target_card_id=target,
                reason=RelationReason.SAME_REVIEW_BATCH,
                reason_detail=f"same review batch: {center_batch}",
                strength=_STRENGTH[RelationReason.SAME_REVIEW_BATCH],
            ))

    # source_location_neighbor
    if center_src and center_location_index is not None:
        seen_location_targets: set[str] = set()
        for nearby in (center_location_index - 1, center_location_index + 1):
            for target in location_index.get((str(center_src), nearby), []):
                if target not in seen_location_targets:
                    seen_location_targets.add(target)
                    edges.append(RelatedCardEdge(
                        source_card_id=card_id,
                        target_card_id=target,
                        reason=RelationReason.SOURCE_LOCATION_NEIGHBOR,
                        reason_detail=f"nearby source location: {nearby}",
                        strength=_STRENGTH[RelationReason.SOURCE_LOCATION_NEIGHBOR],
                    ))

    # 按 strength 降序排列
    edges.sort(key=lambda e: e.strength, reverse=True)

    # 每种 reason 最多 5 条
    reason_counts: dict[RelationReason, int] = defaultdict(int)
    capped: list[RelatedCardEdge] = []
    for e in edges:
        if reason_counts[e.reason] < 5:
            capped.append(e)
            reason_counts[e.reason] += 1

    return capped


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
