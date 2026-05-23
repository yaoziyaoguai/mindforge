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
from .quality.models import CardQuality
from .quality.rubric import score_quality
from .quality.warnings import detect_warnings
from .quality.card_type import classify_card_type
from .quality.suggestions import generate_suggestions
from .run_logger import EVENT_SOURCE_ERROR, EVENT_STATE_WRITTEN
from .scanner import Scanner
from .strategies import (
    DEFAULT_STRATEGY_NAME,
    StrategyContext,
    build_strategy,
    get_strategy_metadata,
)
from .writer import CardWriter


@dataclass(frozen=True)
class ApprovedSourceMatch:
    card_path: str
    source_content_hash: str | None = None


@dataclass(frozen=True)
class ApprovedSourceIndex:
    source_ids: dict[str, ApprovedSourceMatch]
    source_paths: dict[str, ApprovedSourceMatch]

    def contains(
        self,
        *,
        source_id: str,
        source_path: str,
        vault_root: Path,
        content_hash: str | None = None,
    ) -> bool:
        return self.match(
            source_id=source_id,
            source_path=source_path,
            vault_root=vault_root,
            content_hash=content_hash,
        ) is not None

    def match(
        self,
        *,
        source_id: str,
        source_path: str,
        vault_root: Path,
        content_hash: str | None = None,
    ) -> ApprovedSourceMatch | None:
        """按具体 source identity 命中 human_approved 来源。

        中文学习型说明：approval boundary 是“某个 source document 对应的
        draft 被人批准”，不是“整个目录已批准”。因此索引只看 card frontmatter
        记录的 source_id / source_path。内容变化时 content_hash 会变，新版本
        必须允许重新生成 ai_draft；所以如果调用方提供 content_hash，只有同一
        hash 的已批准卡片才算 already_approved。
        """

        if source_id in self.source_ids:
            match = self.source_ids[source_id]
            if _hash_matches(match, content_hash):
                return match
        for key in source_path_keys(source_path, vault_root=vault_root):
            match = self.source_paths.get(key)
            if match is not None and _hash_matches(match, content_hash):
                return match
        return None


@dataclass(frozen=True)
class ProcessRuntimeParts:
    scanner: Scanner
    checkpoint: Checkpoint
    writer: CardWriter
    pipeline: object


