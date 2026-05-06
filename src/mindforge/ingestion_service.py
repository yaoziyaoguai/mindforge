"""Simple watch/import ingestion workflow.

中文学习型说明：本 service 是用户级 ingestion 入口的业务层。CLI 只负责参数和
展示；这里负责 registry、source discovery、dedupe、checkpoint、writer 与
pipeline 的组合。它不 approve、不删除 source、不复制外部 source 到 Inbox。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .checkpoint import Checkpoint
from .config import MindForgeConfig
from .llm.base import ProviderError
from .process_executor import (
    build_approved_source_index,
    build_process_runtime_parts,
    emit_already_approved_source_skip,
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
    registry_result: AddWatchResult | None = None
    registry_path: Path | None = None


REAL_PROVIDER_KEY_ERRORS = {
    "MINDFORGE_OPENAI_API_KEY": (
        "real provider openai_compatible requires MINDFORGE_OPENAI_API_KEY. "
        "Set it via shell export or local .env. Do not put secrets in YAML. "
        "fake/demo remains available with --provider fake."
    ),
    "MINDFORGE_ANTHROPIC_API_KEY": (
        "real provider anthropic requires MINDFORGE_ANTHROPIC_API_KEY. "
        "Set it via shell export or local .env. Do not put secrets in YAML. "
        "fake/demo remains available with --provider fake."
    ),
}

REAL_PROVIDER_KEY_ERROR = (
    "real provider openai_compatible requires MINDFORGE_OPENAI_API_KEY. "
    "Set it via shell export or local .env. Do not put secrets in YAML. "
    "fake/demo remains available with --provider fake."
)


def import_sources(cfg: MindForgeConfig, target: Path) -> IngestionSummary:
    """一次性导入当前内容，不写 watched source registry。"""

    counts = _ingest_targets(cfg, target, command="import")
    return IngestionSummary(mode="import", target=target, counts=counts)


def watch_add_source(cfg: MindForgeConfig, target: Path) -> IngestionSummary:
    """注册 watched source，并立即处理当前内容。

    第一版 watch add 不是后台监听：它只登记来源 + 做一次当前内容 ingestion。
    未来 polling/hook 可以复用 registry 中的 fingerprint/last_seen 字段。
    """

    registry_path = registry_path_for_vault(cfg.vault.root)
    registry_result = add_watch_source(cfg.vault.root, registry_path, target)
    counts = _ingest_targets(cfg, registry_result.source.path, command="watch_add")
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
        registry_result=registry_result,
        registry_path=registry_path,
    )


def watch_sources_for_display(cfg: MindForgeConfig) -> tuple[object, ...]:
    registry = registry_path_for_vault(cfg.vault.root)
    from .watch_registry import list_watch_sources

    return list_watch_sources(cfg.vault.root, registry)


def _ingest_targets(cfg: MindForgeConfig, target: Path, *, command: str) -> dict[str, int]:
    runtime = resolve_process_runtime(
        ProcessRequest(
            cfg=cfg,
            file=None,
            limit=None,
            dry_run=False,
            prompts_dir=None,
            tracks=None,
            template=None,
        )
    )
    if isinstance(runtime, ProcessError):
        raise RuntimeError(runtime.message)
    try:
        parts = build_process_runtime_parts(cfg=cfg, runtime=runtime, strategy="five_stage")
    except ProviderError as exc:
        friendly = _friendly_missing_key_error(str(exc))
        if friendly:
            raise RuntimeError(friendly) from exc
        raise
    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}
    approved_sources = build_approved_source_index(cfg)
    processed_sources = _build_processed_source_index(parts.checkpoint)
    mux = SourceMux()
    with RunLogger(cfg.state.runs_path, command=command) as logger:
        parts.pipeline.logger = logger
        for result in mux.iter_deduped(discover_source_results(cfg, target)):
            counts["seen"] += 1
            if not result.ok:
                emit_source_error(result=result, logger=logger, counts=counts)
                continue
            doc = result.document
            assert doc is not None
            if approved_sources.contains(
                source_id=doc.source_id,
                source_path=doc.source_path,
                vault_root=cfg.vault.root,
            ):
                emit_already_approved_source_skip(
                    result=result,
                    doc=doc,
                    logger=logger,
                    counts=counts,
                )
                continue
            if _already_processed(doc.source_id, doc.content_hash, processed_sources):
                counts["skipped"] += 1
                logger.emit(
                    "source_skipped_or_unchanged",
                    source_id=doc.source_id,
                    source_type=doc.source_type,
                    adapter_name=result.adapter_name,
                    source_path=doc.source_path,
                    content_hash=doc.content_hash,
                    status="already_processed",
                    skip_reason="already_processed",
                )
                continue
            try:
                process_one_result(
                    result=result,
                    cp=parts.checkpoint,
                    pipeline=parts.pipeline,
                    logger=logger,
                    writer=parts.writer,
                    cfg=cfg,
                    counts=counts,
                    dry_run=False,
                )
            except ProviderError as exc:
                friendly = _friendly_missing_key_error(str(exc))
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
    return counts


def _build_processed_source_index(checkpoint: Checkpoint) -> frozenset[tuple[str, str]]:
    keys: set[tuple[str, str]] = set()
    for item in checkpoint.all_items():
        if item.status == "processed" and item.card_path:
            keys.add((item.source_id, item.content_hash))
    return frozenset(keys)


def _already_processed(
    source_id: str,
    content_hash: str,
    processed_sources: frozenset[tuple[str, str]],
) -> bool:
    return (source_id, content_hash) in processed_sources


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _friendly_missing_key_error(message: str) -> str | None:
    for env_name, friendly in REAL_PROVIDER_KEY_ERRORS.items():
        if env_name in message and _looks_like_missing_key(message):
            return friendly
    return None


def _looks_like_missing_key(message: str) -> bool:
    return (
        "未设置" in message or "requires" in message or "要求环境变量" in message
    )


__all__ = [
    "IngestionSummary",
    "import_sources",
    "watch_add_source",
    "watch_sources_for_display",
]
