"""MindForge Web facade.

中文学习型说明：Facade 是 Web 场景编排层。它知道 Home/Setup/Sources/Drafts
这些页面需要哪些数据，但不拥有 approval/recall/provider/source 的核心规则。
Router 调 Facade，Facade 调现有 MindForge service，这样 Web 不会长成新的
业务巨石。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from mindforge_web.schemas import SensemakingResponse

from fastapi import HTTPException

from mindforge.app_context import build_app_context
from mindforge_web.services.web_import_export_service import WebImportExportService
from mindforge_web.services.web_lab_service import WebLabService
from mindforge_web.services.web_recall_service import WebRecallService
from mindforge.cards import CardSummary, iter_cards
from mindforge.card_workspace_service import CardWorkspaceError, update_card_body
from mindforge.checkpoint import Checkpoint, CheckpointError
from mindforge.config import MindForgeConfig

from mindforge.library_service import (
    LibraryCardDetail,
    LibraryLookupError,
    build_library_inventory,
    show_library_card,
)

from mindforge.relations.discovery_context import (
    DiscoveryCommunityRef,
    DiscoveryContext,
)
from mindforge.relations.graph_builder import DeterministicGraphBuilder
from mindforge.relations.graph_models import (
    Graph as GraphResult,
    GraphEdge,
    GraphNode,
)
from mindforge.relations.local_graph import LocalGraph, NodeType, build_card_centered_graph
from mindforge.relations.related_cards import RelatedCardEdge, compute_multi_hop_related_cards
from mindforge.health.health_service import build_knowledge_health_report
from mindforge.strategy_display import strategy_display

from mindforge_web.schemas import (
    ConfigStatusResponse,
    DiscoveryCardRefResponse,
    DiscoveryCommunityRefResponse,
    DiscoveryContextResponse,
    DiscoverySectionRefResponse,
    DiscoverySourceRefResponse,
    DiscoveryTagRefResponse,
    DraftDetailResponse,
    DraftsResponse,
    DogfoodReportResponse,
    ProviderAliasStatus,
    ProviderReadinessResponse,
    CardBodyUpdateResponse,
    GraphEdgeDetailResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    HealthIssueResponse,
    HealthReportResponse,
    HealthResponse,
    HomeStatusResponse,
    FolderImportPreviewResponse,
    FolderImportResponse,
    ImportCardResponse,
    IngestionActionResponse,
    LifecycleResponse,
    LibraryCardDetailResponse,
    LibraryCardResponse,
    LibraryCardsResponse,
    LibraryStatsResponse,
    LocalGraphEdgeResponse,
    LocalGraphNodeResponse,
    LocalGraphResponse,
    NextAction,
    RecallResponse,
    RecallStatus,
    SourceLifecycleItem,
    ProvenanceTrailRelatedSource,
    ProvenanceTrailResponse,
    ProvenanceTrailSection,
    ProvenanceTrailSiblingCard,
    ProvenanceTrailSource,
    RelatedCardReasonResponse,
    RelatedCardResponse,
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
        self.path_action_service = WebPathActionService(self.cfg, config_path=self.config_path)
        self.source_service = WebSourceService(self.cfg, path_action_service=self.path_action_service)
        self.review_service = WebReviewService(self.cfg)
        self._lab_service = WebLabService(self.cfg)
        self._import_export_service = WebImportExportService(self.cfg)
        self._recall_service = WebRecallService(self.cfg)

    def health(self) -> HealthResponse:
        return HealthResponse(ok=True, local_only=self.host in {"127.0.0.1", "localhost"})

    def knowledge_health_report(self) -> HealthReportResponse:
        try:
            report = build_knowledge_health_report(self.cfg)
        except Exception:  # noqa: BLE001 — diagnostic fallback
            return HealthReportResponse(
                summary="无法生成健康报告，请检查 vault 和 cards 目录是否可读。",
                stats={},
                issues=[],
                maintenance_suggestions=[],
            )
        return HealthReportResponse(
            summary=report.summary,
            stats=report.stats,
            issues=[
                HealthIssueResponse(
                    code=issue.code,
                    severity=issue.severity.value,
                    message=issue.message,
                    suggested_action=issue.suggested_action,
                    reason=issue.reason,
                    affected_card_ids=list(issue.affected_card_ids),
                )
                for issue in report.issues
            ],
            maintenance_suggestions=list(report.maintenance_suggestions),
        )

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

    def set_provider_mode(self, mode: Literal["fake", "real"]) -> ConfigStatusResponse:
        self.config_service.write_provider_mode(mode)
        return self.config_status()

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
                action_key="watch_source",
                description_key="watch_source.desc",
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
        return processing_run_response(record, path_action_service=self.path_action_service)

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

    def reveal_by_ref(
        self, *, card_id: str | None = None, draft_id: str | None = None
    ) -> PathActionResponse:
        """安全的 object-reference reveal —— 不接受 raw path。"""
        return self.path_action_service.reveal_by_ref(card_id=card_id, draft_id=draft_id)

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
        cards = [_library_card_response(card) for card in inventory.cards]
        for c in cards:
            c.source_path_view = self.path_action_service.build_source_path_view(
                c.source_path, source_title=c.source_title,
                source_archive_path=c.source_archive_path,
            )
            # 中文学习型说明：API contract 安全边界 —— source_path 对 unsafe
            # path_kind 必须 redact 为 None，由 source_path_view.display_path
            # 提供安全展示。这里在组装 response 后统一 redact。
            c.source_path = self.path_action_service.safe_source_path(
                c.source_path, c.source_path_view
            )
        return LibraryCardsResponse(
            stats=_library_stats_response(inventory.stats),
            cards=cards,
        )

    def library_card_detail(self, ref: str, *, show_content: bool = False) -> LibraryCardDetailResponse | None:
        detail = show_library_card(self.cfg, ref, show_content=show_content)
        if isinstance(detail, LibraryLookupError):
            return None
        return _library_detail_response(self.cfg, detail, path_action_service=self.path_action_service)

    def provenance_trail(self, ref: str) -> ProvenanceTrailResponse | None:
        """U3 Provenance Trail — source → sibling cards → wiki sections。"""
        detail = show_library_card(self.cfg, ref, show_content=False)
        if isinstance(detail, LibraryLookupError):
            return None
        return _provenance_trail_response(self.cfg, detail)

    def knowledge_communities(self) -> object:
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.knowledge_communities()

    def knowledge_topics(self) -> object:
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.knowledge_topics()

    # ── v0.6 Graph API ──────────────────────────────

    def get_graph_node(self, ref: str, *, depth: int = 2) -> GraphResponse | None:
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.get_graph_node(ref, depth=depth)

    def get_graph_explore(
        self, node_type: str, node_id: str, *, depth: int = 1,
    ) -> GraphResponse | None:
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.get_graph_explore(node_type, node_id, depth=depth)

    def get_graph_edge(self, source: str, target: str) -> GraphEdgeDetailResponse | None:
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.get_graph_edge(source, target)

    def get_sensemaking(self, ref: str) -> "SensemakingResponse | None":
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.get_sensemaking(ref)

    def get_discovery_context(self, ref: str) -> DiscoveryContextResponse | None:
        """LAB/INTERNAL — 委托给 WebLabService。"""
        return self._lab_service.get_discovery_context(ref)

    def compute_card_quality(self, card_id: str):
        """计算单张卡片的 quality metadata（M1 — SDD §4.1）。"""
        from mindforge.cards import CardScanResult, iter_cards
        from mindforge_web.services.web_quality_service import compute_card_quality as _compute

        result: CardScanResult = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        matching = [c for c in result.cards if c.id == card_id or c.path.name == card_id]
        if not matching:
            return None
        card = matching[0]
        all_titles = [c.title for c in result.cards if c.title]
        return _compute(card, self.cfg.vault.root, all_titles)

    def compute_card_location(self, card_id: str):
        """计算单张卡片的 source location（M4 — SDD §8.1）。"""
        from mindforge.cards import iter_cards
        from mindforge.provenance.location import SourceLocation

        result = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        matching = [c for c in result.cards if c.id == card_id or c.path.name == card_id]
        if not matching:
            return None
        card = matching[0]
        source_type = card.source_type or "plain_markdown"

        heading_path = tuple(card.tags) if card.tags else None

        return SourceLocation(source_type=source_type, heading_path=heading_path)

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

    def import_card(self, title: str, body: str, source_name: str = "") -> ImportCardResponse:
        """从 Markdown 内容创建 ai_draft 卡片 — 委托给 WebImportExportService。"""
        return self._import_export_service.import_card(title, body, source_name)

    def preview_folder_import(self, folder_path: str) -> FolderImportPreviewResponse:
        """扫描文件夹中的 .md 文件 — 委托给 WebImportExportService。"""
        return self._import_export_service.preview_folder_import(folder_path)

    def import_from_folder(
        self, folder_path: str, indices: list[int],
    ) -> FolderImportResponse:
        """批量导入文件夹中的 .md 文件 — 委托给 WebImportExportService。"""
        return self._import_export_service.import_from_folder(folder_path, indices)

    def drafts(self) -> DraftsResponse:
        drafts, errors = self.review_service.list_drafts()
        for d in drafts:
            d.source_path_view = self.path_action_service.build_source_path_view(
                d.source_path, source_title=d.source_title,
                source_archive_path=d.source_archive_path,
            )
            d.source_path = self.path_action_service.safe_source_path(
                d.source_path, d.source_path_view
            )
        empty = None
        if not drafts:
            empty = NextAction(
                label="Create drafts",
                description="没有 ai_draft。先在 Sources 页 watch add 或 import 文件/文件夹。",
                href="/sources",
                action_key="create_drafts",
                description_key="create_drafts.desc",
            )
        return DraftsResponse(drafts=drafts, scan_errors=errors, empty_state=empty)

    def draft_detail(self, draft_id: str) -> DraftDetailResponse | None:
        result = self.review_service.draft_detail(draft_id)
        if result is not None:
            result.draft.source_path_view = self.path_action_service.build_source_path_view(
                result.draft.source_path, source_title=result.draft.source_title,
                source_archive_path=result.draft.source_archive_path,
            )
            result.draft.source_path = self.path_action_service.safe_source_path(
                result.draft.source_path, result.draft.source_path_view
            )
            # 中文学习型说明：source_context 中的 source_path 同样需要
            # redact，不与 raw card 值混用。
            if result.source_context and "source_path" in result.source_context:
                result.source_context["source_path"] = self.path_action_service.safe_source_path(
                    result.source_context.get("source_path"),
                    result.draft.source_path_view,
                )
        return result

    def update_draft_body(self, draft_id: str, body: str) -> CardBodyUpdateResponse | None:
        return self.review_service.update_draft_body(draft_id, body)

    def recall(self, query: str, *, context: str | None = None) -> RecallResponse:
        """BM25 lexical recall — 委托给 WebRecallService。"""
        return self._recall_service.recall(query, context=context)

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
        """BM25 索引状态 — 委托给 WebRecallService。"""
        return self._recall_service.recall_status(approved_count)

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
        # 中文学习型说明：action_key 是稳定的展示映射键，前端通过 nextActionLabel(action_key, locale)
        # 生成本地化文案。label/description 保留为 fallback，缺 action_key 时兜底展示。
        # i18n 只改变 presentation 层，不改变 action 行为（href/command 不变）。
        if not vault.exists:
            actions.append(
                NextAction(
                    label="Initialize vault",
                    description="当前 vault 路径不存在；先创建本地 vault 或传 --vault。",
                    command="mindforge init",
                    action_key="init_vault",
                    description_key="init_vault.desc",
                )
            )
        if safety.pending_drafts_count > 0:
            actions.append(
                NextAction(
                    label="Review drafts",
                    description="有 ai_draft 等待人工 review 和显式 approve/reject。",
                    href="/drafts",
                    action_key="review_drafts",
                    description_key="review_drafts.desc",
                )
            )
        if recall.approved_card_count == 0:
            actions.append(
                NextAction(
                    label="Watch or import source",
                    description="还没有 approved cards；先添加 source 生成 ai_draft，再显式 approve。",
                    href="/sources",
                    action_key="watch_source",
                    description_key="watch_source.desc",
                )
            )
        if not actions:
            actions.append(
                NextAction(
                    label="Search knowledge",
                    description="本地状态已可用；可以进入 Recall 搜索 approved cards。",
                    href="/recall",
                    action_key="search_knowledge",
                    description_key="search_knowledge.desc",
                )
            )
        return actions

    # ── v2.5 U3 Dogfood Report ──────────────────────────────────────

    def dogfood_report(self) -> DogfoodReportResponse:
        """生成工作台使用报告 — 纯本地数据聚合，不调用 LLM。

        中文学习型说明：报告从 vault cards / sources / wiki / graph / search
        的现有数据中计算统计值，不生成新内容，不修改任何文件。
        """
        from datetime import datetime, timezone
        from mindforge.cards import iter_cards
        from mindforge.wiki_service import get_wiki_status

        now = datetime.now(timezone.utc).isoformat()

        # 扫描所有卡片
        scan = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        cards = list(scan.cards)

        total = len(cards)
        approved = [c for c in cards if c.status == "human_approved"]
        drafts = [c for c in cards if c.status == "ai_draft"]
        imported = [c for c in cards if c.status == "imported"]

        approved_count = len(approved)
        draft_count = len(drafts)
        imported_count = len(imported)
        error_count = len(scan.errors)

        approval_rate = approved_count / total if total > 0 else 0.0

        # 统计 source 数（去重 source_id）
        source_ids = {c.source_id for c in cards if c.source_id}
        source_count = len(source_ids)

        # Graph 密度：使用 DeterministicGraphBuilder 获取关系数
        relation_count = 0
        try:
            builder = _build_graph_builder(self.cfg)
            if builder is not None and approved_count > 0:
                # 取一张已确认卡片作为入口获取 graph snapshot
                first_id = approved[0].id or approved[0].rel_path
                graph = builder.get_graph(first_id, depth=1)
                # 计算所有唯一边
                edges_seen: set[tuple[str, str]] = set()
                for edge in graph.edges:
                    pair = (edge.source, edge.target)
                    if pair not in edges_seen and (pair[1], pair[0]) not in edges_seen:
                        edges_seen.add(pair)
                relation_count = len(edges_seen)
        except Exception:
            relation_count = 0
        graph_density = relation_count / total if total > 0 else 0.0

        # 社区数
        community_count = len(source_ids)

        # Wiki 状态
        try:
            ws = get_wiki_status(self.cfg)
            wiki_section_count = ws.approved_card_count
            wiki_stale = ws.is_stale
        except Exception:
            wiki_section_count = 0
            wiki_stale = False

        # 搜索索引状态
        recall = self.recall_status()
        search_index_exists = recall.index_exists

        # 健康问题
        try:
            hr = self.knowledge_health_report()
            health_issue_count = len(hr.issues)
        except Exception:
            health_issue_count = 0

        # 趋势总结（确定性生成，不调 LLM）
        trend_parts = [
            f"总卡片 {total} 张" if total > 0 else "暂无卡片",
        ]
        if total > 0:
            trend_parts.append(f"确认率 {approval_rate:.0%}")
            if draft_count > 0:
                trend_parts.append(f"{draft_count} 张待审")
        if graph_density > 0:
            trend_parts.append(f"图密度 {graph_density:.1f} 关系/卡片")
        trend_summary = " · ".join(trend_parts) + "。"

        # 维护建议
        suggestions: list[str] = []
        if draft_count > 0:
            suggestions.append(f"审阅 {draft_count} 张待确认草稿以提高知识库覆盖率。")
        if not search_index_exists:
            suggestions.append("搜索索引尚未构建，前往搜索页触发索引构建。")
        if wiki_stale:
            suggestions.append("Wiki 可能过期，考虑重新构建以包含最新确认的卡片。")
        if health_issue_count > 0:
            suggestions.append(f"知识健康报告发现 {health_issue_count} 项需关注，请查看详情。")
        if total == 0:
            suggestions.append("知识库为空，导入资料或粘贴 Markdown 内容开始构建知识库。")

        return DogfoodReportResponse(
            generated_at=now,
            total_cards=total,
            approved_count=approved_count,
            draft_count=draft_count,
            approval_rate=round(approval_rate, 4),
            source_count=source_count,
            graph_total_relations=relation_count,
            graph_density=round(graph_density, 4),
            community_count=community_count,
            wiki_section_count=wiki_section_count,
            wiki_stale=wiki_stale,
            search_index_exists=search_index_exists,
            search_index_path=str(recall.index_path) if recall.index_path else "",
            imported_card_count=imported_count,
            exported_count=approved_count,
            import_error_count=error_count,
            health_issue_count=health_issue_count,
            trend_summary=trend_summary,
            maintenance_suggestions=suggestions,
        )

    # ── v2.5 U4 Provider Readiness Center ───────────────────────────

    def provider_readiness_detail(self) -> ProviderReadinessResponse:
        """返回完整 provider 就绪状态，含 invariants — 不读取 API key 值。

        中文学习型说明：合并 build_readiness_report (provider_readiness.py) 与
        model_setup_readiness，给出 provider 系统当前是否可用的完整诊断，
        供 Provider Readiness Center UI 展示。
        """
        from mindforge.provider_readiness import build_readiness_report
        from mindforge.model_setup_readiness import model_setup_readiness

        report = build_readiness_report(self.cfg.llm)
        provider = report["provider"]
        opt_in = report["opt_in"]
        invariants = report["invariants"]

        readiness = model_setup_readiness(self.cfg)

        alias_statuses = []
        for a in provider["aliases"]:
            alias_id = str(a["alias"])
            model = self.cfg.llm.models.get(alias_id)
            env_key_present = bool(a.get("api_key_present"))
            secret_key_present = bool(
                model and self.secrets.api_key_source(
                    alias_id, model.type, model.api_key_env,
                ) in ("local_secret", "env")
            )
            alias_statuses.append(
                ProviderAliasStatus(
                    alias=alias_id,
                    type=str(a["type"]),
                    in_active_profile=bool(a["in_active_profile"]),
                    api_key_env=a.get("api_key_env"),
                    api_key_present=env_key_present or secret_key_present,
                    base_url_env_present=bool(a.get("base_url_env_present")),
                )
            )

        provider_mode = "fake"
        try:
            from mindforge.checkpoint import Checkpoint
            cp = Checkpoint.load(self.cfg.state.state_path)
            mode = cp.provider_mode
            if mode in ("fake", "real"):
                provider_mode = mode
        except Exception:
            pass

        return ProviderReadinessResponse(
            active_profile=provider["active_profile"],
            opt_in_state="ready" if readiness.ready else opt_in["opt_in_state"],
            model_setup=readiness.status,
            model_setup_label=readiness.label,
            can_run_real_smoke=readiness.ready,
            provider_mode=provider_mode,
            aliases=alias_statuses,
            blockers=list(opt_in["blockers"]),
            invariants=invariants,
        )

    # ── v2.5 U2 Source-to-Card Lifecycle ────────────────────────────

    def source_lifecycle(self) -> LifecycleResponse:
        """返回每个 source 的卡片生命周期统计 — 纯本地数据聚合。

        中文学习型说明：扫描所有卡片，按 source_id 分组统计各状态下卡片数，
        展示 Source → ai_draft → human_approved 的完整知识流转。
        """
        from mindforge.cards import iter_cards

        scan = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        cards = list(scan.cards)

        # 按 source_id 分组
        by_source: dict[str, dict] = {}
        for c in cards:
            sid = c.source_id or "__unknown__"
            if sid not in by_source:
                by_source[sid] = {
                    "source_id": sid,
                    "source_title": getattr(c, "source_title", sid),
                    "total_cards": 0,
                    "ai_draft_count": 0,
                    "human_approved_count": 0,
                    "imported_count": 0,
                    "error_count": 0,
                }
            by_source[sid]["total_cards"] += 1
            status = getattr(c, "status", "")
            if status == "ai_draft":
                by_source[sid]["ai_draft_count"] += 1
            elif status == "human_approved":
                by_source[sid]["human_approved_count"] += 1
            elif status == "imported":
                by_source[sid]["imported_count"] += 1
            elif status == "error":
                by_source[sid]["error_count"] += 1

        sources = [
            SourceLifecycleItem(**v)
            for v in sorted(by_source.values(), key=lambda x: x["total_cards"], reverse=True)
        ]

        total = len(cards)
        approved = sum(s.human_approved_count for s in sources)
        drafts = sum(s.ai_draft_count for s in sources)

        return LifecycleResponse(
            sources=sources,
            total_sources=len(sources),
            total_cards=total,
            total_approved=approved,
            total_drafts=drafts,
        )


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
        approved_at=summary.approved_at.isoformat() if summary.approved_at else None,
        updated_at=summary.updated_at.isoformat() if summary.updated_at else None,
        rel_path=summary.rel_path,
        fallback_provider_note=card.fallback_provider_note,
        quality_score=summary.quality_score,
        quality_level=summary.quality_level,
    )



def _library_detail_response(
    cfg: MindForgeConfig,
    detail: LibraryCardDetail,
    path_action_service: WebPathActionService | None = None,
) -> LibraryCardDetailResponse:
    related_context = _library_relationship_context(cfg, detail, path_action_service=path_action_service)
    card = _library_card_response(detail.card)
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
        local_graph=_local_graph_response(related_context.graph),
        related_cards=related_context.related_cards,
    )


class _LibraryRelationshipContext:
    def __init__(
        self,
        *,
        graph: LocalGraph,
        related_cards: list[RelatedCardResponse],
    ) -> None:
        self.graph = graph
        self.related_cards = related_cards


def _library_relationship_context(
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
    records = [_relation_record(card) for card in approved]
    center_id = detail.card.summary.id or detail.card.summary.rel_path
    graph = build_card_centered_graph(center_id, records)
    cards_by_id = {
        card.id or card.rel_path: _library_card_summary_response(card, path_action_service=path_action_service)
        for card in approved
    }
    edges = compute_multi_hop_related_cards(center_id, records, context="library", max_depth=2)
    return _LibraryRelationshipContext(
        graph=graph,
        related_cards=_related_card_responses(edges, cards_by_id),
    )


def _relation_record(card: CardSummary) -> dict[str, object]:
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


def _library_card_summary_response(
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


def _local_graph_response(graph: LocalGraph) -> LocalGraphResponse:
    section_card_counts: dict[str, int] = {}
    for edge in graph.edges:
        if edge.reason == "same_wiki_section":
            section_card_counts[edge.target_id] = section_card_counts.get(edge.target_id, 0) + 1

    return LocalGraphResponse(
        center_id=graph.center_id,
        center_type=graph.center_type.value,
        nodes=[
            LocalGraphNodeResponse(
                id=node.id,
                type=node.type.value,
                label=node.label,
                href=node.href,
                card_count=section_card_counts.get(node.id) if node.type == NodeType.WIKI_SECTION else None,
            )
            for node in graph.nodes
        ],
        edges=[
            LocalGraphEdgeResponse(
                source_id=edge.source_id,
                target_id=edge.target_id,
                reason=edge.reason,
                label=_relation_reason_label(edge.reason),
            )
            for edge in graph.edges
        ],
    )


def _related_card_responses(
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
                label=_relation_reason_label(edge.reason.value),
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


def _relation_reason_label(reason: str) -> str:
    labels = {
        "same_source": "Same source",
        "same_tag": "Same tag",
        "same_wiki_section": "Same wiki section",
        "same_review_batch": "Same review batch",
        "source_location_neighbor": "Source location neighbor",
        "manual_link": "Manual link",
    }
    return labels.get(reason, reason.replace("_", " ").title())


# ── v0.6 Graph helpers ──────────────────────────────


def _build_graph_builder(cfg: MindForgeConfig) -> DeterministicGraphBuilder | None:
    """从 vault 中所有 approved cards 构建 DeterministicGraphBuilder。"""
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = [card for card in scan.cards if card.status == "human_approved"]
    if not approved:
        return None
    records = [_relation_record(card) for card in approved]
    return DeterministicGraphBuilder(records)


def _resolve_card_id(cfg: MindForgeConfig, ref: str) -> str | None:
    """将用户输入的 ref 解析为卡片 id。"""
    detail = show_library_card(cfg, ref, show_content=False)
    if isinstance(detail, LibraryLookupError):
        return None
    return detail.card.summary.id or detail.card.summary.rel_path


def _graph_response(graph: GraphResult) -> GraphResponse:
    """将内部 Graph 转换为 API response。"""
    return GraphResponse(
        center_id=graph.center_id,
        center_type=graph.center_type.value,
        depth=graph.depth,
        nodes=[_graph_node_response(n) for n in graph.nodes],
        edges=[_graph_edge_response(e) for e in graph.edges],
    )


def _graph_node_response(node: GraphNode) -> GraphNodeResponse:
    return GraphNodeResponse(
        id=node.id,
        type=node.type.value,
        label=node.label,
        href=node.href,
        card_count=node.card_count,
    )


def _graph_edge_response(edge: GraphEdge) -> GraphEdgeResponse:
    from mindforge_web.schemas import RelationEvidenceResponse
    return GraphEdgeResponse(
        source_id=edge.source_id,
        target_id=edge.target_id,
        edge_type=edge.edge_type.value,
        evidence=RelationEvidenceResponse(
            reason=edge.evidence.reason,
            evidence=edge.evidence.evidence,
            strength=edge.evidence.strength,
            detail=edge.evidence.detail,
        ),
    )


def _discovery_context_response(ctx: DiscoveryContext) -> DiscoveryContextResponse:
    """将内部 DiscoveryContext 转换为 API response — v2.1 增强。"""
    return DiscoveryContextResponse(
        center_card_id=ctx.center_card_id,
        center_card_title=ctx.center_card_title,
        reasoning=ctx.reasoning,
        estimated_token_count=ctx.estimated_token_count,
        direct_matches=[
            DiscoveryCardRefResponse(
                card_id=ref.card_id,
                title=ref.title,
                relation_reason=ref.relation_reason,
                relation_strength=ref.relation_strength,
                evidence=ref.evidence,
            )
            for ref in ctx.direct_matches
        ],
        neighbor_cards=[
            DiscoveryCardRefResponse(
                card_id=ref.card_id,
                title=ref.title,
                relation_reason=ref.relation_reason,
                relation_strength=ref.relation_strength,
                evidence=ref.evidence,
            )
            for ref in ctx.neighbor_cards
        ],
        wiki_sections=[
            DiscoverySectionRefResponse(
                section_title=s.section_title,
                card_count=s.card_count,
            )
            for s in ctx.wiki_sections
        ],
        shared_tags=[
            DiscoveryTagRefResponse(tag=t.tag, card_count=t.card_count)
            for t in ctx.shared_tags
        ],
        shared_sources=[
            DiscoverySourceRefResponse(source_id=s.source_id, card_count=s.card_count)
            for s in ctx.shared_sources
        ],
        communities=[
            DiscoveryCommunityRefResponse(
                community_type=c.community_type,
                shared_entity=c.shared_entity,
                member_count=c.member_count,
                description=c.description,
            )
            for c in ctx.communities
        ],
    )


def _center_card_communities(
    center_card_id: str,
    cards: list[dict[str, object]],
) -> tuple[DiscoveryCommunityRef, ...]:
    """检测中心卡片所属的知识社区（v1.2 U4）。

    对所有卡片运行 detect_communities，筛选出包含 center_card_id 的社区，
    返回 DiscoveryCommunityRef 元组。
    """
    from mindforge.relations.community import detect_communities

    all_communities = detect_communities(cards, min_members=2)
    result: list[DiscoveryCommunityRef] = []
    for c in all_communities:
        if center_card_id in c.member_card_ids:
            result.append(DiscoveryCommunityRef(
                community_type=c.community_type,
                shared_entity=c.shared_entity,
                member_count=c.member_count,
                description=c.description,
            ))
    return tuple(result)


def _compute_related_sources(
    source_id: str | None,
    approved: list,
) -> list[ProvenanceTrailRelatedSource]:
    """找出与给定 source 通过共享 tags/wiki_sections 关联的其他 source（v1.2 U5）。

    双向探索的关键：从当前 card → source → 找到"哪些其他 source 有相似的知识"。
    """
    if not source_id:
        return []

    # 收集当前 source 的所有 tags 和 wiki_sections
    source_tags: set[str] = set()
    source_sections: set[str] = set()
    for c in approved:
        if c.source_id == source_id:
            for t in c.tags:
                source_tags.add(t)
            for s in c.wiki_sections:
                source_sections.add(s)

    if not source_tags and not source_sections:
        return []

    # 统计其他 source 与当前 source 的共享情况
    related: dict[str, dict] = {}  # source_id → {tags: set, sections: set, cards: set}
    for c in approved:
        sid = c.source_id
        if not sid or sid == source_id:
            continue
        if sid not in related:
            related[sid] = {"tags": set(), "sections": set(), "cards": set(), "title": c.source_title}
        related[sid]["cards"].add(c.id or c.rel_path)
        for t in c.tags:
            if t in source_tags:
                related[sid]["tags"].add(t)
        for s in c.wiki_sections:
            if s in source_sections:
                related[sid]["sections"].add(s)

    # 排序：共享 tag + section 总数降序
    scored = [
        (sid, info) for sid, info in related.items()
        if info["tags"] or info["sections"]
    ]
    scored.sort(key=lambda x: len(x[1]["tags"]) + len(x[1]["sections"]), reverse=True)

    result: list[ProvenanceTrailRelatedSource] = []
    for sid, info in scored[:5]:
        result.append(ProvenanceTrailRelatedSource(
            source_id=sid,
            source_title=info["title"],
            card_count=len(info["cards"]),
            shared_tags=sorted(info["tags"]),
            shared_wiki_sections=sorted(info["sections"]),
        ))

    return result


def _graph_neighbor_count(
    builder: DeterministicGraphBuilder | None,
    card_id: str,
) -> int | None:
    """获取卡片 1-hop 邻居数量（轻量，不做 full 2-hop build）。"""
    if builder is None:
        return None
    try:
        edges = builder.get_edges(card_id, direction="outgoing")
        neighbor_ids = {e.target_id for e in edges}
        return len(neighbor_ids)
    except Exception:
        return None


def _provenance_trail_response(
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
    related_sources = _compute_related_sources(source_id, approved)

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
