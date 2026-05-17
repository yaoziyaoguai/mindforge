"""M1 Card Quality Web Service — SDD §4.1。

为 Web API 层提供 quality metadata 计算。调用 quality 模块的确定性评分，
不调用 LLM / API / Embedding。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.cards import CardSummary, read_card_body
from mindforge.quality import (
    classify_card_type,
    detect_warnings,
    generate_suggestions,
    score_quality,
)
from mindforge.quality.models import CardQuality


def compute_card_quality(
    card: CardSummary,
    vault_root: Path,
    all_titles: list[str] | None = None,
) -> CardQuality:
    """计算单张卡片的 quality metadata。

    Args:
        card: 卡片摘要（必须已有 title, source_id 等 frontmatter 信息）
        vault_root: vault 根路径（用于读取 body）
        all_titles: 所有卡片 title 列表（用于 duplicate detection）

    Returns:
        CardQuality 元数据。不会修改卡片文件内容或 frontmatter status。
    """
    # 读取卡片 body
    body = ""
    try:
        body = read_card_body(card.path)
    except (OSError, ValueError):
        pass

    # 1. 检测 warnings
    warnings = detect_warnings(
        title=card.title or "",
        body=body,
        source_id=card.source_id,
        source_path=card.source_path,
        all_titles=[t for t in (all_titles or []) if t != card.title],
    )

    # 2. 评分
    quality = score_quality(
        title=card.title or "",
        body=body,
        source_id=card.source_id,
        source_path=card.source_path,
        source_type=card.source_type,
        warnings=warnings,
    )

    # 3. 分类
    ct = classify_card_type(title=card.title or "", body=body)
    quality = CardQuality(
        overall_level=quality.overall_level,
        overall_score=quality.overall_score,
        rubric_scores=quality.rubric_scores,
        warnings=quality.warnings,
        card_type=ct,
        regenerate_suggestion=quality.regenerate_suggestion,
        split_candidate=quality.split_candidate,
        merge_candidate=quality.merge_candidate,
        dedup_candidates=quality.dedup_candidates,
    )

    # 4. 生成建议
    return generate_suggestions(quality)
