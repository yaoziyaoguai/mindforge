"""MindForge Web facade.

中文学习型说明：Facade 是 Web 场景编排层。它知道 Home/Setup/Sources/Drafts
这些页面需要哪些数据，但不拥有 approval/recall/provider/source 的核心规则。
Router 调 Facade，Facade 调现有 MindForge service，这样 Web 不会长成新的
业务巨石。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException

from mindforge.app_context import build_app_context
from mindforge.cards import iter_cards
from mindforge.card_workspace_service import CardWorkspaceError, update_card_body
from mindforge.checkpoint import Checkpoint, CheckpointError
from mindforge.lexical_index import default_index_path
from mindforge.library_service import (
    LibraryCardDetail,
    LibraryLookupError,
    build_library_inventory,
    show_library_card,
)
from mindforge.recall_service import RecallQuery, RecallServiceError, run_bm25_recall
from mindforge.strategy_display import strategy_display

from mindforge_web.schemas import (
    ConfigStatusResponse,
    DraftDetailResponse,
    DraftsResponse,
    CardBodyUpdateResponse,
    HealthResponse,
    HomeStatusResponse,
    IngestionActionResponse,
    LibraryCardDetailResponse,
    LibraryCardResponse,
    LibraryCardsResponse,
    LibraryStatsResponse,
    NextAction,
    RecallHit,
    RecallResponse,
    RecallStatus,
    SafetySummary,
    SetupConfigPatch,
    SetupConfigUpdateResponse,
    SetupEditableConfigResponse,
    SetupValidationResponse,
    PathActionResponse,
    ProcessingRunResponse,
    SourcesResponse,
    StatusItem,
    VaultStatus,
    WatchSourcesResponse,
    WorkspaceStatus,
    WorkflowSummaryResponse,
)
from mindforge_web.services.web_config_service import ConfigUpdateError, WebConfigService
from mindforge_web.services.processing_run_service import get_processing_run, processing_run_response
from mindforge_web.services.web_path_action_service import WebPathActionService
from mindforge_web.services.web_review_service import WebReviewService
from mindforge_web.services.web_source_service import WebSourceService


class WebFacade:
    """Web use-case facade for one local MindForge config/vault."""

    def __init__(
        self,
        *,
        config_path: Path = Path("configs/mindforge.yaml"),
        vault_override: Path | None = None,
        host: str = "127.0.0.1",
    ) -> None:
        self.requested_config_path = config_path
        self.vault_override = vault_override
        self.host = host
        self._load_context()

    def _load_context(self) -> None:
        self.context = build_app_context(
            self.requested_config_path,
            vault_override=self.vault_override,
        )
        self.cfg = self.context.config
        self.config_path = self.context.paths.config_path
        self.config_service = WebConfigService(self.cfg, config_path=self.config_path)
        self.source_service = WebSourceService(self.cfg)
        self.path_action_service = WebPathActionService(self.cfg, config_path=self.config_path)
        self.review_service = WebReviewService(self.cfg)

    def health(self) -> HealthResponse:
        return HealthResponse(ok=True, local_only=self.host in {"127.0.0.1", "localhost"})

    def home_status(self) -> HomeStatusResponse:
        cards_scan = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        status_counts: dict[str, int] = {}
        for card in cards_scan.cards:
            status_counts[card.status] = status_counts.get(card.status, 0) + 1
        safety = self.safety_summary(status_counts=status_counts)
        workspace = self.workspace_status()
        vault = self.vault_status(status_counts=status_counts, scan_error_count=len(cards_scan.errors))
        provider = self.config_service.provider_status()
        recall = self.recall_status(approved_count=status_counts.get("human_approved", 0))
        return HomeStatusResponse(
            safety=safety,
            workspace=workspace,
            vault=vault,
            provider=provider,
            env_keys=[],
            recall=recall,
            cards_by_status=status_counts,
            next_actions=self._next_actions(vault, safety, recall),
        )

    def config_status(self) -> ConfigStatusResponse:
        env_keys = self.config_service.env_key_statuses()
        status_counts = self._card_status_counts()
        safety = self.safety_summary(status_counts=status_counts)
        vault = self.vault_status(status_counts=status_counts)
        provider = self.config_service.provider_status()
        configured = [item for item in env_keys if item.configured]
        missing = [item for item in env_keys if not item.configured]
        checklist = [
            StatusItem(
                key="config",
                label="Config file",
                status="ok",
                value=str(self.config_path),
                detail="Config 已加载；Web 未返回 secret value。",
            ),
            StatusItem(
                key="vault",
                label="Vault path",
                status="ok" if vault.exists else "warn",
                value=vault.path,
                detail="真实 vault 会以 amber warning 显示；写入动作仍需显式确认。",
            ),
            StatusItem(
                key="provider",
                label="Model setup",
                status="ok" if provider.model_setup == "ready" else "warn",
                value=provider.model_setup_label,
                detail="Model setup 只检查 metadata 与 local secret store presence，不调用真实 LLM。",
            ),
            StatusItem(
                key="env",
                label="Process environment diagnostics",
                status="ok" if not missing else "warn",
                value=f"{len(configured)} env vars present",
                detail=(
                    "Advanced diagnostics only. Provider defaults may still supply "
                    "effective non-secret model/base URL values."
                ),
            ),
            self.config_service.cubox_status_item(),
        ]
        return ConfigStatusResponse(
            safety=safety,
            config_path=str(self.config_path),
            configured_keys=configured,
            missing_keys=missing,
            provider=provider,
            cubox=self.config_service.cubox_status_item(),
            vault=vault,
            checklist=checklist,
            next_actions=self._next_actions(vault, safety, self.recall_status()),
        )

    def setup_editable_config(self) -> SetupEditableConfigResponse:
        return self.config_service.editable_config()

    def validate_setup_config_patch(self, patch: SetupConfigPatch) -> SetupValidationResponse:
        return self.config_service.validate_patch(patch)

    def update_setup_config_patch(self, patch: SetupConfigPatch) -> SetupConfigUpdateResponse:
        try:
            self.config_service.update_patch(patch)
        except ConfigUpdateError:
            raise
        self._load_context()
        return SetupConfigUpdateResponse(
            ok=True,
            message="Setup saved",
            status=self.config_status(),
            editable=self.setup_editable_config(),
        )

    def workspace_status(self) -> WorkspaceStatus:
        state_exists = self.cfg.state.state_path.exists()
        item_count = 0
        source_counts: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        if state_exists:
            try:
                checkpoint = Checkpoint.load(self.cfg.state.state_path)
                items = list(checkpoint.all_items())
                item_count = len(items)
                source_counts = checkpoint.count_by_source_type()
                status_counts = checkpoint.count_by_status()
            except CheckpointError:
                source_counts = {}
                status_counts = {}
        return WorkspaceStatus(
            config_path=str(self.config_path),
            state_path=str(self.cfg.state.state_path),
            state_exists=state_exists,
            state_item_count=item_count,
            source_counts=source_counts,
            status_counts=status_counts,
        )

    def sources(self) -> SourcesResponse:
        sources = self.source_service.list_sources()
        next_actions = [
            NextAction(
                label="Watch or import source",
                description="Web 主入口是 watch/import；自动化只生成 ai_draft。",
                href="/sources",
            )
        ]
        watches = self.source_service.watch_sources()
        return SourcesResponse(
            sources=sources,
            bucket_counts=self.source_service.bucket_counts(),
            watched_sources=watches.watched_sources,
            available_imports=self.source_service.available_imports(),
            ingestion=self.source_service.ingestion_status(),
            next_actions=next_actions,
        )

    def watch_sources(self) -> WatchSourcesResponse:
        return self.source_service.watch_sources()

    def watch_add(
        self,
        path: Path,
        *,
        frequency: str | None = None,
        recursive: bool | None = None,
        process_now: bool = True,
    ) -> IngestionActionResponse:
        try:
            return self.source_service.watch_add(
                path,
                frequency=frequency,
                recursive=recursive,
                process_now=process_now,
            )
        except ValueError as exc:
            raise _http_error(400, str(exc)) from exc
        except RuntimeError as exc:
            raise _http_error(500, str(exc)) from exc

    def watch_scan(self, ref: str | None = None, *, all_sources: bool = False) -> IngestionActionResponse:
        try:
            return self.source_service.watch_scan(ref=ref, all_sources=all_sources)
        except ValueError as exc:
            raise _http_error(400, str(exc)) from exc
        except RuntimeError as exc:
            raise _http_error(500, str(exc)) from exc

    def processing_run(self, run_id: str) -> ProcessingRunResponse | None:
        record = get_processing_run(self.cfg, run_id)
        if record is None:
            return None
        return processing_run_response(record)

    def watch_delete(self, ref: str) -> IngestionActionResponse:
        return self.source_service.watch_delete(ref)

    def watch_frequency(self, ref: str, frequency: str) -> IngestionActionResponse:
        return self.source_service.watch_frequency(ref, frequency)

    def import_source(self, path: Path) -> IngestionActionResponse:
        try:
            return self.source_service.import_source(path)
        except ValueError as exc:
            raise _http_error(400, str(exc)) from exc
        except RuntimeError as exc:
            raise _http_error(500, str(exc)) from exc

    def copy_path(self, path: Path) -> PathActionResponse:
        return self.path_action_service.copy_path(path)

    def reveal_path(self, path: Path) -> PathActionResponse:
        return self.path_action_service.reveal_path(path)

    def workflow_summary(self) -> WorkflowSummaryResponse:
        inventory = build_library_inventory(self.cfg, limit=500)
        bucket_counts = self.source_service.bucket_counts()
        pending_count = sum(bucket_counts.get("pending", {}).values())
        processed_count = sum(bucket_counts.get("processed", {}).values())
        return WorkflowSummaryResponse(
            vault_root=str(self.cfg.vault.root),
            cards_dir=self.cfg.vault.cards_dir,
            inbox_pending_count=pending_count,
            processed_source_count=processed_count,
            ai_draft_count=inventory.stats.by_status.get("ai_draft", 0),
            human_approved_count=inventory.stats.by_status.get("human_approved", 0),
            index=self.recall_status(
                approved_count=inventory.stats.by_status.get("human_approved", 0)
            ),
            provider=self.config_service.provider_status(),
            source_bucket_counts=bucket_counts,
            next_actions=self._next_actions(
                self.vault_status(status_counts=inventory.stats.by_status),
                self.safety_summary(status_counts=inventory.stats.by_status),
                self.recall_status(),
            ),
        )

    def library_cards(self) -> LibraryCardsResponse:
        inventory = build_library_inventory(self.cfg, limit=500)
        return LibraryCardsResponse(
            stats=_library_stats_response(inventory.stats),
            cards=[_library_card_response(card) for card in inventory.cards],
        )

    def library_card_detail(self, ref: str, *, show_content: bool = False) -> LibraryCardDetailResponse | None:
        detail = show_library_card(self.cfg, ref, show_content=show_content)
        if isinstance(detail, LibraryLookupError):
            return None
        return _library_detail_response(detail)

    def update_library_card_body(self, ref: str, body: str) -> CardBodyUpdateResponse | None:
        detail = show_library_card(self.cfg, ref, show_content=False)
        if isinstance(detail, LibraryLookupError):
            return None
        card = detail.card.summary
        try:
            result = update_card_body(self.cfg, card.path, body, expected_status=card.status)
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
            message=(
                "Approved card saved and recall index refreshed."
                if result.index_updated
                else "Card body saved."
            ),
            card_path=str(result.card_path),
            rel_path=card.rel_path,
            index_updated=result.index_updated,
            index_path=str(result.index_path) if result.index_path else None,
            index_error=result.index_error,
        )

    def drafts(self) -> DraftsResponse:
        drafts, errors = self.review_service.list_drafts()
        empty = None
        if not drafts:
            empty = NextAction(
                label="Create drafts",
                description="没有 ai_draft。先在 Sources 页 watch add 或 import 文件/文件夹。",
                href="/sources",
            )
        return DraftsResponse(drafts=drafts, scan_errors=errors, empty_state=empty)

    def draft_detail(self, draft_id: str) -> DraftDetailResponse | None:
        return self.review_service.draft_detail(draft_id)

    def update_draft_body(self, draft_id: str, body: str) -> CardBodyUpdateResponse | None:
        return self.review_service.update_draft_body(draft_id, body)

    def recall(self, query: str) -> RecallResponse:
        index = self.recall_status()
        if not query.strip():
            return RecallResponse(
                query=query,
                hits=[],
                index=index,
                empty_state=NextAction(
                    label="Search approved cards",
                    description="输入关键词后会用本地 lexical recall 查询 human_approved cards。",
                ),
            )
        try:
            result = run_bm25_recall(
                self.cfg,
                RecallQuery(
                    query=query,
                    track=None,
                    project=None,
                    tags=(),
                    source_type=None,
                    status="human_approved",
                    include_drafts=False,
                    since=None,
                    until=None,
                    limit=10,
                    output_format="json",
                    explain=False,
                ),
            )
        except RecallServiceError as exc:
            return RecallResponse(
                query=query,
                hits=[],
                index=index,
                warnings=[str(exc)],
                empty_state=NextAction(
                    label="Adjust query",
                    description="Recall query 无法执行，请缩短或调整关键词。",
                ),
            )
        return RecallResponse(
            query=query,
            hits=[
                RecallHit(
                    score=hit.score,
                    title=hit.title,
                    card_ref=hit.id or Path(hit.rel_path).name,
                    detail_href=f"/library?card={hit.id or hit.rel_path}",
                    rel_path=hit.rel_path,
                    status=hit.status,
                    track=hit.track,
                    projects=list(hit.projects),
                    tags=list(hit.tags),
                    source_type=hit.source_type,
                    why_this_matched=hit.why_this_matched,
                )
                for hit in result.hits
            ],
            index=RecallStatus(
                index_path=str(result.index.path),
                index_exists=result.index.path.exists(),
                approved_card_count=result.index.card_counts.get("human_approved", 0),
                available=True,
                next_action=NextAction(
                    label="Rebuild index",
                    description="索引缺失或 stale 时可重建本地 BM25 index。",
                    command="mindforge index rebuild",
                )
                if result.index.suggest_rebuild
                else None,
            ),
            warnings=list(result.warnings),
            empty_state=None
            if result.hits
            else NextAction(
                label="Try another query",
                description="没有命中 approved cards；换一个关键词或先 approve draft。",
            ),
        )

    def safety_summary(self, *, status_counts: dict[str, int] | None = None) -> SafetySummary:
        status_counts = status_counts or self._card_status_counts()
        provider = self.config_service.provider_status()
        vault_real = self._is_real_environment()
        warnings: list[str] = []
        if vault_real:
            warnings.append("Real-looking vault is active; writes require explicit user action.")
        if provider.model_setup != "ready":
            warnings.append("Model setup needs attention; no hidden provider calls are made.")
        return SafetySummary(
            local_only=self.host in {"127.0.0.1", "localhost"},
            host=self.host,
            vault_path=str(self.cfg.vault.root),
            vault_status="warn" if vault_real else "ok",
            provider_state=provider.model_setup,
            env_status="ok" if provider.model_setup == "ready" else "info",
            write_mode="explicit_approval_required",
            pending_drafts_count=status_counts.get("ai_draft", 0),
            warnings=warnings,
        )

    def vault_status(
        self,
        *,
        status_counts: dict[str, int] | None = None,
        scan_error_count: int | None = None,
    ) -> VaultStatus:
        status_counts = status_counts or self._card_status_counts()
        errors = 0 if scan_error_count is None else scan_error_count
        return VaultStatus(
            path=str(self.cfg.vault.root),
            exists=self.cfg.vault.root.exists(),
            inbox_exists=self.cfg.vault.inbox_path.exists(),
            cards_exists=self.cfg.vault.cards_path.exists(),
            projects_exists=self.cfg.vault.projects_path.exists(),
            approved_card_count=status_counts.get("human_approved", 0),
            draft_card_count=status_counts.get("ai_draft", 0),
            scan_error_count=errors,
            is_real_environment=self._is_real_environment(),
        )

    def recall_status(self, approved_count: int | None = None) -> RecallStatus:
        count = approved_count
        if count is None:
            count = self._card_status_counts().get("human_approved", 0)
        index_path = default_index_path(self.cfg.state.workdir)
        return RecallStatus(
            index_path=str(index_path),
            index_exists=index_path.exists(),
            approved_card_count=count,
            available=True,
            next_action=NextAction(
                label="Approve drafts",
                description="Recall 默认只查询 human_approved cards。",
                href="/drafts",
            )
            if count == 0
            else None,
        )

    def _resolve_draft_path(self, draft_id: str) -> Path:
        """根据 draft_id 解析 ai_draft 卡片路径。"""
        detail = self.review_service.draft_detail(draft_id)
        if detail is None:
            raise FileNotFoundError(f"draft {draft_id} not found")
        return self.cfg.vault.cards_path / detail.draft.rel_path

    def _resolve_library_card_path(self, card_ref: str) -> Path:
        """根据 card_ref 解析 approved 卡片路径。"""
        from mindforge.cards import iter_cards
        scan = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        for c in scan.cards:
            if c.id == card_ref or card_ref in str(c.rel_path) or c.rel_path.endswith(card_ref):
                return self.cfg.vault.root / c.rel_path
        raise FileNotFoundError(f"card {card_ref} not found")

    def _card_status_counts(self) -> dict[str, int]:
        scan = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        counts: dict[str, int] = {}
        for card in scan.cards:
            counts[card.status] = counts.get(card.status, 0) + 1
        return counts

    def _is_real_environment(self) -> bool:
        root = self.cfg.vault.root.expanduser().resolve()
        text = str(root)
        return (
            "demo-vault" not in text
            and "dogfood-vault" not in text
            and "tmp" not in root.parts
            and root.exists()
        )

    @staticmethod
    def _next_actions(vault: VaultStatus, safety: SafetySummary, recall: RecallStatus) -> list[NextAction]:
        actions: list[NextAction] = []
        if not vault.exists:
            actions.append(
                NextAction(
                    label="Initialize vault",
                    description="当前 vault 路径不存在；先创建本地 vault 或传 --vault。",
                    command="mindforge init",
                )
            )
        if safety.pending_drafts_count > 0:
            actions.append(
                NextAction(
                    label="Review drafts",
                    description="有 ai_draft 等待人工 review 和显式 approve/reject。",
                    href="/drafts",
                )
            )
        if recall.approved_card_count == 0:
            actions.append(
                NextAction(
                    label="Watch or import source",
                    description="还没有 approved cards；先添加 source 生成 ai_draft，再显式 approve。",
                    href="/sources",
                )
            )
        if not actions:
            actions.append(
                NextAction(
                    label="Search knowledge",
                    description="本地状态已可用；可以进入 Recall 搜索 approved cards。",
                    href="/recall",
                )
            )
        return actions


def _library_stats_response(stats) -> LibraryStatsResponse:
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


def _http_error(status_code: int, message: str) -> HTTPException:
    """把用户主路径错误保持为前端可读的 `{detail:{message}}`。

    中文学习型说明：Add Source / Process Now 是普通用户第一阶段主链路。
    后端拒绝相对路径、缺模型或其它用户可修复错误时，不能只返回字符串
    detail，否则 Web fetch helper 会退化成浏览器的 `Bad Request` 文案。
    """

    return HTTPException(status_code=status_code, detail={"message": message})


def _library_card_response(card) -> LibraryCardResponse:
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
        approved_at=None,
        updated_at=summary.updated_at.isoformat() if summary.updated_at else None,
        rel_path=summary.rel_path,
        fallback_provider_note=card.fallback_provider_note,
    )


def _library_detail_response(detail: LibraryCardDetail) -> LibraryCardDetailResponse:
    return LibraryCardDetailResponse(
        card=_library_card_response(detail.card),
        body=detail.body,
    )
    WatchSourcesResponse,
