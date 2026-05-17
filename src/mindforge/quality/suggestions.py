"""M1 卡片维护建议 — SDD §5.3, RFC §7 FR1.5。

为低质量卡片生成 regenerate / split / merge / dedup 建议。
建议仅作信号参考，不自动执行（RFC §6 AD-2）。
"""

from __future__ import annotations

from mindforge.quality.models import CardQuality


def generate_suggestions(quality: CardQuality) -> CardQuality:
    """根据质量评分生成维护建议。

    修改 quality 的 regenerate_suggestion / split_candidate / merge_candidate 字段。
    由于 CardQuality 是 frozen dataclass，返回一个新的 CardQuality 实例。

    不修改原实例的任何字段。
    """
    regenerate = _regenerate_reason(quality)
    split = _should_split(quality)
    merge = _should_merge(quality)

    return CardQuality(
        overall_level=quality.overall_level,
        overall_score=quality.overall_score,
        rubric_scores=quality.rubric_scores,
        warnings=quality.warnings,
        card_type=quality.card_type,
        regenerate_suggestion=regenerate,
        split_candidate=split,
        merge_candidate=merge,
        dedup_candidates=quality.dedup_candidates,
    )


def _regenerate_reason(quality: CardQuality) -> str | None:
    """判断是否应建议重新生成。"""
    reasons: list[str] = []

    if quality.overall_score < 40:
        reasons.append("整体质量评分过低")
    if any(w.code == "too_short" for w in quality.warnings):
        reasons.append("内容过短")
    if any(w.code == "vague_language" for w in quality.warnings):
        reasons.append("模糊表述过多")
    if any(w.code == "missing_sections" for w in quality.warnings):
        reasons.append("缺少结构化章节")

    if not reasons:
        return None
    return "建议重新生成该卡片（regenerate）。原因：" + "；".join(reasons)


def _should_split(quality: CardQuality) -> bool:
    """检测是否包含多个独立主题 → 建议拆分。"""
    # 仅当 structure 维度接近满分（≥ 0.95，即 4+ h2 + 有 h3）且整体质量高时才建议拆分
    return quality.overall_score >= 60 and _count_h2_sections(quality) >= 4


def _should_merge(quality: CardQuality) -> bool:
    """检测是否为碎片化小卡片 → 建议合并。"""
    return quality.overall_score < 50 and any(
        w.code == "too_short" for w in quality.warnings
    )


def _count_h2_sections(quality: CardQuality) -> int:
    """从 rubric_scores 推断 ## 标题数量（间接方式）。

    不直接访问 body — quality 模块可能不持有原始 body。
    structure score = 1.0 → 4+ h2 with h3; = 0.8 → 2-3 h2 with h3.
    """
    for rs in quality.rubric_scores:
        if rs.dimension == "structure":
            if rs.score >= 1.0:
                return 4
            if rs.score >= 0.8:
                return 3
            return 2
    return 2
