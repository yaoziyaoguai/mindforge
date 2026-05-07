"""Web review/draft service.

中文学习型说明：draft list 使用 `approval_service` 的安全候选列表；detail
才读取单张 draft 正文给用户 review。approve 必须带二次确认 payload，并且
最终仍调用现有 `approve_explicit_card`，Web 不重写状态转移规则。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mindforge.approval_service import (
    ApprovalListQuery,
    approve_explicit_card,
    list_approval_candidates,
    preview_approval_card,
)
from mindforge.card_workspace_service import CardWorkspaceError, update_card_body
from mindforge.cards import CardSummary, read_card_body
from mindforge.config import MindForgeConfig
from mindforge.lexical_index import rebuild_index_for_config
from mindforge.strategy_display import strategy_display

from mindforge_web.schemas import (
    ApprovalResponse,
    CardBodyUpdateResponse,
    DraftDetailResponse,
    DraftSummary,
    NextAction,
    StatusItem,
    UnavailableResponse,
)


class WebReviewService:
    def __init__(self, cfg: MindForgeConfig) -> None:
        self.cfg = cfg

    def list_drafts(self) -> tuple[list[DraftSummary], list[StatusItem]]:
        result = list_approval_candidates(
            self.cfg,
            ApprovalListQuery(statuses=("ai_draft",), limit=200),
        )
        errors = [
            StatusItem(
                key=err.rel_path,
                label=err.rel_path,
                status="warn",
                value="unreadable card",
                detail=err.reason,
            )
            for err in result.scan_errors
        ]
        return [self._summary(card) for card in result.candidates], errors

    def draft_detail(self, rel_or_id: str) -> DraftDetailResponse | None:
        card = self._find_draft(rel_or_id)
        if card is None:
            return None
        preview = preview_approval_card(self.cfg, card.path)
        if preview.error is not None or preview.card_path is None:
            return None
        body = read_card_body(preview.card_path)
        return DraftDetailResponse(
            draft=self._summary(card),
            frontmatter=preview.fields,
            body=body,
            source_context=self._source_context(card, preview.fields),
        )

    def approve(self, rel_or_id: str, *, confirm: bool, reviewed_source: bool) -> ApprovalResponse:
        if not confirm or not reviewed_source:
            return ApprovalResponse(
                ok=False,
                status="confirmation_required",
                message="Approve 需要 confirm=true 且 reviewed_source=true。",
            )
        card = self._find_draft(rel_or_id)
        if card is None:
            return ApprovalResponse(
                ok=False,
                status="not_found",
                message="未找到可 approve 的 ai_draft。",
            )
        result = approve_explicit_card(self.cfg, card.path)
        if result.error is not None:
            return ApprovalResponse(
                ok=False,
                status=result.error.kind,
                message=result.error.message,
                card_path=str(card.path),
                previous_status=result.error.prev_status,
            )
        assert result.effect is not None
        effect = result.effect
        index_updated = False
        index_path = None
        index_error = None
        if effect.kind == "approved":
            try:
                # 中文学习型说明：Web approve 与 CLI approve 共享“人审后刷新
                # BM25”的本地索引边界；这里不读 .env、不调 provider，只重建
                # approved card 的本地 lexical index。
                rebuilt = rebuild_index_for_config(self.cfg)
                index_updated = True
                index_path = str(rebuilt.path)
            except Exception as exc:  # pragma: no cover - UI 用结构化错误兜底
                index_error = f"{type(exc).__name__}: {exc}"
        return ApprovalResponse(
            ok=True,
            status=effect.kind,
            message="Draft 已显式晋升为 human_approved。",
            card_path=str(effect.card_path),
            previous_status=effect.prev_status,
            new_status=effect.new_status,
            idempotent=effect.kind == "already_approved",
            index_updated=index_updated,
            index_path=index_path,
            index_error=index_error,
        )

    def update_draft_body(self, rel_or_id: str, body: str) -> CardBodyUpdateResponse | None:
        card = self._find_draft(rel_or_id)
        if card is None:
            return None
        try:
            result = update_card_body(self.cfg, card.path, body, expected_status="ai_draft")
        except CardWorkspaceError as exc:
            return CardBodyUpdateResponse(
                ok=False,
                status="error",
                message=str(exc),
                card_path=str(card.path),
                rel_path=card.rel_path,
            )
        return CardBodyUpdateResponse(
            ok=True,
            status=result.status,
            message="Draft body saved; status remains ai_draft.",
            card_path=str(result.card_path),
            rel_path=card.rel_path,
            index_updated=result.index_updated,
            index_path=str(result.index_path) if result.index_path else None,
            index_error=result.index_error,
        )

    def reject_unavailable(self) -> UnavailableResponse:
        return UnavailableResponse(
            reason=(
                "当前核心后端尚未提供安全的 reject 持久化 service。Web v1 不伪造"
                " reject 成功，也不会静默改写 draft。"
            ),
            next_action=NextAction(
                label="Leave draft pending",
                description="先保留 draft，下一 slice 增加 reject/defer 的核心 service 后再开放。",
            ),
        )

    def _find_draft(self, rel_or_id: str) -> CardSummary | None:
        drafts, _errors = self.list_drafts()
        by_path: dict[str, DraftSummary] = {}
        for draft in drafts:
            by_path[draft.rel_path] = draft
            by_path[Path(draft.rel_path).name] = draft
            if draft.id:
                by_path[draft.id] = draft
        target = by_path.get(rel_or_id)
        if target is None:
            return None
        result = list_approval_candidates(
            self.cfg,
            ApprovalListQuery(statuses=("ai_draft",), limit=500),
        )
        for card in result.candidates:
            if card.rel_path == target.rel_path:
                return card
        return None

    @staticmethod
    def _summary(card: CardSummary) -> DraftSummary:
        strategy = strategy_display(card.strategy_id)
        return DraftSummary(
            id=card.id,
            title=card.title,
            path=str(card.path),
            rel_path=card.rel_path,
            status=card.status,
            track=card.track,
            projects=list(card.projects),
            tags=list(card.tags),
            source_type=card.source_type,
            source_id=card.source_id,
            source_title=card.source_title,
            source_path=card.source_path,
            source_archive_path=card.source_archive_path,
            source_content_hash=card.source_content_hash,
            value_score=card.value_score,
            profile=card.profile,
            provider=card.provider,
            strategy_id=card.strategy_id,
            strategy_label=strategy.label,
            strategy_note=strategy.note,
            strategy_canonical_id=strategy.canonical_id,
            strategy_version=card.strategy_version,
            schema_version=card.schema_version,
            prompt_version=card.prompt_version,
            prompt_versions=dict(card.prompt_versions),
            stage_models=dict(card.stage_models),
            run_id=card.run_id,
            created_at=card.created_at.isoformat() if card.created_at else None,
            updated_at=card.updated_at.isoformat() if card.updated_at else None,
        )

    @staticmethod
    def _source_context(card: CardSummary, fields: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_type": card.source_type,
            "source_id": card.source_id,
            "source_path": card.source_path,
            "source_content_hash": card.source_content_hash,
            "source_title": card.source_title,
            "source_url": card.source_url,
            "track": card.track,
            "projects": list(card.projects),
            "tags": list(card.tags),
            "frontmatter_preview": fields,
        }
