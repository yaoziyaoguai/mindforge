"""Web source/workspace status service.

中文学习型说明：Sources 页现在对齐 CLI 的用户级 ingestion 心智：
watch/import 是主入口；scan/process 只作为 advanced/troubleshooting。Web 不
复制 pipeline，而是调用 ``ingestion_service`` 与 ``watch_registry`` 这些
已经被 CLI 使用的 service 边界。
"""

from __future__ import annotations

from pathlib import Path

from mindforge.cards import iter_cards
from mindforge.config import MindForgeConfig
from mindforge.config import ConfigError
from mindforge.config import REQUIRED_STAGES
from mindforge.ingestion_service import (
    SourcePathError,
    import_sources,
    watch_scan_sources,
    watch_sources_for_display,
)
from mindforge.scanner import Scanner
from mindforge.source_discovery import discover_source_results, enumerate_supported_source_files
from mindforge.watch_registry import (
    add_watch_source,
    delete_watch_source,
    find_watch_source,
    is_due,
    next_scan_after,
    registry_path_for_vault,
    update_watch_source,
)

from mindforge_web.schemas import (
    IngestionActionResponse,
    IngestionSummaryStatus,
    NextAction,
    SourceStatus,
    StatusItem,
    WatchedSourceResponse,
    WatchSourcesResponse,
)
from mindforge_web.services.processing_run_service import (
    latest_run_for_source,
    next_actions_for_record,
    processing_run_response,
    start_processing_run,
)


