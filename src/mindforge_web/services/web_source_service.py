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
from mindforge.ingestion_service import import_sources, watch_add_source, watch_sources_for_display
from mindforge.scanner import Scanner
from mindforge.watch_registry import delete_watch_source, registry_path_for_vault

from mindforge_web.schemas import (
    IngestionActionResponse,
    IngestionSummaryStatus,
    NextAction,
    SourceStatus,
    StatusItem,
    WatchedSourceResponse,
    WatchSourcesResponse,
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
        return WatchSourcesResponse(
            vault_root=str(self.cfg.vault.root),
            registry_path=str(registry_path),
            watched_sources=[_watch_response(source) for source in watch_sources_for_display(self.cfg)],
            next_actions=[
                NextAction(
                    label="Add watched source",
                    description="注册 file/folder 并立即处理当前内容；只会生成 ai_draft。",
                ),
                NextAction(
                    label="Review drafts",
                    description="自动化不会 approve；human_approved 必须显式确认。",
                    href="/drafts",
                ),
            ],
        )

    def watch_add(self, path: Path) -> IngestionActionResponse:
        summary = watch_add_source(self.cfg, path)
        registry_result = summary.registry_result
        assert registry_result is not None
        return IngestionActionResponse(
            ok=True,
            mode=summary.mode,
            target=str(summary.target),
            counts=summary.counts,
            message=(
                "watch source registered and current content processed as ai_draft"
                if registry_result.added
                else "watch source already registered; current content checked"
            ),
            added_to_registry=registry_result.added,
            registry_path=str(summary.registry_path) if summary.registry_path else None,
            watch_id=registry_result.source.id,
            next_actions=_ingestion_next_actions(),
        )

    def watch_delete(self, ref: str) -> IngestionActionResponse:
        registry_path = registry_path_for_vault(self.cfg.vault.root)
        result = delete_watch_source(self.cfg.vault.root, registry_path, ref)
        return IngestionActionResponse(
            ok=result.deleted,
            mode="watch_delete",
            target=str(result.source.path) if result.source is not None else ref,
            counts={"processed": 0, "skipped": 0, "failed": 0, "seen": 0},
            message=(
                "watch source registry record removed; source and cards were not deleted"
                if result.deleted
                else result.message
            ),
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

    def import_source(self, path: Path) -> IngestionActionResponse:
        summary = import_sources(self.cfg, path)
        return IngestionActionResponse(
            ok=True,
            mode=summary.mode,
            target=str(summary.target),
            counts=summary.counts,
            message="source imported once as ai_draft; not added to watched sources",
            added_to_registry=False,
            next_actions=_ingestion_next_actions(),
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
                detail="注册 watched source，并立即处理当前内容生成 ai_draft；不会自动 approve。",
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
                detail="一次性处理当前内容生成 ai_draft；不会加入 watched sources。",
                next_action=NextAction(
                    label="Import once",
                    description="适合一次性导入外部 file/folder。",
                ),
            ),
        ]

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


def _watch_response(source) -> WatchedSourceResponse:
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
        fingerprint=source.fingerprint,
        can_delete=not source.is_default,
        error=source.error,
    )


def _ingestion_next_actions() -> list[NextAction]:
    return [
        NextAction(
            label="Review drafts",
            description="新生成内容仍是 ai_draft；human_approved 必须显式 approve。",
            href="/drafts",
        ),
        NextAction(
            label="Open library",
            description="查看 cards metadata 和 source provenance。",
            href="/library",
        ),
    ]
