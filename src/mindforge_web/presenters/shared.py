"""shared relation utilities — used by graph、library presenters。

中文学习型说明：此模块提供 graph presenter 和 library presenter 共用的窄工具函数。
放在独立的 shared 模块中以避免 graph ↔ library 间的循环导入。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.cards import CardSummary


def make_relation_record(card: CardSummary) -> dict[str, object]:
    """把 CardSummary 转成 relations engine 的窄输入结构。"""

    card_id = card.id or card.rel_path
    return {
        "id": card_id,
        "title": card.title or Path(card.rel_path).stem,
        "status": card.status,
        "source_id": card.source_id,
        "tags": list(card.tags),
        "wiki_sections": list(card.wiki_sections),
        "run_id": card.run_id,
        "source_location_index": card.source_location_index,
    }


def get_relation_reason_label(reason: str) -> str:
    labels = {
        "same_source": "Same source",
        "same_tag": "Same tag",
        "same_wiki_section": "Same wiki section",
        "same_review_batch": "Same review batch",
        "source_location_neighbor": "Source location neighbor",
        "manual_link": "Manual link",
    }
    return labels.get(reason, reason.replace("_", " ").title())
