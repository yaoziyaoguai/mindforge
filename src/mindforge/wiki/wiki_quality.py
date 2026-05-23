"""M2 Wiki Quality Report — SDD §6, TDD §4。

Deterministic wiki quality computation: coverage, faithfulness, staleness,
conflicting claims detection. 不调用 LLM，不引入 embedding。
"""

from __future__ import annotations

import re
from dataclasses import dataclass


# ──────────────────────────────────────────────
# Data Models (frozen)
# ──────────────────────────────────────────────

@dataclass(frozen=True)
class SectionReference:
    section_title: str
    card_ids: tuple[str, ...]
    relevance: str  # primary, supporting, mentioned


@dataclass(frozen=True)
class WikiQualityReport:
    wiki_version: str
    rebuild_time: str
    total_approved_cards: int
    used_card_ids: tuple[str, ...]
    unused_card_ids: tuple[str, ...]
    unused_reasons: dict[str, str]
    section_references: tuple[SectionReference, ...]
    stale_sections: tuple[str, ...]
    faithfulness_scores: dict[str, float]
    faithfulness_issues: tuple[str, ...]
    knowledge_gaps: tuple[str, ...]
    conflicting_claims: tuple[tuple[str, str, str], ...]  # (card_a, card_b, topic)
    dedup_suggestions: tuple[tuple[str, str], ...]


# ──────────────────────────────────────────────
# Coverage Computation
# ──────────────────────────────────────────────

def compute_coverage(
    approved_ids: list[str],
    used_ids: list[str],
    reason_map: dict[str, str],
) -> tuple[list[str], dict[str, str]]:
    """计算哪些 approved cards 未被 Wiki 使用。

    Returns:
        (unused_ids, reasons) — reasons 仅包含 unused_ids 的条目
    """
    used_set = set(used_ids)
    unused = [cid for cid in approved_ids if cid not in used_set]
    reasons = {cid: reason_map.get(cid, "Not referenced in any Wiki section") for cid in unused}
    return unused, reasons


# ──────────────────────────────────────────────
# Faithfulness Computation (Deterministic)
# ──────────────────────────────────────────────

# English stopwords — small built-in list, no external dependency
_EN_STOPWORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "shall", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "as", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "both", "each", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "and", "but", "or", "if", "while", "that", "this",
    "it", "its", "they", "them", "their", "he", "she", "we", "you",
    "about", "up", "out", "just", "now", "also",
}

_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9一-鿿\s]")


def compute_faithfulness_score(
    section_text: str,
    card_bodies: dict[str, str],
) -> float:
    """确定性 faithfulness 评分 via Jaccard similarity of key terms。

    1. 提取 section 和所有 card bodies 的 key terms
    2. 计算 section_terms ∩ union(card_terms) / section_terms ∪ union(card_terms)
    3. 返回 Jaccard coefficient (0.0-1.0)

    Returns 0.0 if section_text is empty or card_bodies is empty.
    """
    if not section_text.strip() or not card_bodies:
        return 0.0

    section_terms = _extract_key_terms(section_text)
    if not section_terms:
        return 0.0

    all_card_terms: set[str] = set()
    for body in card_bodies.values():
        all_card_terms.update(_extract_key_terms(body))

    if not all_card_terms:
        return 0.0

    intersection = section_terms & all_card_terms
    union = section_terms | all_card_terms
    return len(intersection) / len(union)


def _extract_key_terms(text: str) -> set[str]:
    """从文本中提取 key terms：lowercase → 去标点 → 分词 → 去停用词。"""
    text = text.lower()
    text = _NON_ALNUM_RE.sub(" ", text)
    tokens = _WHITESPACE_RE.split(text)
    return {t for t in tokens if t and len(t) > 1 and t not in _EN_STOPWORDS}


# ──────────────────────────────────────────────
# Staleness Detection
# ──────────────────────────────────────────────

def detect_stale_sections(
    section_refs: list[SectionReference],
    *,
    new_card_titles: set[str] | None = None,
    topic_keywords: dict[str, set[str]] | None = None,
) -> list[str]:
    """检测哪些 Wiki section 可能过期。

    如果新的 approved card 标题包含 section 主题关键词 →
    该 section 标记为 stale。

    Args:
        section_refs: Wiki section 引用列表
        new_card_titles: 所有已批准卡片的标题集
        topic_keywords: section → 关键词集合映射
    """
    if not new_card_titles or not topic_keywords:
        return []

    stale: list[str] = []
    for ref in section_refs:
        keywords = topic_keywords.get(ref.section_title, set())
        if not keywords:
            continue
        for title in new_card_titles:
            title_lower = title.lower()
            if any(kw in title_lower for kw in keywords):
                stale.append(ref.section_title)
                break
    return stale


# ──────────────────────────────────────────────
# Knowledge Gap Detection (keyword-based)
# ──────────────────────────────────────────────


def compute_knowledge_gaps(
    section_titles: list[str],
    used_tags: set[str],
    topic_keywords: dict[str, set[str]],
) -> list[str]:
    """检测 Wiki 未覆盖的知识主题。

    检查 topic_keywords 中定义的每个主题关键词是否至少出现在
    一个 section title 或 used tags 中。未出现的主题即 knowledge gap。

    Args:
        section_titles: Wiki 中各 section 标题
        used_tags: Wiki 中引用的卡片 tag 集合
        topic_keywords: 主题 → 关键词集合映射
    """
    gaps: list[str] = []
    for topic, keywords in topic_keywords.items():
        found = False
        for title in section_titles:
            title_lower = title.lower()
            if any(kw in title_lower for kw in keywords):
                found = True
                break
        if not found:
            for tag in used_tags:
                tag_lower = tag.lower()
                if any(kw in tag_lower for kw in keywords):
                    found = True
                    break
        if not found:
            gaps.append(topic)
    return gaps


# ──────────────────────────────────────────────
# Conflicting Claims Detection (Rule-based)
# ──────────────────────────────────────────────

_POSITIVE_VERBS = {"increases", "improves", "enhances", "boosts", "raises", "causes"}
_NEGATIVE_VERBS = {"decreases", "worsens", "reduces", "prevents", "lowers", "hinders"}


def detect_conflicting_claims(
    card_a: tuple[str, str, set[str]],  # (id, title, tags)
    card_b: tuple[str, str, set[str]],
) -> list[tuple[str, str, str]]:
    """检测两张卡片是否有矛盾声明。

    条件：
    1. 两者共享 ≥1 tag
    2. 一个 title 包含正向动词，另一个包含负向动词
    """
    _a_id, a_title, a_tags = card_a
    _b_id, b_title, b_tags = card_b

    shared_tags = a_tags & b_tags
    if not shared_tags:
        return []

    a_lower = a_title.lower()
    b_lower = b_title.lower()

    a_has_pos = any(v in a_lower for v in _POSITIVE_VERBS)
    a_has_neg = any(v in a_lower for v in _NEGATIVE_VERBS)
    b_has_pos = any(v in b_lower for v in _POSITIVE_VERBS)
    b_has_neg = any(v in b_lower for v in _NEGATIVE_VERBS)

    if (a_has_pos and b_has_neg) or (a_has_neg and b_has_pos):
        topic = sorted(shared_tags)[0]
        return [(card_a[0], card_b[0], topic)]

    return []
