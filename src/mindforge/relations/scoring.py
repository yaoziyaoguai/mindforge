"""v1.2 Relation Scoring — 加权确定性关系评分。

中文学习型说明：替代 v0.6 的固定 strength 权重，引入多因子加权公式：
- 关系类型基础权重（source > wiki_section > tag > batch > location）
- 共享实体数量加权（共享 3 个 tag 比共享 1 个 tag 更强）
- 时效性加权（近期卡片略高于旧卡片，encourage knowledge freshness）

所有计算均为 deterministic 纯函数，不涉及 embedding/ML/LLM。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationWeights:
    """关系评分权重配置。"""
    source_base: float = 0.8
    tag_base: float = 0.5
    wiki_section_base: float = 0.7
    review_batch_base: float = 0.3
    location_neighbor_base: float = 0.4
    manual_link_base: float = 1.0

    # 共享实体数量的加权因子（越多共享实体，关系越强）
    shared_entity_factor: float = 0.1

    # 时效性权重（相对于固定 base 的可变比例）
    recency_weight: float = 0.1


def compute_tag_strength(
    shared_tag_count: int,
    weights: RelationWeights | None = None,
) -> float:
    """计算基于共享标签数量的加权 strength。

    公式: tag_base + shared_entity_factor * min(shared_count - 1, 3)
    共享 1 个 tag → base, 2 个 → base + 0.1, 3 个 → base + 0.2, 4+ → base + 0.3
    """
    w = weights or RelationWeights()
    bonus = w.shared_entity_factor * min(shared_tag_count - 1, 3)
    return min(w.tag_base + bonus, 0.95)


def compute_source_strength(
    shared_source_count: int,
    weights: RelationWeights | None = None,
) -> float:
    """计算基于共享 source 的 strength。多 source 共享极少见，保持固定。"""
    w = weights or RelationWeights()
    return w.source_base


def compute_wiki_strength(
    shared_section_count: int,
    weights: RelationWeights | None = None,
) -> float:
    """计算基于共享 wiki section 数量的加权 strength。"""
    w = weights or RelationWeights()
    bonus = w.shared_entity_factor * min(shared_section_count - 1, 3)
    return min(w.wiki_section_base + bonus, 0.95)


def compute_recency_bonus(
    created_at_iso: str | None,
    *,
    now_iso: str | None = None,
    weights: RelationWeights | None = None,
) -> float:
    """计算时效性加权（0~recency_weight）。

    规则: 30 天内 → full bonus, 30~90 天 → 线性衰减, 90+ 天 → 0。
    """
    if not created_at_iso:
        return 0.0
    w = weights or RelationWeights()
    try:
        from datetime import datetime, timezone

        created = datetime.fromisoformat(created_at_iso)
        now = datetime.fromisoformat(now_iso) if now_iso else datetime.now(timezone.utc)
        # 移除时区信息做纯日期比较
        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        age_days = (now - created).days
        if age_days <= 30:
            return w.recency_weight
        if age_days <= 90:
            return w.recency_weight * (1.0 - (age_days - 30) / 60.0)
        return 0.0
    except (ValueError, TypeError):
        return 0.0


def compute_multi_factor_strength(
    base_strength: float,
    *,
    shared_entities: int = 1,
    recency_bonus: float = 0.0,
) -> float:
    """综合多因子加权。

    公式: base + shared_factor_bonus + recency_bonus, clamped to [0.05, 0.99]
    """
    raw = base_strength + recency_bonus
    return max(0.05, min(raw, 0.99))


__all__ = [
    "RelationWeights",
    "compute_tag_strength",
    "compute_source_strength",
    "compute_wiki_strength",
    "compute_recency_bonus",
    "compute_multi_factor_strength",
]
