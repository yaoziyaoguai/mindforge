"""M1 卡片类型分类 — SDD §5.4, RFC §7 FR1.4。

基于关键词的规则分类，返回 CardType enum。
不依赖 LLM / AI 推断（Open Question §4: 先规则再可选 AI enhancement）。
"""

from __future__ import annotations

from mindforge.quality.models import CardType

# 每种类型的匹配关键词 — SDD §5.4 定义
_TYPE_KEYWORDS: dict[CardType, tuple[str, ...]] = {
    CardType.FACT: (
        "is defined as", "was found", "measured", "observed", "recorded",
    ),
    CardType.CLAIM: (
        "argues that", "claims that", "asserts", "contends", "purports",
    ),
    CardType.DECISION: (
        "decided to", "chose to", "agreed on", "resolved", "committed to",
    ),
    CardType.METHOD: (
        "how to", "steps to", "procedure", "method", "approach", "technique",
    ),
    CardType.RISK: (
        "risk of", "pitfall", "failure mode", "edge case", "watch out", "caution",
    ),
    CardType.QUESTION: (
        "how can", "why does", "what is", "when should", "open question",
    ),
    CardType.INSIGHT: (
        "interesting", "surprising", "key insight", "lesson", "pattern emerges",
    ),
}


def classify_card_type(title: str, body: str) -> CardType | None:
    """基于关键词的卡片类型规则分类。

    Args:
        title: 卡片标题
        body: 卡片正文（仅使用前 500 字符以提高性能）

    Returns:
        匹配的 CardType，若无关键词命中返回 None。
        多类型命中时返回关键词匹配数最多的类型（平局时按 enum 顺序居先）。
    """
    # 仅检查标题 + body 前 500 字符（与 SDD §5.4 一致）
    text = f"{title} {body[:500]}".lower()

    scores: dict[CardType, int] = {}
    for ct, keywords in _TYPE_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[ct] = score

    if not scores:
        return None

    # 选最高分；平局按 CardType enum 顺序
    best = max(scores, key=lambda ct: (scores[ct], -list(CardType).index(ct)))
    return best
