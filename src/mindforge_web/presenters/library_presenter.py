"""Library card response builders — 将 library domain 模型转换为 Web API response。

中文学习型说明：此模块包含 Library 页面所需的所有 response 构造函数。
从 CardSummary / LibraryCardDetail / LibraryStats 等 core 层 domain 对象
转换为 mindforge_web.schemas 中的 Pydantic response 类型。

所有函数都是纯数据变换，无 IO，无副作用。
"""

from __future__ import annotations

from mindforge.cards import CardSummary, iter_cards
from mindforge.config import MindForgeConfig
from mindforge.library_service import LibraryCardDetail
from mindforge.relations.local_graph import build_card_centered_graph
from mindforge.relations.related_cards import RelatedCardEdge, compute_multi_hop_related_cards
from mindforge.strategy_display import strategy_display
from mindforge_web.presenters.graph_presenter import build_local_graph_response
from mindforge_web.presenters.shared import get_relation_reason_label, make_relation_record
from mindforge_web.schemas import (
    LibraryCardDetailResponse,
    LibraryCardResponse,
    LibraryStatsResponse,
    RelatedCardReasonResponse,
    RelatedCardResponse,
)
from mindforge_web.services.web_path_action_service import WebPathActionService


def build_library_stats_response(stats) -> LibraryStatsResponse:
    return LibraryStatsResponse(
        vault_root=str(stats.vault_root),
        cards_dir=stats.cards_dir,
        total_cards=stats.total_cards,
        by_status=stats.by_status,
        by_track=stats.by_track,
        by_provider=stats.by_provider,
        recent_count=stats.recent_count,
        index_path=str(stats.index_path),
        index_exists=stats.index_exists,
        next_action=stats.next_action,
    )


def build_library_card_response(card) -> LibraryCardResponse:
    summary = card.summary
    strategy = strategy_display(summary.strategy_id)
    return LibraryCardResponse(
        id=summary.id,
        title=summary.title,
        status=summary.status,
        status_explanation=card.status_explanation,
        track=summary.track,
        source_id=summary.source_id,
        source_type=summary.source_type,
        adapter_name=summary.adapter_name,
        source_title=summary.source_title,
        source_path=summary.source_path,
        source_content_hash=summary.source_content_hash,
        source_archive_path=summary.source_archive_path,
        source_missing=card.source_missing,
        profile=summary.profile,
        provider=summary.provider,
        strategy_id=summary.strategy_id,
        strategy_label=strategy.label,
        strategy_note=strategy.note,
        strategy_canonical_id=strategy.canonical_id,
        strategy_version=summary.strategy_version,
        schema_version=summary.schema_version,
        prompt_version=summary.prompt_version,
        prompt_versions=dict(summary.prompt_versions),
        stage_models=dict(summary.stage_models),
        run_id=summary.run_id,
        created_at=summary.created_at.isoformat() if summary.created_at else None,
        approved_at=summary.approved_at.isoformat() if summary.approved_at else None,
        updated_at=summary.updated_at.isoformat() if summary.updated_at else None,
        rel_path=summary.rel_path,
        fallback_provider_note=card.fallback_provider_note,
        quality_score=summary.quality_score,
        quality_level=summary.quality_level,
    )


