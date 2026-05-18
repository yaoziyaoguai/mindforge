"""M1 质量警告检测 — SDD §5.3, RFC §7 FR1.3。

检测 5 种 warning：
  too_short, missing_sections, no_source_citation, vague_language, possible_duplicate

所有检测基于确定性规则，不依赖 LLM / API。
"""

from __future__ import annotations

from mindforge.quality.models import QualityWarning


def detect_warnings(
    *,
    title: str,
    body: str,
    source_id: str | None = None,
    source_path: str | None = None,
    all_titles: list[str] | None = None,
) -> tuple[QualityWarning, ...]:
    """检测单张卡片的所有质量警告。

    Returns:
        QualityWarning 的 tuple，可能为空（无警告）。
    """
    warnings: list[QualityWarning] = []

    # 1. too_short — body < 100 chars
    if len(body) < 100:
        warnings.append(QualityWarning(
            code="too_short",
            severity="warn",
            message="卡片正文过短（< 100 字符），可能缺乏足够信息量。",
            suggestion="建议扩展卡片内容，至少包含一段完整的 ## Summary 和一段 ## Details。",
        ))

    # 2. missing_sections — body 中无 ##  标记
    if "## " not in body:
        warnings.append(QualityWarning(
            code="missing_sections",
            severity="warn",
            message="卡片缺少 Markdown 章节结构（无 ##  标题）。",
            suggestion="建议添加 ## Summary 和 ## Details 章节以提升结构化程度。",
        ))

    # 3. no_source_citation — 无 source_id 且无 source_path
    if not source_id and not source_path:
        warnings.append(QualityWarning(
            code="no_source_citation",
            severity="info",
            message="卡片未引用来源（无 source_id 或 source_path）。",
            suggestion="如果该卡片内容来自某个 source，建议在 frontmatter 中标注来源。",
        ))

    # 4. vague_language — 模糊词比例高
    if _vague_ratio(body) > 0.15:
        warnings.append(QualityWarning(
            code="vague_language",
            severity="warn",
            message="卡片中模糊表述比例较高，可能缺乏具体性。",
            suggestion="建议使用具体数据、确切名称和可验证的表述替代模糊词汇。",
        ))

    # 5. possible_duplicate — title 与其他卡片 title 相似度 > 80%
    if all_titles:
        for other_title in all_titles:
            sim = _title_similarity(title, other_title)
            if sim >= 0.8:
                warnings.append(QualityWarning(
                    code="possible_duplicate",
                    severity="info",
                    message=f"卡片标题与已有卡片高度相似（相似度 {sim:.0%}）：{other_title[:60]}",
                    suggestion="建议检查两张卡片是否重复，考虑合并或删除其中之一。",
                ))
                break  # 只报告第一个相似项

    return tuple(warnings)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

_VAGUE_TERMS: frozenset[str] = frozenset({
    "something", "maybe", "probably", "might be", "could be", "possibly",
    "perhaps", "somehow", "somewhat", "kind of", "sort of", "seems like",
    "i think", "not sure", "don't know", "dont know", "whatever",
})


def _vague_ratio(body: str) -> float:
    """计算 body 中模糊词的出现比例。"""
    lower = body.lower()
    total_words = len(lower.split())
    if total_words == 0:
        return 0.0
    vague_count = sum(1 for t in _VAGUE_TERMS if t in lower)
    return vague_count / max(total_words, 1)


def _title_similarity(title1: str, title2: str) -> float:
    """计算两个 title 的 case-insensitive token overlap（Jaccard-like）。

    用于 possible_duplicate 检测。仅比较两个 title 之间的 token 重叠度。
    """
    if not title1 or not title2:
        return 0.0
    t1 = set(title1.lower().split())
    t2 = set(title2.lower().split())
    if not t1 or not t2:
        return 0.0
    intersection = t1 & t2
    union = t1 | t2
    return len(intersection) / len(union)
