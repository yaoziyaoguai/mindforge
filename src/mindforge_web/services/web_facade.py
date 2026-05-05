"""MindForge Web facade.

中文学习型说明：Facade 是 Web 场景编排层。它知道 Home/Setup/Sources/Drafts
这些页面需要哪些数据，但不拥有 approval/recall/provider/source 的核心规则。
Router 调 Facade，Facade 调现有 MindForge service，这样 Web 不会长成新的
业务巨石。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.app_context import build_app_context
from mindforge.cards import iter_cards
from mindforge.checkpoint import Checkpoint, CheckpointError
from mindforge.lexical_index import default_index_path
from mindforge.recall_service import RecallQuery, RecallServiceError, run_bm25_recall

from mindforge_web.schemas import (
    ConfigStatusResponse,
    DraftDetailResponse,
    DraftsResponse,
    HealthResponse,
    HomeStatusResponse,
    NextAction,
    RecallHit,
    RecallResponse,
    RecallStatus,
    SafetySummary,
    SourcesResponse,
    StatusItem,
    VaultStatus,
    WorkspaceStatus,
)
from mindforge_web.services.web_config_service import WebConfigService
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
        self.context = build_app_context(config_path, vault_override=vault_override)
        self.cfg = self.context.config
        self.config_path = config_path
        self.host = host
        self.config_service = WebConfigService(self.cfg)
        self.source_service = WebSourceService(self.cfg)
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
        env_keys = self.config_service.env_key_statuses()
        recall = self.recall_status(approved_count=status_counts.get("human_approved", 0))
        return HomeStatusResponse(
            safety=safety,
            workspace=workspace,
            vault=vault,
            provider=provider,
            env_keys=env_keys,
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
                label="LLM provider",
                status="ok" if provider.opt_in_state == "fake_default" else "warn",
                value=provider.opt_in_state,
                detail="Provider readiness 只检查 key presence，不调用真实 LLM。",
            ),
            StatusItem(
                key="env",
                label=".env keys",
                status="ok" if not missing else "warn",
                value=f"{len(configured)} configured / {len(missing)} missing",
                detail="只显示 key name 与 presence，不显示 value。",
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
                label="Scan sources",
                description="扫描 configured inbox，把 source 状态写入 state.json。",
                command=f"mindforge scan --vault {self.cfg.vault.root}",
            )
        ]
        return SourcesResponse(
            sources=sources,
            available_imports=self.source_service.available_imports(),
            next_actions=next_actions,
        )

    def drafts(self) -> DraftsResponse:
        drafts, errors = self.review_service.list_drafts()
        empty = None
        if not drafts:
            empty = NextAction(
                label="Create drafts",
                description="没有 ai_draft。先 scan/process，或检查 Sources 页的 inbox 状态。",
                command=f"mindforge process --profile fake --limit 1 --vault {self.cfg.vault.root}",
            )
        return DraftsResponse(drafts=drafts, scan_errors=errors, empty_state=empty)

    def draft_detail(self, draft_id: str) -> DraftDetailResponse | None:
        return self.review_service.draft_detail(draft_id)

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
        env_keys = self.config_service.env_key_statuses()
        vault_real = self._is_real_environment()
        warnings: list[str] = []
        if vault_real:
            warnings.append("Real-looking vault is active; writes require explicit user action.")
        if provider.opt_in_state not in {"fake_default", "env_only"}:
            warnings.append("Real provider profile may be active; no hidden provider calls are made.")
        return SafetySummary(
            local_only=self.host in {"127.0.0.1", "localhost"},
            host=self.host,
            vault_path=str(self.cfg.vault.root),
            vault_status="warn" if vault_real else "ok",
            provider_state=provider.opt_in_state,
            env_status="ok" if any(item.configured for item in env_keys) else "info",
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
                    label="Approve first card",
                    description="Recall 需要 human_approved cards；先完成一张 draft review。",
                    href="/drafts",
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
