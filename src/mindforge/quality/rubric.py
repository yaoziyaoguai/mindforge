"""M1 确定性质量评分规则 — SDD §5.1-5.2, RFC §7 FR1.1-1.2。

5 维度加权评分：
  completeness (25%) + structure (20%) + specificity (25%) + source_citation (20%) + consistency (10%)

所有评分基于确定性规则，不依赖 LLM / Embedding / API（RFC §6 AD-1）。
"""

from __future__ import annotations

from mindforge.quality.models import (
    CardQuality,
    QualityLevel,
    QualityRubricScore,
    QualityWarning,
)


def score_quality(
    *,
    title: str,
    body: str,
    source_id: str | None = None,
    source_path: str | None = None,
    source_type: str | None = None,
    warnings: tuple[QualityWarning, ...] = (),
    card_type: str | None = None,
) -> CardQuality:
    """对单张卡片执行 5 维度质量评分，返回 CardQuality 元数据。

    确定性保证：同一输入始终产生相同 score。不调任何外部服务。
    """
    from mindforge.quality.models import CardType

    # 5 维度评分
    completeness = _score_completeness(body)
    structure = _score_structure(body)
    specificity = _score_specificity(body)
    source_citation = _score_source_citation(source_id, source_path)
    consistency = _score_consistency(title, body)

    rubric_scores = (
        QualityRubricScore(dimension="completeness", score=completeness,
                           notes=_completeness_note(completeness)),
        QualityRubricScore(dimension="structure", score=structure,
                           notes=_structure_note(structure)),
        QualityRubricScore(dimension="specificity", score=specificity,
                           notes=_specificity_note(specificity)),
        QualityRubricScore(dimension="source_citation", score=source_citation,
                           notes=_citation_note(source_citation)),
        QualityRubricScore(dimension="consistency", score=consistency,
                           notes=_consistency_note(consistency)),
    )

    # 加权总分：completeness 25%, structure 20%, specificity 25%, source_citation 20%, consistency 10%
    weights = {
        "completeness": 0.25,
        "structure": 0.20,
        "specificity": 0.25,
        "source_citation": 0.20,
        "consistency": 0.10,
    }
    overall_score = sum(rs.score * weights[rs.dimension] for rs in rubric_scores) * 100

    # 矛盾惩罚：检测到内容自相矛盾时，整体可信度打折
    # consistency 为 0 表示内容内部矛盾 → overall × 0.5
    if consistency == 0.0:
        overall_score *= 0.5

    # 等级映射
    if overall_score >= 70:
        level = QualityLevel.HIGH
    elif overall_score >= 40:
        level = QualityLevel.MEDIUM
    else:
        level = QualityLevel.LOW

    # card_type 解析
    ct = None
    if card_type and card_type in CardType.__members__:
        ct = CardType[card_type.upper()]
    elif card_type:
        try:
            ct = CardType(card_type)
        except ValueError:
            ct = None

    return CardQuality(
        overall_level=level,
        overall_score=round(overall_score, 1),
        rubric_scores=rubric_scores,
        warnings=warnings,
        card_type=ct,
    )


# ---------------------------------------------------------------------------
# 维度 1: completeness（完整性）— 权重 25%
# ---------------------------------------------------------------------------

def _score_completeness(body: str) -> float:
    """检查是否包含 ## Summary 和 ## Details 两个必要章节。

    两者都有 → 1.0; 只有一个 → 0.5; 都没有 → 0.0。
    额外引入长度因子：body < 150 chars → 整体 completeness × 0.5（过短即使有结构也不完整）。
    """
    has_summary = _has_section(body, "Summary")
    has_details = _has_section(body, "Details")
    if has_summary and has_details:
        base = 1.0
    elif has_summary or has_details:
        base = 0.5
    else:
        base = 0.0

    # 长度因子：body < 150 chars → 过短卡片即使有结构也扣分
    if len(body) < 150 and base > 0:
        base *= 0.5
    return base


# ---------------------------------------------------------------------------
# 维度 2: structure（结构化程度）— 权重 20%
# ---------------------------------------------------------------------------

def _score_structure(body: str) -> float:
    """评估正文结构化程度。

    检查：二级标题（## ）数量、三级标题（### ）数量。
    无标题 → 0.0; 1个h2 → 0.3; 2个h2无子标题 → 0.5; 2+h2有h3 → 0.8; 4+h2有h3 → 1.0。
    """
    h2_count = body.count("\n## ")
    if body.startswith("## "):
        h2_count += 1
    h3_count = body.count("\n### ")

    if h2_count == 0:
        return 0.0
    if h2_count == 1:
        return 0.3
    if h3_count >= 2:
        return 0.8 if h2_count <= 3 else 1.0
    if h2_count <= 3:
        return 0.5
    return 0.8


