"""TopicPresenter —— 从 approved cards 构建安全、runtime 的 topic 视图。

核心规则：
1. 只包含 human_approved 卡片，ai_draft 被严格排除。
2. summary 从 approved card body 中安全提取，不调用 LLM、不合成新知识。
3. 所有字段来自已持久化的 frontmatter 或已审批正文，不做推断。
"""

from __future__ import annotations

from typing import Any, Iterable

from .cards import CardSummary, read_card_body, extract_section


def build_topic_view(topic: str, all_cards: Iterable[CardSummary]) -> dict[str, Any]:
    """从 approved cards 构建安全 topic 运行时视图。

    CRITICAL: 严格执行 approval boundary。仅 human_approved 卡片进入视图。
    """
    approved_cards = []
    type_counts: dict[str, int] = {}

    for card in all_cards:
        if card.status != "human_approved":
            continue
        if card.track != topic:
            continue

        approved_cards.append(_build_card_view(card))

        k_type = card.knowledge_type or "concept"
        type_counts[k_type] = type_counts.get(k_type, 0) + 1

    return {
        "topic": topic,
        "total_approved_cards": len(approved_cards),
        "type_counts": type_counts,
        "cards": approved_cards,
    }


def list_topics(all_cards: Iterable[CardSummary]) -> list[str]:
    """列出所有包含 human_approved 卡片的 topic 名称。"""
    topics: set[str] = set()
    for card in all_cards:
        if card.status == "human_approved" and card.track:
            topics.add(card.track)
    return sorted(topics)


# ---------------------------------------------------------------------------
# 内部 helper
# ---------------------------------------------------------------------------


def _build_card_view(card: CardSummary) -> dict[str, Any]:
    """从单张 CardSummary 构建安全视图 dict。"""
    return {
        "id": card.id,
        "title": card.title,
        "knowledge_type": card.knowledge_type,
        "relations": list(card.relations),
        "tags": list(card.tags),
        "summary": _extract_safe_summary(card),
        "human_note": card.human_note,
        "approval_state": card.status,
        "value_score": card.value_score,
        "source_title": card.source_title,
        "source_type": card.source_type,
        "track": card.track,
        "created_at": card.created_at.isoformat() if card.created_at else None,
        "approved_at": card.approved_at.isoformat() if card.approved_at else None,
    }


def _extract_safe_summary(card: CardSummary, max_chars: int = 300) -> str:
    """从 approved card body 中安全提取摘要。

    不调用 LLM，不合成新知识，不生成未经审批的观点。
    优先级：
    1. ``## AI Summary`` section 内容；
    2. ``## Summary`` section 内容；
    3. body 第一个非空段落。

    始终截断到 max_chars。
    """
    try:
        body = read_card_body(card.path)
    except (OSError, ValueError):
        return ""

    # 优先取显式 summary section
    for section_name in ("AI Summary", "Summary"):
        content = extract_section(body, section_name)
        if content:
            return _truncate_text(content, max_chars)

    # fallback: 第一个非空段落
    paras = _extract_paragraphs(body)
    if paras:
        return _truncate_text(paras[0], max_chars)

    return ""


def _extract_paragraphs(body: str) -> list[str]:
    """从 markdown body 提取非空段落（跳过标题行和空白行）。"""
    result: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("- [ ]") or stripped.startswith("- [x]"):
            continue
        if stripped.startswith("---"):
            continue
        result.append(stripped)
    return result


def _truncate_text(text: str, max_chars: int) -> str:
    """安全截断文本，保证不以词中间截断。"""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated + "…"
