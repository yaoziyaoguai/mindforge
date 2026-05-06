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
from .source_discovery import discover_source_results
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
    add_watch_source,
    registry_path_for_vault,
    update_watch_source,
)


@dataclass(frozen=True)
class IngestionSummary:
    mode: str
    target: Path
    counts: dict[str, int]
    skipped: tuple[SkippedDocumentDetail, ...] = ()
    provider_failure: ProviderFailureDetail | None = None
    registry_result: AddWatchResult | None = None
    registry_path: Path | None = None
    strategy: StrategySelection | None = None


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
) -> IngestionSummary:
    """注册 watched source，并立即处理当前内容。

    第一版 watch add 不是后台监听：它只登记来源 + 做一次当前内容 ingestion。
    未来 polling/hook 可以复用 registry 中的 fingerprint/last_seen 字段。
    """

    if not target.exists():
        raise RuntimeError(f"File not found: {target}")
    selected_strategy = strategy or resolve_strategy_selection(cfg)
    registry_path = registry_path_for_vault(cfg.vault.root)
    registry_result = add_watch_source(
        cfg.vault.root,
        registry_path,
        target,
        strategy_id=selected_strategy.strategy_id,
    )
    effective_strategy = resolve_strategy_selection(
        cfg,
        watched_strategy=registry_result.source.strategy_id,
    )
    summary = _ingest_targets_summary(
        cfg,
        registry_result.source.path,
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
    target: Path,
    *,
    command: str,
    bypass_triage_gate: bool,
    strategy: StrategySelection,
) -> IngestionSummary:
    if not target.exists():
        raise RuntimeError(f"File not found: {target}")
    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}
    mux = SourceMux(key_fn=_document_identity_key)
    results = list(mux.iter_deduped(discover_source_results(cfg, target)))
    if not results:
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
        for result in results:
            counts["seen"] += 1
            counts["failed"] += 1
        return IngestionSummary(
            mode=command,
            target=target,
            counts=counts,
            provider_failure=provider_failure_detail(cfg, str(exc)),
            strategy=strategy,
        )
    except (UnknownStrategyError, NotYetImplementedStrategyError) as exc:
        raise RuntimeError(str(strategy_error_from_build_error(strategy.strategy_id, exc))) from exc
    except StrategySelectionError as exc:
        raise RuntimeError(str(exc)) from exc
    approved_sources = build_approved_source_index(cfg)
    processed_sources = _build_processed_source_index(parts.checkpoint)
    skipped_details: list[SkippedDocumentDetail] = []
    with RunLogger(cfg.state.runs_path, command=command) as logger:
        parts.pipeline.logger = logger
        for result in results:
            counts["seen"] += 1
            if not result.ok:
                emit_source_error(result=result, logger=logger, counts=counts)
                continue
            doc = result.document
            assert doc is not None
            approved_match = approved_sources.match(
                source_id=doc.source_id,
                source_path=doc.source_path,
                vault_root=cfg.vault.root,
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
        strategy=strategy,
    )


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


def _document_identity_key(doc: SourceDocument) -> str:
    """同批次 dedupe key 必须精确到具体 source document。

    中文学习型说明：content_hash 只能说明“正文和关键 metadata 一样”，不能说明
    “是同一个用户文件”。watch/import 的产品语义是 file/folder ingestion，
    同内容不同文件仍是两个可审核 source，不能互相误伤。
    """

    return f"{doc.source_type}::{_normalized_source_path(doc.source_path)}"


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
    "import_sources",
    "watch_add_source",
    "watch_sources_for_display",
]
