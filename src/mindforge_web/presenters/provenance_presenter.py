"""Provenance trail response builder — 构建卡片来源追溯 API response。

中文学习型说明：此模块将 LibraryCardDetail 转换为 ProvenanceTrailResponse，
包含 source 信息、sibling cards（同源卡片）、wiki sections 和 related sources。

所有函数都是纯数据变换，无 IO，无副作用。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.library_service import LibraryCardDetail
from mindforge_web.presenters.discovery_presenter import compute_related_sources
from mindforge_web.schemas import (
    ProvenanceTrailResponse,
    ProvenanceTrailSection,
    ProvenanceTrailSiblingCard,
    ProvenanceTrailSource,
)


def build_provenance_trail_response(
    cfg: MindForgeConfig,
    detail: LibraryCardDetail,
) -> ProvenanceTrailResponse:
    """U3: 构建 provenance trail — source → siblings → wiki sections。"""
    card = detail.card
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = [c for c in scan.cards if c.status == "human_approved"]

    summary = card.summary
    card_id = summary.id or summary.rel_path
    source_id = summary.source_id
    source_title = summary.source_title

    # Sibling cards: same source, excluding self, ≤ 5
    siblings: list[ProvenanceTrailSiblingCard] = []
    if source_id:
        for c in approved:
            if c.source_id != source_id:
                continue
            cid = c.id or c.rel_path
            if cid == card_id:
                continue
            siblings.append(ProvenanceTrailSiblingCard(
                card_id=cid,
                title=c.title or Path(c.rel_path).stem,
                quality_level=c.quality_level,
                quality_score=c.quality_score,
            ))
            if len(siblings) >= 5:
                break

    # Wiki sections from siblings and self
    seen_sections: dict[str, int] = {}
    for c in approved:
        csid = c.source_id
        if csid != source_id:
            continue
        for sec in c.wiki_sections:
            seen_sections[sec] = seen_sections.get(sec, 0) + 1

    # Top 5 sections by card count
    sorted_sections = sorted(seen_sections.items(), key=lambda x: x[1], reverse=True)[:5]
    wiki_sections = [
        ProvenanceTrailSection(title=title, card_count=count)
        for title, count in sorted_sections
    ]

    # Related sources: other sources sharing tags/wiki_sections with this source
    related_sources = compute_related_sources(source_id, approved)

    return ProvenanceTrailResponse(
        card_id=card_id,
        source=ProvenanceTrailSource(
            source_id=source_id,
            source_title=source_title,
        ),
        sibling_cards=siblings,
        wiki_sections=wiki_sections,
        related_sources=related_sources,
    )