# ---------------------------------------------------------------------------
# 维度 3: specificity（具体性）— 权重 25%
# ---------------------------------------------------------------------------

# 模糊词列表 — 出现越多 specificity 越低
_VAGUE_TERMS = frozenset({
    "something", "maybe", "probably", "might be", "could be", "possibly",
    "perhaps", "somehow", "somewhat", "kind of", "sort of", "seems like",
    "i think", "not sure", "don't know", "dont know", "whatever",
    "various", "several", "many", "lot of", "lots of",
})

# 具体词列表 — 出现越多 specificity 越高
_SPECIFIC_TERMS = frozenset({
    "measured", "observed", "recorded", "documented", "verified",
    "tested", "validated", "analyzed", "calculated", "computed",
    "defined as", "specifically", "precisely", "exactly",
    "percent", "percentage", "ratio", "frequency", "correlation",
    "step 1", "step 2", "step 3", "phase 1", "phase 2",
})


def _score_specificity(body: str) -> float:
    """根据模糊词 vs 具体词的比例计算 specificity。

    vague_ratio = vague_count / (vague_count + specific_count + 1)
    score = 1.0 - vague_ratio，clamp 到 [0, 1]。
    """
    lower = body.lower()
    vague_count = sum(1 for t in _VAGUE_TERMS if t in lower)
    specific_count = sum(1 for t in _SPECIFIC_TERMS if t in lower)
    total = vague_count + specific_count + 1  # +1 避免除零
    vague_ratio = vague_count / total
    return max(0.0, min(1.0, 1.0 - vague_ratio * 2))


# ---------------------------------------------------------------------------
# 维度 4: source_citation（来源引用）— 权重 20%
# ---------------------------------------------------------------------------

def _score_source_citation(source_id: str | None, source_path: str | None) -> float:
    """检查是否有 source 引用。

    有 source_id + source_path → 1.0; 仅有其一 → 0.5; 都没有 → 0.0。
    """
    if source_id and source_path:
        return 1.0
    if source_id or source_path:
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# 维度 5: consistency（一致性）— 权重 10%
# ---------------------------------------------------------------------------

# 矛盾模式对 — 出现于同一文本则标记 inconsistency
_CONTRADICTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("is the best", "completely unsuitable"),
    ("always", "never"),
    ("must always", "should not"),
    ("every", "no"),
    ("all", "none"),
    ("is superior", "is inferior"),
    ("should be used everywhere", "should never be used"),
    ("guaranteed", "unreliable"),
    ("perfect", "flawed"),
)


def _score_consistency(title: str, body: str) -> float:
    """检测自相矛盾的模式对。

    每发现一个矛盾对扣 1.0，最低 0.0。一旦有矛盾，该维度直接归零（矛盾内容不可信）。
    """
    text = f"{title} {body}".lower()
    for a, b in _CONTRADICTION_PATTERNS:
        if a in text and b in text:
            return 0.0  # 有矛盾 → 该维度 0 分
    return 1.0


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _has_section(body: str, section_title: str) -> bool:
    """检查 body 中是否存在指定二级标题。"""
    target = f"## {section_title}"
    return target.lower() in body.lower()


def _completeness_note(score: float) -> str:
    if score >= 1.0:
        return "包含 ## Summary 和 ## Details"
    if score >= 0.5:
        return "缺少一个必要章节"
    return "缺少所有必要章节"


def _structure_note(score: float) -> str:
    if score >= 0.8:
        return "结构良好，有多层标题"
    if score >= 0.5:
        return "有一定结构"
    if score >= 0.3:
        return "结构较简单"
    return "无结构化章节"


def _specificity_note(score: float) -> str:
    if score >= 0.7:
        return "内容具体"
    if score >= 0.4:
        return "有部分模糊表述"
    return "模糊表述较多"


def _citation_note(score: float) -> str:
    if score >= 1.0:
        return "有完整来源引用"
    if score >= 0.5:
        return "部分来源引用"
    return "无来源引用"


def _consistency_note(score: float) -> str:
    if score >= 1.0:
        return "未检测到矛盾"
    return "检测到内容矛盾"