class WebSourceService:
    def __init__(self, cfg: MindForgeConfig) -> None:
        self.cfg = cfg

    def list_sources(self) -> list[SourceStatus]:
        results: list[SourceStatus] = []
        scan_errors = self._scan_error_counts()
        generated_cards = self._generated_cards_by_source_subdir()
        for entry in self.cfg.sources.active_entries():
            path = self.cfg.vault.inbox_path / entry.inbox_subdir
            files = self._safe_files(path, entry.file_glob) if path.exists() else []
            processed_dir = self.cfg.vault.inbox_path / "_processed" / entry.inbox_subdir
            processed_files = (
                self._safe_files(processed_dir, entry.file_glob) if processed_dir.exists() else []
            )
            card_paths = generated_cards.get(entry.inbox_subdir, [])
            results.append(
                SourceStatus(
                    source_type=entry.source_type,
                    adapter=entry.adapter,
                    inbox_subdir=entry.inbox_subdir,
                    file_glob=entry.file_glob,
                    enabled=entry.enabled,
                    path=str(path),
                    exists=path.exists(),
                    file_count=len(files),
                    error_count=scan_errors.get(entry.source_type, 0),
                    processed_count=len(processed_files),
                    pending_files=[_rel_to_vault(self.cfg, file) for file in files],
                    processed_files=[_rel_to_vault(self.cfg, file) for file in processed_files],
                    display_status=_display_status(
                        exists=path.exists(),
                        pending_count=len(files),
                        processed_count=len(processed_files),
                        error_count=scan_errors.get(entry.source_type, 0),
                    ),
                    generated_knowledge_status=(
                        "Has generated knowledge" if card_paths else "No generated knowledge"
                    ),
                    generated_card_count=len(card_paths),
                    generated_card_paths=[_rel_to_vault(self.cfg, file) for file in card_paths],
                    next_action=None
                    if path.exists()
                    else NextAction(
                        label="Create source folder",
                        description="创建该 inbox 子目录后再放入本地 source 文件。",
                        command=f"mkdir -p {path}",
                    ),
                )
            )
        return results

    def watch_sources(self) -> WatchSourcesResponse:
        registry_path = registry_path_for_vault(self.cfg.vault.root)
        generated_cards = tuple(iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir).cards)
        return WatchSourcesResponse(
            vault_root=str(self.cfg.vault.root),
            registry_path=str(registry_path),
            watched_sources=[
                self._watch_response(source, generated_cards)
                for source in watch_sources_for_display(self.cfg)
            ],
            next_actions=[
                NextAction(
                    label="Add watched source",
                    description=(
                        "注册 file/folder 并在后台处理当前内容；folder 默认递归扫描，只会生成 ai_draft。"
                    ),
                )
            ],
        )

    def watch_add(
        self,
        path: Path,
        *,
        frequency: str | None = None,
        recursive: bool | None = None,
        process_now: bool = True,
    ) -> IngestionActionResponse:
        # 中文学习型说明：Web Add Source 统一在这里校验路径，不管 process_now 是 true 还是 false。
        # 相对路径、不存在路径都必须在 Web 边界被拒绝，不能进入 registry 或 pipeline。
        # 这样避免了之前"不存在路径 silent ok:true"的问题。

        # 1. 拒绝相对路径 —— 浏览器环境下无法可靠解析
        if not path.is_absolute():
            raise SourcePathError(
                f"Please use an absolute path, such as /Users/you/Documents/note.md. "
                f"Received relative path: {path}"
            )

        # 2. 拒绝不存在路径 —— 不允许注册或处理不存在的 source
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise SourcePathError(
                f"File or folder not found: {resolved}. "
                f"Please choose or paste an existing path."
            )

        # 3. 路径合法，继续正常流程
        if not process_now:
            registry_path = registry_path_for_vault(self.cfg.vault.root)
            registry_result = add_watch_source(
                self.cfg.vault.root,
                registry_path,
                resolved,
                frequency=frequency or "manual",
                recursive=recursive,
            )
            return IngestionActionResponse(
                ok=True,
                mode="watch_add",
                target=str(registry_result.source.path),
                counts={"processed": 0, "skipped": 0, "failed": 0, "seen": 0},
                message=(
                    "watch source registered; process now when ready"
                    if registry_result.added
                    else "watch source already registered; no processing run started"
                ),
                added_to_registry=registry_result.added,
                registry_path=str(registry_path),
                watch_id=registry_result.source.id,
                next_actions=_ingestion_next_actions({"processed": 0}),
            )
        _ensure_processing_model_configured(self.cfg)
        registry_path = registry_path_for_vault(self.cfg.vault.root)
        from mindforge.strategy_selection import resolve_strategy_selection

        selected_strategy = resolve_strategy_selection(self.cfg)
        registry_result = add_watch_source(
            self.cfg.vault.root,
            registry_path,
            resolved,
            strategy_id=selected_strategy.strategy_id,
            frequency=frequency or "manual",
            recursive=recursive,
        )
        run = start_processing_run(
            self.cfg,
            source_ref=registry_result.source.id,
            source_path=str(registry_result.source.path),
            mode="watch_add",
            work=lambda: watch_scan_sources(
                self.cfg,
                ref=registry_result.source.id,
                all_sources=True,
            ),
        )
        return IngestionActionResponse(
            ok=True,
            mode="watch_add",
            target=str(registry_result.source.path),
            counts={"processed": 0, "skipped": 0, "failed": 0, "seen": 0},
            message=run.message,
            added_to_registry=registry_result.added,
            registry_path=str(registry_path),
            watch_id=registry_result.source.id,
            next_actions=next_actions_for_record(run),
            run_id=run.run_id,
            processing_status=run.status,
        )

    def watch_scan(self, ref: str | None = None, *, all_sources: bool = False) -> IngestionActionResponse:
        _ensure_processing_model_configured(self.cfg)
        source_ref = ref or ("all" if all_sources else "due")
        source_path = None
        if ref:
            source = find_watch_source(self.cfg.vault.root, registry_path_for_vault(self.cfg.vault.root), ref)
            if source is not None:
                source_path = str(source.path)
        run = start_processing_run(
            self.cfg,
            source_ref=source_ref,
            source_path=source_path,
            mode="watch_scan",
            work=lambda: watch_scan_sources(self.cfg, ref=ref, all_sources=all_sources),
        )
        return IngestionActionResponse(
            ok=True,
            mode="watch_scan",
            target=ref or ("all watched sources" if all_sources else "due watched sources"),
            counts={
                "processed": 0,
                "skipped": 0,
                "failed": 0,
                "seen": 0,
                "scanned": 0,
                "not_due": 0,
                "missing": 0,
            },
            message=run.message,
            added_to_registry=False,
            next_actions=next_actions_for_record(run),
            run_id=run.run_id,
            processing_status=run.status,
        )

    def watch_delete(self, ref: str) -> IngestionActionResponse:
        registry_path = registry_path_for_vault(self.cfg.vault.root)
        result = delete_watch_source(self.cfg.vault.root, registry_path, ref)
        return IngestionActionResponse(
            ok=result.deleted,
            mode="watch_delete",
            target=str(result.source.path) if result.source is not None else ref,
            counts={"processed": 0, "skipped": 0, "failed": 0, "seen": 0},
            message=result.message,
            added_to_registry=False,
            registry_path=str(registry_path),
            watch_id=result.source.id if result.source is not None else None,
            source_deleted=False,
            cards_deleted=False,
            next_actions=[
                NextAction(
                    label="Watch list",
                    description="确认 default 00-Inbox 和剩余 user-added watches。",
                    href="/sources",
                )
            ],
        )

    def watch_frequency(self, ref: str, frequency: str) -> IngestionActionResponse:
        registry_path = registry_path_for_vault(self.cfg.vault.root)
        source = find_watch_source(self.cfg.vault.root, registry_path, ref)
        if source is None:
            return IngestionActionResponse(
                ok=False,
                mode="watch_frequency",
                target=ref,
                counts={"processed": 0, "skipped": 0, "failed": 0, "seen": 0},
                message="watched source not found",
                added_to_registry=False,
                registry_path=str(registry_path),
            )
        updated = update_watch_source(
            self.cfg.vault.root,
            registry_path,
            source.id,
            frequency=frequency,
            next_scan_at=next_scan_after(source.last_scan_at, frequency),
        )
        assert updated is not None
        return IngestionActionResponse(
            ok=True,
            mode="watch_frequency",
            target=str(updated.path),
            counts={"processed": 0, "skipped": 0, "failed": 0, "seen": 0},
            message="watch frequency updated for the top-level source only",
            added_to_registry=False,
            registry_path=str(registry_path),
            watch_id=updated.id,
            next_actions=_ingestion_next_actions({"processed": 0}),
        )

    def import_source(self, path: Path) -> IngestionActionResponse:
        # 中文学习型说明：Web import_source 必须和 watch_add 一样在 Web 边界校验路径。
        # 相对路径、不存在路径都必须在进入 ingestion pipeline 之前被拒绝，返回 400。
        if not path.is_absolute():
            raise SourcePathError(
                f"Please use an absolute path, such as /Users/you/Documents/note.md. "
                f"Received relative path: {path}"
            )
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise SourcePathError(
                f"File or folder not found: {resolved}. "
                f"Please choose or paste an existing path."
            )
        summary = import_sources(self.cfg, resolved)
        return IngestionActionResponse(
            ok=True,
            mode=summary.mode,
            target=str(summary.target),
            counts=summary.counts,
            message="source imported once as ai_draft; not added to watched sources",
            added_to_registry=False,
            next_actions=_ingestion_next_actions({"processed": 0}),
        )

    def ingestion_status(self) -> IngestionSummaryStatus:
        return IngestionSummaryStatus(
            primary_entry="watch/import",
            safety_note=(
                "Automation only creates ai_draft. human_approved requires explicit approve."
            ),
            advanced_note=(
                "scan/process remain available only for Advanced / Troubleshooting, "
                "not as the Web primary ingestion flow."
            ),
        )

    def bucket_counts(self) -> dict[str, dict[str, int]]:
        pending: dict[str, int] = {}
        processed: dict[str, int] = {}
        for entry in self.cfg.sources.active_entries():
            pending_dir = self.cfg.vault.inbox_path / entry.inbox_subdir
            processed_dir = self.cfg.vault.inbox_path / "_processed" / entry.inbox_subdir
            pending[entry.inbox_subdir] = (
                len(self._safe_files(pending_dir, entry.file_glob)) if pending_dir.exists() else 0
            )
            processed[entry.inbox_subdir] = (
                len(self._safe_files(processed_dir, entry.file_glob))
                if processed_dir.exists()
                else 0
            )
        return {"pending": pending, "processed": processed}

    def available_imports(self) -> list[StatusItem]:
        return [
            StatusItem(
                key="watch_add",
                label="Watch file or folder",
                status="ok",
                value="available",
                detail=(
                    "注册 watched source，并启动后台 processing；folder 默认递归扫描。"
                    "ai_draft 只会在后台处理成功后出现，且不会自动 approve。"
                ),
                next_action=NextAction(
                    label="Add watch",
                    description="支持 file/folder；后续 daemon/hook 不在本阶段。",
                ),
            ),
            StatusItem(
                key="import_local",
                label="Import file or folder",
                status="ok",
                value="available",
                detail=(
                    "一次性登记当前内容并启动后台 processing；folder 使用同一套递归扫描策略，"
                    "ai_draft 只会在处理成功后出现，不会加入 watched sources。"
                ),
                next_action=NextAction(
                    label="Import once",
                    description="适合一次性导入外部 file/folder。",
                ),
            ),
        ]

    def _watch_response(self, source, generated_cards) -> WatchedSourceResponse:
        scan = enumerate_supported_source_files(self.cfg, source.path) if source.path.exists() else None
        supported_count = len(scan.candidates) if scan is not None else 0
        skipped_summary = dict(scan.skipped_reason_summary) if scan is not None else {}
        failed_count = 0
        processed_hashes = {
            card.source_content_hash: card
            for card in generated_cards
            if card.source_content_hash
        }
        if source.path.exists():
            for result in discover_source_results(self.cfg, source.path):
                if not result.ok:
                    failed_count += 1
                    skipped_summary["parse_failed"] = skipped_summary.get("parse_failed", 0) + 1
                    continue
                doc = result.document
                if doc is None:
                    continue
                matched_card = processed_hashes.get(doc.content_hash)
                if matched_card is not None:
                    reason = (
                        "already_processed"
                        if _same_source_path(self.cfg, matched_card.source_path, doc.source_path)
                        else "duplicate_content_hash"
                    )
                    skipped_summary[reason] = skipped_summary.get(reason, 0) + 1
        card_paths = [
            card.path
            for card in generated_cards
            if _card_matches_watch_source(self.cfg, source.path, card.source_path)
        ]
        generated_status = "Has generated knowledge" if card_paths else "No generated knowledge"
        latest_run = latest_run_for_source(
            self.cfg,
            source_ref=source.id,
            source_path=str(source.path),
        )
        run_response = processing_run_response(latest_run) if latest_run is not None else None
        active_run_id = (
            run_response.run_id if run_response is not None and run_response.status in {"queued", "running"} else None
        )
        status_label = _watch_status_label(
            raw_status=source.status,
            failed_count=failed_count,
            generated_card_count=len(card_paths),
            supported_count=supported_count,
            processing_status=run_response.status if run_response is not None else None,
        )
        last_error = (
            run_response.error_message
            if run_response is not None and run_response.status in {"failed", "partial_failed"}
            else source.error
        )
        return WatchedSourceResponse(
            id=source.id,
            path=str(source.path),
            path_type=source.path_type,
            is_default=source.is_default,
            kind="default" if source.is_default else "user-added",
            status=source.status,
            added_at=source.added_at,
            last_seen_at=source.last_seen_at,
            last_processed_at=source.last_processed_at,
            last_scan_at=source.last_scan_at,
            next_scan_at=source.next_scan_at,
            frequency=source.frequency,
            due_status=_due_status(source),
            fingerprint=source.fingerprint,
            can_delete=True,
            error=source.error,
            recursive=source.path_type == "folder",
            supported_file_count=supported_count,
            processed_count=len(card_paths),
            skipped_count=sum(skipped_summary.values()),
            failed_count=failed_count,
            skipped_reason_summary=skipped_summary,
            diff_counts=dict(source.diff_counts),
            generated_knowledge_status=generated_status,
            generated_card_count=len(card_paths),
            generated_card_paths=[_rel_to_vault(self.cfg, file) for file in card_paths],
            status_label=status_label,
            active_run_id=active_run_id,
            last_run_id=run_response.run_id if run_response is not None else None,
            last_run_started_at=run_response.started_at if run_response is not None else None,
            last_run_finished_at=run_response.finished_at if run_response is not None else None,
            processing_status=run_response.status if run_response is not None else None,
            last_run_summary=run_response.summary if run_response is not None else None,
            last_message=run_response.message if run_response is not None else None,
            last_error=last_error,
            generated_draft_count=len(card_paths),
        )

    def _generated_cards_by_source_subdir(self) -> dict[str, list[Path]]:
        by_subdir: dict[str, list[Path]] = {}
        cards = iter_cards(self.cfg.vault.root, self.cfg.vault.cards_dir)
        for card in cards.cards:
            if not card.source_path:
                continue
            source_path = card.source_path.replace("\\", "/")
            for entry in self.cfg.sources.active_entries():
                markers = (
                    f"{self.cfg.vault.inbox_root}/{entry.inbox_subdir}/",
                    f"{self.cfg.vault.inbox_root}/_processed/{entry.inbox_subdir}/",
                )
                if any(marker in source_path for marker in markers):
                    by_subdir.setdefault(entry.inbox_subdir, []).append(card.path)
                    break
        return by_subdir

    def _scan_error_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        scanner = Scanner(self.cfg)
        for result in scanner.iter_results():
            if not result.ok:
                counts[result.source_type] = counts.get(result.source_type, 0) + 1
        return counts

    @staticmethod
    def _safe_files(path: Path, file_glob: str) -> list[Path]:
        return sorted(file for file in path.rglob(file_glob) if file.is_file())


