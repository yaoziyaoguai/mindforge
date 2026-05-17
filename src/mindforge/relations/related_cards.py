"""M3 Related Cards computation — SDD §7, TDD §5。

确定性关系发现：基于 source_id, tags, wiki_sections, run_id,
source_location_index 的字段匹配。
不做 semantic similarity，不引入 embedding，全部 in-memory。
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from collections import defaultdict


class RelationReason(str, enum.Enum):
    SAME_SOURCE = "same_source"
    SAME_TAG = "same_tag"
    SAME_WIKI_SECTION = "same_wiki_section"
    SAME_REVIEW_BATCH = "same_review_batch"
    SOURCE_LOCATION_NEIGHBOR = "source_location_neighbor"
    MANUAL_LINK = "manual_link"  # reserved — v0.3 不发出此边类型


# Strength weights per SDD §7.1
_STRENGTH: dict[RelationReason, float] = {
    RelationReason.SAME_SOURCE: 0.8,
    RelationReason.SAME_TAG: 0.5,
    RelationReason.SAME_WIKI_SECTION: 0.7,
    RelationReason.SAME_REVIEW_BATCH: 0.3,
    RelationReason.SOURCE_LOCATION_NEIGHBOR: 0.4,
    RelationReason.MANUAL_LINK: 1.0,
}


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

    # same_source
    if center_src:
        for target in source_index.get(str(center_src), []):
            edges.append(RelatedCardEdge(
                source_card_id=card_id,
                target_card_id=target,
                reason=RelationReason.SAME_SOURCE,
                reason_detail=f"same source: {center_src}",
                strength=_STRENGTH[RelationReason.SAME_SOURCE],
            ))

    # same_tag
    seen_tag_targets: set[str] = set()
    for tag in center_tags:
        for target in tag_index.get(str(tag), []):
            if target not in seen_tag_targets:
                seen_tag_targets.add(target)
                edges.append(RelatedCardEdge(
                    source_card_id=card_id,
                    target_card_id=target,
                    reason=RelationReason.SAME_TAG,
                    reason_detail=f"shared tag: {tag}",
                    strength=_STRENGTH[RelationReason.SAME_TAG],
                ))

    # same_wiki_section
    seen_section_targets: set[str] = set()
    for sec in center_sections:
        for target in section_index.get(str(sec), []):
            if target not in seen_section_targets:
                seen_section_targets.add(target)
                edges.append(RelatedCardEdge(
                    source_card_id=card_id,
                    target_card_id=target,
                    reason=RelationReason.SAME_WIKI_SECTION,
                    reason_detail=f"same wiki section: {sec}",
                    strength=_STRENGTH[RelationReason.SAME_WIKI_SECTION],
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
