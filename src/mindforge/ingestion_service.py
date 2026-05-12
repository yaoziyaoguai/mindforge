"""Simple watch/import ingestion workflow.

中文学习型说明：本 service 是用户级 ingestion 入口的业务层。CLI 只负责参数和
展示；这里负责 registry、source discovery、dedupe、checkpoint、writer 与
pipeline 的组合。它不 approve、不删除 source、不复制外部 source 到 Inbox。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import MindForgeConfig
from .ingestion_diagnostics import (
    ProviderFailureDetail,
    SkippedDocumentDetail,
    friendly_missing_key_error,
    provider_failure_detail,
)
from .llm.base import ProviderError
from .process_executor import (
    build_approved_source_index,
    build_process_runtime_parts,
    emit_source_error,
    finalize_process_run,
    process_one_result,
)
from .process_service import (
    ProcessError,
    ProcessRequest,
    resolve_process_runtime,
)
from .run_logger import RunLogger
from .source_discovery import SourceScanPolicy, discover_source_results, enumerate_supported_source_files
from .source_mux import SourceMux
from .sources.base import SourceDocument
from .strategy_selection import (
    StrategySelection,
    StrategySelectionError,
    resolve_strategy_selection,
    strategy_error_from_build_error,
)
from .strategies import NotYetImplementedStrategyError, UnknownStrategyError
from .watch_registry import (
    AddWatchResult,
    WatchedSource,
    WatchFileSnapshot,
    add_watch_source,
    find_watch_source,
    is_due,
    list_watch_sources,
    next_scan_after,
    registry_path_for_vault,
    update_watch_source,
)


class SourcePathError(ValueError):
    """用户级 source path 错误 —— 文件不存在/不可读等。

    Web 层可安全转为 HTTP 400；CLI 输出友好消息不打印 traceback。
    与内部 RuntimeError（bug/strategy error）严格区分。
    """


@dataclass(frozen=True)
class IngestionSummary:
    mode: str
    target: Path
    counts: dict[str, int]
    skipped: tuple[SkippedDocumentDetail, ...] = ()
    errors: tuple[str, ...] = ()
    provider_failure: ProviderFailureDetail | None = None
    registry_result: AddWatchResult | None = None
    registry_path: Path | None = None
    strategy: StrategySelection | None = None
    diff_counts: dict[str, int] | None = None


@dataclass(frozen=True)
class WatchScanSourceDetail:
    """单个 watched source 的 scan 结果，供 CLI 创建 background processing run。

    中文学习型说明：CLI watch scan 命令需要知道每个 source 是否有新增/变更文件，
    才能为有变更的 source 创建 background processing run。这个 dataclass 是
    watch_scan_sources() 的 per-source 输出，不包含 processing 结果。
    """

    source_id: str
    path: Path
    has_changes: bool
    diff_counts: dict[str, int]


@dataclass(frozen=True)
class WatchScanSummary:
    scanned: int
    not_due: int
    missing: int
    counts: dict[str, int]
    diff_counts: dict[str, int]
    source_ids: tuple[str, ...]
    source_details: tuple[WatchScanSourceDetail, ...] = ()
    skipped: tuple[SkippedDocumentDetail, ...] = ()
    errors: tuple[str, ...] = ()
    provider_failure: ProviderFailureDetail | None = None


def import_sources(
    cfg: MindForgeConfig,
    target: Path,
    *,
    bypass_triage_gate: bool = False,
    strategy: StrategySelection | None = None,
) -> IngestionSummary:
    """一次性导入当前内容，不写 watched source registry。"""

    selected_strategy = strategy or resolve_strategy_selection(cfg)
    summary = _ingest_targets_summary(
        cfg,
        target,
        command="import",
        bypass_triage_gate=bypass_triage_gate,
        strategy=selected_strategy,
    )
    return IngestionSummary(
        mode="import",
        target=target,
        counts=summary.counts,
        skipped=summary.skipped,
        provider_failure=summary.provider_failure,
        strategy=selected_strategy,
    )


def watch_add_source(
    cfg: MindForgeConfig,
    target: Path,
    *,
    strategy: StrategySelection | None = None,
    frequency: str = "manual",
    recursive: bool | None = None,
) -> IngestionSummary:
    """注册 watched source，并同步处理当前内容的底层服务。

    中文学习型说明：CLI/Web 用户主路径不直接调用这个函数作为产品体验，
    而是先创建 durable processing run，再由后台 worker 复用这段同步逻辑。
    这样 source registration 与 processing lifecycle 可以分开表达。
    """

    if not target.exists():
        raise SourcePathError(f"File or folder not found: {target}. Please verify the path exists.")
    selected_strategy = strategy or resolve_strategy_selection(cfg)
    registry_path = registry_path_for_vault(cfg.vault.root)
    registry_result = add_watch_source(
        cfg.vault.root,
        registry_path,
        target,
        strategy_id=selected_strategy.strategy_id,
        frequency=frequency,
        recursive=recursive,
    )
    effective_strategy = resolve_strategy_selection(
        cfg,
        watched_strategy=registry_result.source.strategy_id,
    )
    baseline, diff_counts = _build_source_baseline(cfg, registry_result.source)
    changed_targets = _changed_targets_from_baseline(baseline, diff_counts)
    ingest_target = (
        registry_result.source.path
        if registry_result.source.path_type == "file" or not changed_targets
        else changed_targets
    )
    summary = _ingest_targets_summary(
        cfg,
        ingest_target,
        command="watch_add",
        bypass_triage_gate=False,
        strategy=effective_strategy,
    )
    counts = summary.counts
    processed = counts.get("processed", 0)
    skipped = counts.get("skipped", 0)
    failed = counts.get("failed", 0)
    update_watch_source(
        cfg.vault.root,
        registry_path,
        registry_result.source.id,
        last_seen_at=_now(),
        last_processed_at=_now() if processed or skipped else None,
        last_scan_at=_now(),
        next_scan_at=next_scan_after(_now(), registry_result.source.frequency),
        baseline=baseline,
        diff_counts=diff_counts,
        status="error" if failed else ("active" if registry_result.source.path.exists() else "missing"),
        error=None if not failed else "one or more sources failed",
    )
    return IngestionSummary(
        mode="watch_add",
        target=registry_result.source.path,
        counts=counts,
        skipped=summary.skipped,
        provider_failure=summary.provider_failure,
        registry_result=registry_result,
        registry_path=registry_path,
        strategy=effective_strategy,
        diff_counts=diff_counts,
    )


def watch_scan_sources(
    cfg: MindForgeConfig,
    *,
    ref: str | None = None,
    all_sources: bool = False,
    strategy: StrategySelection | None = None,
    process_changes: bool = True,
) -> WatchScanSummary:
    """扫描已保存 watched sources, 并按 baseline diff 决定是否进入 ingestion.

    schedule/baseline 只决定"哪个顶层 source due, 哪些文件新增或变化".
    当 process_changes=True (worker 路径) 时, 变更文件直接进入 ingestion pipeline
    同步处理. 当 process_changes=False (CLI 路径) 时, 只做 scan + diff + registry
    更新, 不调用 _ingest_targets_summary(); CLI 调用方负责为有变更的 source
    创建 background ProcessingRun.

    Source deletion never deletes approved knowledge.
    Knowledge reduction is always manual. Watch is additive by default.
    """

    registry_path = registry_path_for_vault(cfg.vault.root)
    if ref:
        source = find_watch_source(cfg.vault.root, registry_path, ref)
        candidates = [source] if source is not None else []
    else:
        candidates = [
            source
            for source in list_watch_sources(cfg.vault.root, registry_path)
            if not source.is_default
        ]
    totals = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}
    diff_totals = {"added": 0, "changed": 0, "unchanged": 0, "deleted": 0, "skipped": 0}
    scanned = 0
    not_due = 0
    missing = 0
    scanned_ids: list[str] = []
    source_details: list[WatchScanSourceDetail] = []
    skipped_details: list[SkippedDocumentDetail] = []
    error_details: list[str] = []
    provider_failure: ProviderFailureDetail | None = None

    for source in candidates:
        if source is None:
            continue
        if source.status == "paused":
            not_due += 1
            continue
        if not ref and not all_sources and not is_due(source):
            not_due += 1
            continue
        scanned += 1
        scanned_ids.append(source.id)
        if not source.path.exists():
            missing += 1
            deleted_baseline = {
                key: WatchFileSnapshot(
                    relative_path=item.relative_path,
                    path=item.path,
                    content_hash=item.content_hash,
                    size=item.size,
                    mtime=item.mtime,
                    last_seen_at=item.last_seen_at,
                    last_processed_at=item.last_processed_at,
                    status="deleted",
                    skipped_reason=item.skipped_reason,
                )
                for key, item in source.baseline.items()
            }
            source_diff = {
                "added": 0,
                "changed": 0,
                "unchanged": 0,
                "deleted": len(source.baseline),
                "skipped": 0,
            }
            _merge_counts(diff_totals, source_diff)
            source_details.append(WatchScanSourceDetail(
                source_id=source.id,
                path=source.path,
                has_changes=False,
                diff_counts=source_diff,
            ))
            update_watch_source(
                cfg.vault.root,
                registry_path,
                source.id,
                last_scan_at=_now(),
                next_scan_at=next_scan_after(_now(), source.frequency),
                status="missing",
                error="source path missing",
                baseline=deleted_baseline,
                diff_counts=source_diff,
            )
            continue

        baseline, source_diff = _build_source_baseline(cfg, source)
        _merge_counts(diff_totals, source_diff)
        changed_targets = _changed_targets_from_baseline(baseline, source_diff)
        has_changes = bool(changed_targets)
        source_failed = False

        if process_changes and changed_targets:
            # worker 路径：同步处理变更文件
            effective_strategy = resolve_strategy_selection(cfg, watched_strategy=source.strategy_id)
            summary = _ingest_targets_summary(
                cfg,
                changed_targets[0] if len(changed_targets) == 1 else changed_targets,
                command="watch_scan",
                bypass_triage_gate=False,
                strategy=effective_strategy,
            )
            _merge_counts(totals, summary.counts)
            skipped_details.extend(summary.skipped)
            error_details.extend(summary.errors)
            if summary.provider_failure is not None:
                provider_failure = summary.provider_failure
            source_failed = bool(summary.counts.get("failed"))

        source_details.append(WatchScanSourceDetail(
            source_id=source.id,
            path=source.path,
            has_changes=has_changes,
            diff_counts=source_diff,
        ))

        # registry 更新：process_changes=False 时只更新 scan 时间戳和 diff_counts，
        # 不更新 baseline（留给 worker 处理完后再更新），避免 worker 找不到变更。
        if process_changes:
            update_watch_source(
                cfg.vault.root,
                registry_path,
                source.id,
                last_seen_at=_now(),
                last_processed_at=_now() if changed_targets else source.last_processed_at,
                last_scan_at=_now(),
                next_scan_at=next_scan_after(_now(), source.frequency),
                status="error" if source_failed else "active",
                error="one or more sources failed" if source_failed else None,
                baseline=baseline,
                diff_counts=source_diff,
            )
        else:
            update_watch_source(
                cfg.vault.root,
                registry_path,
                source.id,
                last_seen_at=_now(),
                last_scan_at=_now(),
                next_scan_at=next_scan_after(_now(), source.frequency),
                diff_counts=source_diff,
            )

    return WatchScanSummary(
        scanned=scanned,
        not_due=not_due,
        missing=missing,
        counts=totals,
        diff_counts=diff_totals,
        source_ids=tuple(scanned_ids),
        source_details=tuple(source_details),
        skipped=tuple(skipped_details),
        errors=tuple(error_details),
        provider_failure=provider_failure,
    )


def watch_sources_for_display(cfg: MindForgeConfig) -> tuple[object, ...]:
    registry = registry_path_for_vault(cfg.vault.root)
    from .watch_registry import list_watch_sources

    return list_watch_sources(cfg.vault.root, registry)


def _ingest_targets(cfg: MindForgeConfig, target: Path, *, command: str) -> dict[str, int]:
    return _ingest_targets_summary(
        cfg,
        target,
        command=command,
        bypass_triage_gate=False,
    ).counts


def _ingest_targets_summary(
    cfg: MindForgeConfig,
    target: Path | list[Path],
    *,
    command: str,
    bypass_triage_gate: bool,
    strategy: StrategySelection,
) -> IngestionSummary:
    target_exists = all(path.exists() for path in target) if isinstance(target, list) else target.exists()
    if not target_exists:
        raise SourcePathError(f"File or folder not found: {target}. Please verify the path exists.")
    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}
    mux = SourceMux()
    results: list = []
    duplicate_skips: list = []
    for result in discover_source_results(cfg, target):
        kept = mux.feed(result)
        if kept is not None:
            results.append(kept)
            continue
        if result.document is not None:
            duplicate_skips.append((result, result.document))
    if not results and not duplicate_skips:
        # 中文学习型说明：seen=0 表示没有输入，不是一次成功处理。这里不创建
        # RunLogger、不保存 checkpoint，避免 missing/empty import 把 processed
        # registry、fingerprint 或 run state 污染到后续真实处理。
        return IngestionSummary(mode=command, target=target, counts=counts)

    runtime = resolve_process_runtime(
        ProcessRequest(
            cfg=cfg,
            file=None,
            limit=None,
            dry_run=False,
            prompts_dir=None,
            tracks=None,
            template=None,
            bypass_triage_gate=bypass_triage_gate,
        )
    )
    if isinstance(runtime, ProcessError):
        raise RuntimeError(runtime.message)
    try:
        parts = build_process_runtime_parts(
            cfg=cfg,
            runtime=runtime,
            strategy=strategy.strategy_id,
        )
    except ProviderError as exc:
        error_details = []
        for result in results:
            counts["seen"] += 1
            counts["failed"] += 1
            error_details.append(str(exc))
        skipped_details = []
        for _result, doc in duplicate_skips:
            counts["seen"] += 1
            counts["skipped"] += 1
            skipped_details.append(_skip_detail(
                doc,
                reason="duplicate_content_hash",
                matched_record=doc.content_hash,
            ))
        return IngestionSummary(
            mode=command,
            target=target,
            counts=counts,
            skipped=tuple(skipped_details),
            errors=tuple(error_details),
            provider_failure=provider_failure_detail(cfg, str(exc)),
            strategy=strategy,
        )
    except (UnknownStrategyError, NotYetImplementedStrategyError) as exc:
        raise RuntimeError(str(strategy_error_from_build_error(strategy.strategy_id, exc))) from exc
    except StrategySelectionError as exc:
        raise RuntimeError(str(exc)) from exc
    approved_sources = build_approved_source_index(cfg)
    processed_sources = _build_processed_source_index(parts.checkpoint)
    processed_content_hashes = _build_processed_content_hash_index(parts.checkpoint)
    skipped_details: list[SkippedDocumentDetail] = []
    error_details: list[str] = []
    with RunLogger(cfg.state.runs_path, command=command) as logger:
        parts.pipeline.logger = logger
        for result, doc in duplicate_skips:
            counts["seen"] += 1
            _emit_skip(
                result=result,
                doc=doc,
                logger=logger,
                counts=counts,
                reason="duplicate_content_hash",
            )
            skipped_details.append(_skip_detail(
                doc,
                reason="duplicate_content_hash",
                matched_record=doc.content_hash,
            ))
        for result in results:
            counts["seen"] += 1
            if not result.ok:
                emit_source_error(result=result, logger=logger, counts=counts)
                if result.error:
                    error_details.append(result.error)
                continue
            doc = result.document
            assert doc is not None
            approved_match = approved_sources.match(
                source_id=doc.source_id,
                source_path=doc.source_path,
                vault_root=cfg.vault.root,
                content_hash=doc.content_hash,
            )
            if approved_match is not None:
                _emit_skip(
                    result=result,
                    doc=doc,
                    logger=logger,
                    counts=counts,
                    reason="already_approved",
                )
                skipped_details.append(_skip_detail(
                    doc,
                    reason="already_approved",
                    matched_record=approved_match.card_path,
                ))
                continue
            processed_match = _processed_match(doc.source_id, doc.content_hash, processed_sources)
            if processed_match is not None:
                _emit_skip(
                    result=result,
                    doc=doc,
                    logger=logger,
                    counts=counts,
                    reason="already_processed",
                )
                skipped_details.append(_skip_detail(
                    doc,
                    reason="already_processed",
                    matched_record=processed_match.state_key,
                ))
                continue
            duplicate_match = processed_content_hashes.get(doc.content_hash)
            if duplicate_match is not None:
                _emit_skip(
                    result=result,
                    doc=doc,
                    logger=logger,
                    counts=counts,
                    reason="duplicate_content_hash",
                )
                skipped_details.append(_skip_detail(
                    doc,
                    reason="duplicate_content_hash",
                    matched_record=duplicate_match.state_key,
                ))
                continue
            try:
                status, message = process_one_result(
                    result=result,
                    cp=parts.checkpoint,
                    pipeline=parts.pipeline,
                    logger=logger,
                    writer=parts.writer,
                    cfg=cfg,
                    counts=counts,
                    dry_run=False,
                )
                if status == "skipped":
                    skipped_details.append(_skip_detail(
                        doc,
                        reason=message or "pipeline_skipped",
                        matched_record=None,
                    ))
                elif status == "failed" and message:
                    error_details.append(message)
            except ProviderError as exc:
                friendly = friendly_missing_key_error(str(exc))
                if friendly:
                    raise RuntimeError(friendly) from exc
                raise
        finalize_process_run(
            cp=parts.checkpoint,
            cfg=cfg,
            logger=logger,
            counts=counts,
            dry_run=False,
        )
    return IngestionSummary(
        mode=command,
        target=target,
        counts=counts,
        skipped=tuple(skipped_details),
        errors=tuple(error_details),
        strategy=strategy,
    )


def _build_source_baseline(
    cfg: MindForgeConfig,
    source: WatchedSource,
) -> tuple[dict[str, WatchFileSnapshot], dict[str, int]]:
    previous = source.baseline
    current: dict[str, WatchFileSnapshot] = {}
    now = _now()
    scan = enumerate_supported_source_files(
        cfg,
        source.path,
        SourceScanPolicy(recursive=source.recursive or source.path_type == "folder"),
    )
    parsed_by_path = {result.path.resolve(): result for result in discover_source_results(cfg, source.path)}
    for candidate in scan.candidates:
        resolved = candidate.path.resolve()
        result = parsed_by_path.get(resolved)
        stat = resolved.stat()
        rel = _relative_to_source(source, resolved)
        if result is None or not result.ok or result.document is None:
            current[rel] = WatchFileSnapshot(
                relative_path=rel,
                path=resolved,
                content_hash="",
                size=stat.st_size,
                mtime=stat.st_mtime,
                last_seen_at=now,
                status="skipped",
                skipped_reason="parse_failed",
            )
            continue
        previous_item = previous.get(rel)
        current[rel] = WatchFileSnapshot(
            relative_path=rel,
            path=resolved,
            content_hash=result.document.content_hash,
            size=stat.st_size,
            mtime=stat.st_mtime,
            last_seen_at=now,
            last_processed_at=previous_item.last_processed_at if previous_item else None,
            status="seen",
        )
    for skipped in scan.skipped:
        if not skipped.path.is_file():
            continue
        resolved = skipped.path.resolve()
        rel = _relative_to_source(source, resolved)
        stat = resolved.stat()
        current[rel] = WatchFileSnapshot(
            relative_path=rel,
            path=resolved,
            content_hash="",
            size=stat.st_size,
            mtime=stat.st_mtime,
            last_seen_at=now,
            status="skipped",
            skipped_reason=skipped.reason,
        )

    counts = {"added": 0, "changed": 0, "unchanged": 0, "deleted": 0, "skipped": 0}
    for rel, item in list(current.items()):
        if item.status == "skipped":
            counts["skipped"] += 1
            continue
        previous_item = previous.get(rel)
        if previous_item is None or previous_item.status == "deleted":
            counts["added"] += 1
            current[rel] = _with_status(item, "added")
        elif previous_item.content_hash != item.content_hash:
            counts["changed"] += 1
            current[rel] = _with_status(item, "changed")
        else:
            counts["unchanged"] += 1
            current[rel] = _with_status(item, "unchanged")
    for rel, item in previous.items():
        if rel not in current:
            counts["deleted"] += 1
            current[rel] = WatchFileSnapshot(
                relative_path=item.relative_path,
                path=item.path,
                content_hash=item.content_hash,
                size=item.size,
                mtime=item.mtime,
                last_seen_at=item.last_seen_at,
                last_processed_at=item.last_processed_at,
                status="deleted",
                skipped_reason=item.skipped_reason,
            )
    return current, counts


def _changed_targets_from_baseline(
    baseline: dict[str, WatchFileSnapshot],
    diff_counts: dict[str, int],
) -> list[Path]:
    if not diff_counts.get("added") and not diff_counts.get("changed"):
        return []
    return [
        item.path
        for item in baseline.values()
        if item.status in {"added", "changed"} and item.path.exists()
    ]


def _relative_to_source(source: WatchedSource, path: Path) -> str:
    if source.path_type == "file":
        return path.name
    try:
        return path.resolve().relative_to(source.path.resolve()).as_posix()
    except ValueError:
        return path.name


def _with_status(item: WatchFileSnapshot, status: str) -> WatchFileSnapshot:
    return WatchFileSnapshot(
        relative_path=item.relative_path,
        path=item.path,
        content_hash=item.content_hash,
        size=item.size,
        mtime=item.mtime,
        last_seen_at=item.last_seen_at,
        last_processed_at=item.last_processed_at,
        status=status,
        skipped_reason=item.skipped_reason,
    )


def _merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


@dataclass(frozen=True)
class ProcessedSourceMatch:
    """已处理 source 的命中信息，用于向用户解释 skipped 原因。"""

    state_key: str


def _build_processed_source_index(checkpoint) -> dict[tuple[str, str], ProcessedSourceMatch]:
    """构建 precise already_processed 索引。

    中文学习型说明：already_processed 只能命中同一个 ``source_id`` 且同一个
    ``content_hash``。这里不按 folder、source root 或单纯 content_hash 去重，
    避免已处理 A 文件后误伤同目录 B 文件，或同内容不同文件。
    """

    keys: dict[tuple[str, str], ProcessedSourceMatch] = {}
    for item in checkpoint.all_items():
        if item.status == "processed" and item.card_path:
            keys[(item.source_id, item.content_hash)] = ProcessedSourceMatch(
                state_key=item.state_key,
            )
    return keys


def _build_processed_content_hash_index(checkpoint) -> dict[str, ProcessedSourceMatch]:
    """构建 content_hash 级 dedupe 索引。

    中文学习型说明：同一个 source 的 unchanged 文件优先走 already_processed，
    不同路径但相同 parser content_hash 的文件走 duplicate_content_hash。
    这样用户能区分"这个文件没变"和"这个内容已经从别处生成过知识"。
    """

    keys: dict[str, ProcessedSourceMatch] = {}
    for item in checkpoint.all_items():
        if item.status == "processed" and item.card_path:
            keys[item.content_hash] = ProcessedSourceMatch(state_key=item.state_key)
    return keys


def _processed_match(
    source_id: str,
    content_hash: str,
    processed_sources: dict[tuple[str, str], ProcessedSourceMatch],
) -> ProcessedSourceMatch | None:
    return processed_sources.get((source_id, content_hash))


def _emit_skip(*, result, doc: SourceDocument, logger, counts: dict[str, int], reason: str) -> None:
    counts["skipped"] += 1
    logger.emit(
        "source_skipped_or_unchanged",
        source_id=doc.source_id,
        source_type=doc.source_type,
        adapter_name=result.adapter_name,
        source_path=doc.source_path,
        content_hash=doc.content_hash,
        status=reason,
        skip_reason=reason,
    )


def _normalized_source_path(source_path: str) -> str:
    try:
        return str(Path(source_path).expanduser().resolve())
    except OSError:
        return source_path


def _short_hash(value: str, *, length: int = 12) -> str:
    return value.split(":", 1)[-1][:length]


def _skip_detail(
    doc: SourceDocument,
    *,
    reason: str,
    matched_record: str | None,
) -> SkippedDocumentDetail:
    hint = None
    if reason.startswith("triage "):
        hint = (
            f"use `mindforge import {doc.source_path} --force` to generate an "
            "ai_draft anyway"
        )
    return SkippedDocumentDetail(
        source_path=doc.source_path,
        normalized_path=_normalized_source_path(doc.source_path),
        source_id_short=_short_hash(doc.source_id),
        fingerprint_short=_short_hash(doc.content_hash),
        reason=reason,
        matched_record=matched_record,
        hint=hint,
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


__all__ = [
    "IngestionSummary",
    "WatchScanSourceDetail",
    "WatchScanSummary",
    "import_sources",
    "watch_scan_sources",
    "watch_add_source",
    "watch_sources_for_display",
]