def _rel_to_vault(cfg: MindForgeConfig, path: Path) -> str:
    try:
        return path.resolve().relative_to(cfg.vault.root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _display_status(
    *,
    exists: bool,
    pending_count: int,
    processed_count: int,
    error_count: int,
) -> str:
    if error_count:
        return "Failed"
    if not exists:
        return "Missing folder"
    if processed_count:
        return "Processed"
    if pending_count:
        return "Pending"
    return "Imported"


def _card_matches_watch_source(cfg: MindForgeConfig, watched_path: Path, source_path: str | None) -> bool:
    if not source_path:
        return False
    candidate = Path(source_path).expanduser()
    if not candidate.is_absolute():
        candidate = cfg.vault.root / candidate
    try:
        resolved_candidate = candidate.resolve()
        resolved_watch = watched_path.resolve()
    except OSError:
        return False
    if resolved_watch.is_file():
        return resolved_candidate == resolved_watch
    if resolved_watch.is_dir():
        return resolved_candidate == resolved_watch or resolved_candidate.is_relative_to(resolved_watch)
    return False


def _same_source_path(cfg: MindForgeConfig, left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return _resolve_source_path(cfg, left) == _resolve_source_path(cfg, right)


def _resolve_source_path(cfg: MindForgeConfig, value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = cfg.vault.root / path
    return path.resolve()


def _watch_status_label(
    *,
    raw_status: str,
    failed_count: int,
    generated_card_count: int,
    supported_count: int,
    processing_status: str | None = None,
) -> str:
    if processing_status in {"queued", "running"}:
        return "Processing"
    if processing_status in {"skipped", "failed", "partial_failed", "succeeded"}:
        return processing_status.replace("_", " ").title()
    if raw_status == "missing":
        return "Missing"
    if raw_status == "error" or failed_count:
        return "Failed"
    if generated_card_count:
        return "Processed"
    if supported_count:
        return "Watching"
    return "Manual"


def _due_status(source) -> str:
    if source.frequency == "manual":
        return "Manual"
    return "Due" if is_due(source) else "Not due"


def _ensure_processing_model_configured(cfg: MindForgeConfig) -> None:
    try:
        for stage in REQUIRED_STAGES:
            cfg.llm.resolve_stage_alias(stage)
    except ConfigError as exc:
        raise SourcePathError(str(exc)) from exc


def _ingestion_next_actions(counts: dict[str, int] | None = None) -> list[NextAction]:
    counts = counts or {}
    actions = [
        NextAction(
            label="View source status",
            description="查看 source processing 状态、skipped reason 或错误。",
            href="/sources",
        )
    ]
    if counts.get("processed", 0) > 0:
        actions.insert(
            0,
            NextAction(
                label="Review drafts",
                description="新生成内容仍是 ai_draft；human_approved 必须显式 approve。",
                href="/drafts",
            ),
        )
    return actions