def build_pipeline(
    *,
    cfg: MindForgeConfig,
    runtime: ProcessRuntime,
    strategy: str,
    llm_client: object | None = None,
):
    """构造 process pipeline；不依赖 Typer/Rich。

    中文学习型说明：strategy selection 与 provider selection 正交。生产路径
    只应通过 Knowledge Card Strategy 进入五段 prompt pipeline。测试要替身化
    LLM response，而不是选择 deterministic strategy 来绕过生产 runtime path。
    ``llm_client`` 是测试注入 seam：它替身化模型返回，不替换 strategy。
    生产调用不传此参数，仍由 ProviderFactory/LLMClient 正常装配。
    """

    client = llm_client
    metadata = get_strategy_metadata(strategy)
    if client is None and metadata.provider_mode != "deterministic":
        from .llm import LLMClient, build_providers
        from .secret_store import resolve_project_root_from_config

        providers = build_providers(
            cfg.llm,
            project_root=resolve_project_root_from_config(cfg),
        )
        client = LLMClient(llm_config=cfg.llm, providers=providers)
    strategy_ctx = StrategyContext(
        client=client,
        prompts_dir=runtime.assets.prompts_dir,
        prompt_versions=cfg.prompts,
        triage_threshold=cfg.triage.value_score_threshold,
        bypass_triage_gate=runtime.bypass_triage_gate,
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
        match = ApprovedSourceMatch(
            card_path=card.rel_path,
            source_content_hash=card.source_content_hash,
        )
        if card.source_id:
            source_ids[card.source_id] = match
        if card.source_path:
            for key in source_path_keys(card.source_path, vault_root=cfg.vault.root):
                source_paths[key] = match
    return ApprovedSourceIndex(
        source_ids=source_ids,
        source_paths=source_paths,
    )


def _hash_matches(match: ApprovedSourceMatch, content_hash: str | None) -> bool:
    if content_hash is None:
        return True
    return bool(match.source_content_hash and match.source_content_hash == content_hash)


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


def _prompt_versions_dict(cfg: MindForgeConfig) -> dict[str, str]:
    """返回 stage -> prompt version 的安全 provenance。

    中文学习型说明：卡片需要能解释“用了哪些 prompt 版本”，但不能把完整
    prompt 文本写进 frontmatter。这里仅持久化版本号，既能复现生成链路，
    又不会泄漏 prompt asset 或 source 正文。
    """

    return {
        "triage": cfg.prompts.triage,
        "distill": cfg.prompts.distill,
        "link_suggestion": cfg.prompts.link_suggestion,
        "review_questions": cfg.prompts.review_questions,
        "action_extraction": cfg.prompts.action_extraction,
    }


def processed_run_dict(*, cfg: MindForgeConfig, outcome, logger, now: datetime) -> dict[str, object]:
    card_payload = outcome.card_payload or {}
    source_evidence = card_payload.get("source_evidence") or {}
    strategy_id = str(card_payload.get("strategy_id") or "")
    prompt_versions = _prompt_versions_dict(cfg) if strategy_id == DEFAULT_STRATEGY_NAME else {}
    return {
        "created_at": now.isoformat(timespec="seconds"),
        "prompts": {"distill_version": cfg.prompts.distill},
        "prompt_versions": prompt_versions,
        "strategy_id": strategy_id,
        "strategy_version": str(card_payload.get("strategy_version") or ""),
        "schema_version": str(card_payload.get("schema_version") or ""),
        "source_content_hash": str(source_evidence.get("content_hash") or ""),
        "profile": cfg.llm.active_profile,
        "model_routing": {
            stage: {
                "model_id": meta["model_alias"],
                "type": meta.get("type") or meta.get("provider_type") or meta["provider"],
                "model": meta["actual_model"],
            }
            for stage, meta in outcome.stages_meta.items()
        },
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


def _compute_card_quality(
    *,
    title: str,
    body: str,
    source_id: str | None = None,
    source_path: str | None = None,
    source_type: str | None = None,
) -> CardQuality | None:
    """计算卡片质量元数据 — try/except 包裹，失败返回 None 不阻塞主线。"""
    try:
        card_type_str = classify_card_type(title, body)
        warnings_tuple = tuple(detect_warnings(body))
        quality = score_quality(
            title=title,
            body=body,
            source_id=source_id,
            source_path=source_path,
            source_type=source_type,
            warnings=warnings_tuple,
            card_type=card_type_str,
        )
        suggestions = generate_suggestions(quality)
        return CardQuality(
            overall_level=quality.overall_level,
            overall_score=quality.overall_score,
            rubric_scores=quality.rubric_scores,
            warnings=quality.warnings,
            card_type=quality.card_type,
            regenerate_suggestion=suggestions.regenerate_suggestion,
            split_candidate=suggestions.split_candidate,
            merge_candidate=suggestions.merge_candidate,
            dedup_candidates=suggestions.dedup_candidates,
        )
    except Exception:
        return None


def _quality_to_dict(quality: CardQuality) -> dict:
    """序列化 CardQuality 为 writer template 可用的纯 dict。"""
    return {
        "overall_score": quality.overall_score,
        "overall_level": quality.overall_level.value,
        "card_type": quality.card_type.value if quality.card_type else "unknown",
        "dimensions": [
            {"name": rs.dimension, "score": rs.score, "max": rs.max_score, "notes": rs.notes}
            for rs in quality.rubric_scores
        ],
        "warnings": [
            {"code": w.code, "severity": w.severity, "message": w.message, "suggestion": w.suggestion}
            for w in quality.warnings
        ],
        "regenerate_suggestion": quality.regenerate_suggestion,
        "split_candidate": quality.split_candidate,
        "merge_candidate": quality.merge_candidate,
    }


def _compute_quality_for_card(
    *,
    card_payload: dict,
    source_id: str | None = None,
    source_path: str | None = None,
    source_type: str | None = None,
) -> dict | None:
    """从 card_payload 提取数据、计算 quality、返回序列化 dict。"""
    try:
        structured = card_payload.get("structured_payload", {})
        card = structured.get("card", {})
        title = str(card.get("title", ""))
        if not title:
            return None

        # 从 card fields 构建近似 body（供 rubric scoring 使用）
        parts: list[str] = []
        excerpt = str(card.get("source_excerpt", ""))
        if excerpt:
            parts.append(f"## Source Excerpt\n{excerpt}")

        bullets = card.get("ai_summary_bullets", []) or []
        if bullets:
            parts.append("## Summary\n" + "\n".join(f"- {b}" for b in bullets))

        inference = card.get("ai_inference_bullets", []) or []
        if inference:
            parts.append("## Details\n" + "\n".join(f"- {b}" for b in inference))

        questions = card.get("review_questions", []) or []
        if questions:
            q_text = "\n".join(f"- {q.get('question', '')}" for q in questions)
            parts.append(f"## Review Questions\n{q_text}")

        principles = card.get("reusable_prompts_or_principles", []) or []
        if principles:
            parts.append("## Details\n" + "\n".join(f"- {p}" for p in principles))

        body = "\n\n".join(parts) if parts else title

        quality = _compute_card_quality(
            title=title,
            body=body,
            source_id=source_id,
            source_path=source_path,
            source_type=source_type,
        )
        if quality is None:
            return None
        return _quality_to_dict(quality)
    except Exception:
        return None


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
        return "failed", _pipeline_failure_message(outcome)

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

    # 计算 quality metadata（确定性评分，无 LLM 调用）
    quality_dict = _compute_quality_for_card(
        card_payload=outcome.card_payload or {},
        source_id=doc.source_id,
        source_path=doc.source_path,
        source_type=doc.source_type,
    )

    wr = writer.write(
        card_payload=outcome.card_payload or {},
        source=item_result.source_dict,
        run=processed_run_dict(cfg=cfg, outcome=outcome, logger=logger, now=now),
        quality=quality_dict,
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


def _pipeline_failure_message(outcome) -> str | None:
    """把 pipeline failed outcome 压成 ingestion summary 可携带的安全错误字符串。

    中文学习型说明：ProcessingRun 只能从 IngestionSummary 读到 tuple[str]。
    如果这里只返回 error_message，Web run detail 会丢失 failed stage；如果
    error_message 为空，又会退化成 errors=1 但没有可行动细节。这里把 stage
    和 message 合并为稳定、可解析的本地诊断，不包含 source 正文或 secret。
    """

    stage = outcome.error_stage
    message = outcome.error_message
    if stage and message:
        return f"{stage}_stage_failed: {message}"
    if stage:
        return f"{stage}_stage_failed"
    return message


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
    "processed_run_dict",
    "source_path_keys",
    "writer_for_runtime",
]
