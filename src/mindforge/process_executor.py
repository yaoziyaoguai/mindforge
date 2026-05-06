"""Reusable process execution primitives.

中文学习型说明：``process_cli`` 与 simple watch/import ingestion 都需要把
``ScanResult`` 跑过 pipeline 并写出 ai_draft card。这里承载可复用副作用编排，
避免 ingestion service 反向 import CLI adapter，也避免复制一套 process 逻辑。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .cards import iter_cards
from .checkpoint import Checkpoint
from .config import MindForgeConfig
from .models import ItemState, StageRecord
from .process_service import ProcessRuntime, summarize_outcome
from .run_logger import EVENT_SOURCE_ERROR, EVENT_STATE_WRITTEN
from .scanner import Scanner
from .strategies import StrategyContext, build_strategy
from .writer import CardWriter


@dataclass(frozen=True)
class ApprovedSourceMatch:
    card_path: str


@dataclass(frozen=True)
class ApprovedSourceIndex:
    source_ids: dict[str, ApprovedSourceMatch]
    source_paths: dict[str, ApprovedSourceMatch]

    def contains(self, *, source_id: str, source_path: str, vault_root: Path) -> bool:
        return self.match(
            source_id=source_id,
            source_path=source_path,
            vault_root=vault_root,
        ) is not None

    def match(self, *, source_id: str, source_path: str, vault_root: Path) -> ApprovedSourceMatch | None:
        """按具体 source identity 命中 human_approved 来源。

        中文学习型说明：approval boundary 是“某个 source document 对应的
        draft 被人批准”，不是“整个目录已批准”。因此索引只看 card frontmatter
        记录的 source_id / source_path，不用 parent folder 或 content hash 推断。
        """

        if source_id in self.source_ids:
            return self.source_ids[source_id]
        for key in source_path_keys(source_path, vault_root=vault_root):
            match = self.source_paths.get(key)
            if match is not None:
                return match
        return None


@dataclass(frozen=True)
class ProcessRuntimeParts:
    scanner: Scanner
    checkpoint: Checkpoint
    writer: CardWriter
    pipeline: object


def build_pipeline(*, cfg: MindForgeConfig, runtime: ProcessRuntime, strategy: str):
    """构造 process pipeline；不依赖 Typer/Rich。

    CLI 负责把异常翻译成用户文案；watch/import ingestion 使用固定策略并让错误
    冒泡为普通异常。这样组合根可以复用，同时不会让 service 反向 import CLI。
    """

    from .llm import LLMClient, build_providers

    providers = build_providers(cfg.llm)
    client = LLMClient(llm_config=cfg.llm, providers=providers)
    strategy_ctx = StrategyContext(
        client=client,
        prompts_dir=runtime.assets.prompts_dir,
        prompt_versions=cfg.prompts,
        triage_threshold=cfg.triage.value_score_threshold,
        learning_tracks_text=runtime.assets.tracks_text,
        logger=None,
    )
    return build_strategy(strategy, strategy_ctx)


def build_process_runtime_parts(
    *,
    cfg: MindForgeConfig,
    runtime: ProcessRuntime,
    strategy: str,
) -> ProcessRuntimeParts:
    return ProcessRuntimeParts(
        scanner=Scanner(cfg),
        checkpoint=Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state),
        writer=writer_for_runtime(cfg, runtime),
        pipeline=build_pipeline(cfg=cfg, runtime=runtime, strategy=strategy),
    )


def writer_for_runtime(cfg: MindForgeConfig, runtime: ProcessRuntime) -> CardWriter:
    if runtime.assets.template_path is not None:
        return CardWriter(
            vault_root=cfg.vault.root,
            cards_dir=cfg.vault.cards_dir,
            template_path=runtime.assets.template_path,
        )
    return CardWriter(
        vault_root=cfg.vault.root,
        cards_dir=cfg.vault.cards_dir,
        template_text=runtime.assets.template_text,
    )


def source_path_keys(source_path: str, *, vault_root: Path) -> set[str]:
    keys = {source_path}
    p = Path(source_path).expanduser()
    if not p.is_absolute():
        keys.add(str((vault_root / p).resolve()))
    try:
        resolved = p.resolve()
        keys.add(str(resolved))
        try:
            keys.add(resolved.relative_to(vault_root.resolve()).as_posix())
        except ValueError:
            pass
    except OSError:
        pass
    return keys


def build_approved_source_index(cfg: MindForgeConfig) -> ApprovedSourceIndex:
    card_scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    source_ids: dict[str, ApprovedSourceMatch] = {}
    source_paths: dict[str, ApprovedSourceMatch] = {}
    for card in card_scan.cards:
        if card.status != "human_approved":
            continue
        match = ApprovedSourceMatch(card_path=card.rel_path)
        if card.source_id:
            source_ids[card.source_id] = match
        if card.source_path:
            for key in source_path_keys(card.source_path, vault_root=cfg.vault.root):
                source_paths[key] = match
    return ApprovedSourceIndex(
        source_ids=source_ids,
        source_paths=source_paths,
    )


def upsert_processing_item(result, cp: Checkpoint) -> tuple[object, ItemState]:
    doc = result.document
    assert doc is not None
    candidate = ItemState(
        source_id=doc.source_id,
        source_type=doc.source_type,
        adapter_name=result.adapter_name,
        source_path=doc.source_path,
        content_hash=doc.content_hash,
        first_seen_at=datetime.now(),
    )
    return doc, cp.upsert_seen(candidate)


def copy_stage_meta_to_item(item: ItemState, outcome, *, now: datetime) -> None:
    item.status = outcome.status
    item.processed_at = now
    item.error_message = outcome.error_message
    for stage_name, meta in outcome.stages_meta.items():
        item.stages[stage_name] = StageRecord(
            stage=stage_name,
            model_alias=meta["model_alias"],
            provider=meta["provider"],
            actual_model=meta["actual_model"],
            prompt_version=meta["prompt_version"],
            status=meta["status"],
            processed_at=now,
            tokens_in=meta.get("tokens_in"),
            tokens_out=meta.get("tokens_out"),
            latency_ms=meta.get("latency_ms"),
        )


def processed_run_dict(*, cfg: MindForgeConfig, outcome, logger, now: datetime) -> dict[str, object]:
    return {
        "created_at": now.isoformat(timespec="seconds"),
        "prompts": {"distill_version": cfg.prompts.distill},
        "profile": cfg.llm.active_profile,
        "stage_models": {
            stage: {
                "alias": meta["model_alias"],
                "provider": meta["provider"],
                "model": meta["actual_model"],
            }
            for stage, meta in outcome.stages_meta.items()
        },
        "run_id": logger.run_id,
    }


def process_one_result(
    *,
    result,
    cp: Checkpoint,
    pipeline,
    logger,
    writer: CardWriter,
    cfg: MindForgeConfig,
    counts: dict[str, int],
    dry_run: bool,
) -> tuple[str, str | None]:
    """处理单个 ScanResult，返回 ``(status, message)`` 供 CLI/presenter 使用。"""

    doc, item = upsert_processing_item(result, cp)
    outcome = pipeline.run(doc)
    item_result = summarize_outcome(
        outcome, doc, result.adapter_name, dry_run=dry_run
    )

    now = datetime.now()
    item.last_run_id = logger.run_id
    copy_stage_meta_to_item(item, outcome, now=now)

    if outcome.status == "skipped":
        counts["skipped"] += 1
        item.track = item_result.track
        item.value_score = item_result.value_score
        logger.emit(
            "source_processed",
            source_id=doc.source_id,
            source_type=doc.source_type,
            adapter_name=result.adapter_name,
            source_path=doc.source_path,
            content_hash=doc.content_hash,
            status="skipped",
            track=item.track or "",
            value_score=item.value_score or 0,
            skip_reason=outcome.skip_reason or "",
        )
        return "skipped", outcome.skip_reason

    if outcome.status == "failed":
        counts["failed"] += 1
        logger.emit(
            "source_processed",
            source_id=doc.source_id,
            source_type=doc.source_type,
            adapter_name=result.adapter_name,
            source_path=doc.source_path,
            content_hash=doc.content_hash,
            status="failed",
            stage_failed=outcome.error_stage or "",
            error_message=outcome.error_message or "",
        )
        return "failed", outcome.error_message

    counts["processed"] += 1
    item.track = item_result.track
    item.value_score = item_result.value_score
    if item_result.would_write_only:
        logger.emit(
            "source_processed",
            source_id=doc.source_id,
            source_type=doc.source_type,
            adapter_name=result.adapter_name,
            source_path=doc.source_path,
            content_hash=doc.content_hash,
            status="processed",
            track=item.track or "",
            value_score=item.value_score or 0,
        )
        return "processed", None

    wr = writer.write(
        card_payload=outcome.card_payload or {},
        source=item_result.source_dict,
        run=processed_run_dict(cfg=cfg, outcome=outcome, logger=logger, now=now),
    )
    item.card_path = str(wr.path.relative_to(cfg.vault.root))
    logger.emit(
        "card_written",
        output_file=str(wr.path),
        source_id=doc.source_id,
        source_type=doc.source_type,
        track=item.track or "",
        value_score=item.value_score or 0,
        card_conflict="true" if wr.conflict else "false",
    )
    logger.emit(
        "source_processed",
        source_id=doc.source_id,
        source_type=doc.source_type,
        adapter_name=result.adapter_name,
        source_path=doc.source_path,
        content_hash=doc.content_hash,
        status="processed",
        track=item.track or "",
        value_score=item.value_score or 0,
        output_file=str(wr.path),
    )
    return "conflict" if wr.conflict else "processed", str(wr.path)


def emit_already_approved_source_skip(*, result, doc, logger, counts: dict[str, int]) -> None:
    counts["skipped"] += 1
    logger.emit(
        "source_skipped_or_unchanged",
        source_id=doc.source_id,
        source_type=doc.source_type,
        adapter_name=result.adapter_name,
        source_path=doc.source_path,
        content_hash=doc.content_hash,
        status="already_approved",
        skip_reason="already_approved",
    )


def emit_source_error(*, result, logger, counts: dict[str, int]) -> None:
    counts["failed"] += 1
    logger.emit(
        EVENT_SOURCE_ERROR,
        source_type=result.source_type,
        adapter_name=result.adapter_name,
        path=str(result.path),
        error_message=result.error or "",
    )


def finalize_process_run(*, cp: Checkpoint, cfg: MindForgeConfig, logger, counts: dict[str, int], dry_run: bool) -> None:
    if dry_run:
        return
    cp.save(active_profile=cfg.llm.active_profile)
    logger.emit(
        EVENT_STATE_WRITTEN,
        path=str(cfg.state.state_path),
        items_count=len(list(cp.all_items())),
    )


__all__ = [
    "ApprovedSourceIndex",
    "ApprovedSourceMatch",
    "ProcessRuntimeParts",
    "build_approved_source_index",
    "build_pipeline",
    "build_process_runtime_parts",
    "emit_already_approved_source_skip",
    "emit_source_error",
    "finalize_process_run",
    "process_one_result",
    "source_path_keys",
    "writer_for_runtime",
]
