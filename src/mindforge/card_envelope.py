"""Normalize strategy envelopes before card rendering.

中文学习型说明：不同 ``KnowledgeStrategy`` 可以拥有各自的
``structured_payload`` schema，但落盘前必须收敛到 CardWriter 已知的
``structured_payload.card`` 合约。这个 adapter 是 strategy 与 writer 的
信息隐藏边界：writer 不按 strategy_id 分支，也不认识每个策略的内部字段。
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any


def normalize_card_payload_for_writer(card_payload: dict[str, Any]) -> dict[str, Any]:
    """确保公共 envelope 内存在 ``structured_payload.card``。

    five_stage 已直接产出 card；deterministic/preview strategy 只产出安全
    envelope。这里从 ``review_hints`` 与常见 structured 字段派生一张最小
    ai_draft card，让所有 strategy 复用同一 CardWriter/template。
    """

    payload = deepcopy(card_payload)
    structured = payload.setdefault("structured_payload", {})
    if not isinstance(structured, dict):
        structured = {"raw": structured}
        payload["structured_payload"] = structured
    existing = structured.get("card")
    if isinstance(existing, dict):
        return payload

    hints = payload.get("review_hints") if isinstance(payload.get("review_hints"), dict) else {}
    title = _first_non_empty(
        structured.get("title"),
        hints.get("title") if isinstance(hints, dict) else None,
        "Untitled Knowledge Card",
    )
    summary = _first_non_empty(
        structured.get("one_sentence_summary"),
        hints.get("one_line") if isinstance(hints, dict) else None,
        "No summary generated.",
    )
    concepts = _string_list(structured.get("concepts"))
    takeaways = _string_list(structured.get("key_takeaways"))
    tags = _string_list(structured.get("tags")) or concepts[:5]
    bullets = takeaways or [summary]
    if concepts and not takeaways:
        bullets.append("Concepts: " + ", ".join(concepts))

    structured["card"] = {
        "id": _slugify(title),
        "title": title,
        "track": "unrouted",
        "projects": [],
        "tags": tags,
        "value_score": 5,
        "confidence": str(structured.get("confidence") or "low"),
        "source_excerpt": "",
        "ai_summary_bullets": bullets,
        "ai_inference_bullets": [],
        "reusable_prompts_or_principles": concepts,
        "project_hooks": [],
        "review_questions": _review_questions(structured.get("questions_for_review")),
        "action_items": [],
        "suggested_links": [],
    }
    return payload


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _review_questions(value: Any) -> list[dict[str, Any]]:
    questions = _string_list(value)
    return [
        {
            "angle": "review",
            "question": question,
            "expected_points": [],
        }
        for question in questions
    ]


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", title.strip().lower()).strip("-")
    return slug[:72] or "knowledge-card"


__all__ = ["normalize_card_payload_for_writer"]