def build_library_card_summary_response(
    summary: CardSummary,
    path_action_service: WebPathActionService | None = None,
) -> LibraryCardResponse:
    strategy = strategy_display(summary.strategy_id)
    source_path_view = None
    if path_action_service is not None:
        source_path_view = path_action_service.build_source_path_view(
            summary.source_path, source_title=summary.source_title,
            source_archive_path=summary.source_archive_path,
        )
    safe_path = path_action_service.safe_source_path(
        summary.source_path, source_path_view
    ) if path_action_service is not None else None
    return LibraryCardResponse(
        id=summary.id,
        title=summary.title,
        status=summary.status,
        status_explanation=(
            "human_approved：显式 approve 后进入正式知识库"
            if summary.status == "human_approved"
            else f"{summary.status}：非 Library 主列表状态"
        ),
        track=summary.track,
        source_id=summary.source_id,
        source_type=summary.source_type,
        adapter_name=summary.adapter_name,
        source_title=summary.source_title,
        source_path=safe_path,
        source_content_hash=summary.source_content_hash,
        source_archive_path=summary.source_archive_path,
        source_missing=summary.source_missing,
        profile=summary.profile,
        provider=summary.provider,
        strategy_id=summary.strategy_id,
        strategy_label=strategy.label,
        strategy_note=strategy.note,
        strategy_canonical_id=strategy.canonical_id,
        strategy_version=summary.strategy_version,
        schema_version=summary.schema_version,
        prompt_version=summary.prompt_version,
        prompt_versions=dict(summary.prompt_versions),
        stage_models=dict(summary.stage_models),
        run_id=summary.run_id,
        created_at=summary.created_at.isoformat() if summary.created_at else None,
        approved_at=summary.approved_at.isoformat() if summary.approved_at else None,
        updated_at=summary.updated_at.isoformat() if summary.updated_at else None,
        rel_path=summary.rel_path,
        fallback_provider_note=None,
        source_path_view=source_path_view,
        quality_score=summary.quality_score,
        quality_level=summary.quality_level,
    )


class _LibraryRelationshipContext:
    def __init__(
        self,
        *,
        graph,
        related_cards: list[RelatedCardResponse],
    ) -> None:
        self.graph = graph
        self.related_cards = related_cards


def build_related_card_responses(
    edges: list[RelatedCardEdge],
    cards_by_id: dict[str, LibraryCardResponse],
) -> list[RelatedCardResponse]:
    grouped: dict[str, list[RelatedCardReasonResponse]] = {}
    for edge in edges:
        if edge.target_card_id not in cards_by_id:
            continue
        grouped.setdefault(edge.target_card_id, []).append(
            RelatedCardReasonResponse(
                reason=edge.reason.value,
                label=get_relation_reason_label(edge.reason.value),
                detail=edge.reason_detail,
                strength=edge.strength,
                hop_distance=edge.hop_distance,
                via_path=list(edge.via_path),
            )
        )
    return [
        RelatedCardResponse(card=cards_by_id[card_id], reasons=reasons)
        for card_id, reasons in grouped.items()
    ]


def build_library_relationship_context(
    cfg: MindForgeConfig,
    detail: LibraryCardDetail,
    path_action_service: WebPathActionService | None = None,
) -> _LibraryRelationshipContext:
    """为 Library card detail 构建只读关系上下文。

    中文学习型说明：Relationship Preview 是用户入口，不是新的知识真相来源。
    它只读取 approved card 摘要字段，调用 deterministic graph / related-card
    engine，不读取 source 正文、不调用 LLM、不修改 approval 状态。
    """

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = [card for card in scan.cards if card.status == "human_approved"]
    records = [make_relation_record(card) for card in approved]
    center_id = detail.card.summary.id or detail.card.summary.rel_path
    graph = build_card_centered_graph(center_id, records)
    cards_by_id = {
        card.id or card.rel_path: build_library_card_summary_response(card, path_action_service=path_action_service)
        for card in approved
    }
    edges = compute_multi_hop_related_cards(center_id, records, context="library", max_depth=2)
    return _LibraryRelationshipContext(
        graph=graph,
        related_cards=build_related_card_responses(edges, cards_by_id),
    )


def build_library_detail_response(
    cfg: MindForgeConfig,
    detail: LibraryCardDetail,
    path_action_service: WebPathActionService | None = None,
) -> LibraryCardDetailResponse:
    related_context = build_library_relationship_context(cfg, detail, path_action_service=path_action_service)
    card = build_library_card_response(detail.card)
    if path_action_service is not None:
        card.source_path_view = path_action_service.build_source_path_view(
            card.source_path, source_title=card.source_title,
            source_archive_path=card.source_archive_path,
        )
        card.source_path = path_action_service.safe_source_path(
            card.source_path, card.source_path_view
        )
    return LibraryCardDetailResponse(
        card=card,
        body=detail.body,
        local_graph=build_local_graph_response(related_context.graph),
        related_cards=related_context.related_cards,
    )
