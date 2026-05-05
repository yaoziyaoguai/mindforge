"""Process Typer adapter.

中文学习型说明：这里保留 process use-case 的副作用编排：RunLogger、
Checkpoint、CardWriter 与 Console 输出。纯资源解析仍在 process_service，
展示文本仍在 process_presenter，strategy 选择仍只来自显式 CLI flag。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import typer

from . import process_presenter as _pp
from .cards import iter_cards
from .checkpoint import Checkpoint
from .cli_runtime import (
    console,
    load_cfg,
    override_active_profile,
    render_active_vault_resolution_notice,
)
from .env_loader import load_dotenv_silently
from .llm import LLMClient, build_providers
from .models import ItemState, StageRecord
from .process_service import summarize_outcome
from .run_logger import EVENT_SOURCE_ERROR, EVENT_STATE_WRITTEN, RunLogger
from .scanner import Scanner
from .strategies import (
    DEFAULT_STRATEGY_NAME,
    NotYetImplementedStrategyError,
    StrategyContext,
    UnknownStrategyError,
    available_strategies,
    build_strategy,
)
from .writer import CardWriter

process_app = typer.Typer(add_completion=False)

# ---------------------------------------------------------------------------
# process — M2 主入口：跑五 stage + 写 Card
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ProcessRuntimeParts:
    """process adapter 的本地运行时对象。

    中文学习型说明：这些对象都带 IO 或外部副作用（scanner/checkpoint/writer/
    provider client），因此保留在 CLI adapter 内部组装；service 层只返回纯
    runtime plan，不直接实例化它们。
    """

    scanner: Scanner
    checkpoint: Checkpoint
    writer: CardWriter
    pipeline: object


@dataclass(frozen=True)
class _ApprovedSourceIndex:
    """已进入 human_approved 知识库的 source provenance 索引。

    中文学习型说明：历史 dogfood 中，老 source 可能仍留在 Inbox，但对应卡片
    已经 human_approved。process 默认不能再把这种 source 当作待处理材料，
    否则会生成 conflict card。这里仅读卡片 frontmatter 白名单，不读 source
    正文，也不移动/删除历史 source。
    """

    source_ids: frozenset[str]
    source_paths: frozenset[str]

    def contains(self, *, source_id: str, source_path: str, vault_root: Path) -> bool:
        if source_id in self.source_ids:
            return True
        return bool(_source_path_keys(source_path, vault_root=vault_root).intersection(self.source_paths))


def _upsert_processing_item(result, cp) -> tuple[object, object]:
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


def _copy_stage_meta_to_item(item, outcome, *, now: datetime) -> None:
    item.status = outcome.status  # type: ignore[assignment]
    item.processed_at = now
    item.error_message = outcome.error_message
    for stage_name, meta in outcome.stages_meta.items():
        item.stages[stage_name] = StageRecord(
            stage=stage_name,  # type: ignore[arg-type]
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


def _emit_skipped_result(*, doc, result, item, item_result, outcome, logger, counts) -> None:
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
    console.print(_pp.format_skipped(
        source_path=doc.source_path, skip_reason=outcome.skip_reason
    ))


def _emit_failed_result(*, doc, result, outcome, logger, counts) -> None:
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
    console.print(_pp.format_failed(
        source_path=doc.source_path,
        error_stage=outcome.error_stage,
        error_message=outcome.error_message,
    ))


def _processed_run_dict(*, cfg, outcome, logger, now: datetime) -> dict[str, object]:
    return {
        "created_at": now.isoformat(timespec="seconds"),
        "prompts": {"distill_version": cfg.prompts.distill},  # type: ignore[attr-defined]
        "profile": cfg.llm.active_profile,  # type: ignore[attr-defined]
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


def _emit_processed_result(
    *,
    doc,
    result,
    item,
    item_result,
    outcome,
    logger,
    writer,
    cfg,
    counts,
    now: datetime,
) -> None:
    counts["processed"] += 1
    item.track = item_result.track
    item.value_score = item_result.value_score
    if item_result.would_write_only:
        console.print(_pp.format_processed_dry_run(
            source_path=doc.source_path,
            target_dir=cfg.vault.cards_path / (item.track or "unrouted"),
        ))
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
        return

    wr = writer.write(
        card_payload=outcome.card_payload or {},
        source=item_result.source_dict,
        run=_processed_run_dict(cfg=cfg, outcome=outcome, logger=logger, now=now),
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
    console.print(_pp.format_processed_real(
        source_path=doc.source_path,
        output_path=wr.path,
        conflict=wr.conflict,
    ))


def _process_one_result(
    *,
    result,
    cp,
    pipeline,
    logger,
    writer,
    cfg,
    console,
    counts,
    dry_run,
):
    """处理单个 scan result 的成功路径。

    架构边界：本函数仍是 cli.py 内部私有 helper，不是新模块。原因：
    - 与 process 命令耦合的本地状态 (cp/pipeline/logger/writer/cfg/console/counts)
      过多，强行抽到独立模块会引入贫血抽象与跨模块状态污染。
    - process_service.py 已被 snapshot caps 锁定（最多 4 个公共函数 / 7 个 dataclass），
      不应继续膨胀；只把纯函数 summarize_outcome 放在那里。
    - 这里的提取目的只是降低 process 函数体行数 / 圈复杂度，让 Typer 命令体保持
      可阅读，并不重组运行时边界。

    时序耦合 (RunLogger.emit / writer.write / console.print / checkpoint 写回)
    保持在 CLI 端，与原实现等价；不引入额外重排。
    """
    doc, item = _upsert_processing_item(result, cp)
    outcome = pipeline.run(doc)
    item_result = summarize_outcome(
        outcome, doc, result.adapter_name, dry_run=dry_run
    )

    now = datetime.now()
    item.last_run_id = logger.run_id
    _copy_stage_meta_to_item(item, outcome, now=now)

    if outcome.status == "skipped":
        _emit_skipped_result(
            doc=doc,
            result=result,
            item=item,
            item_result=item_result,
            outcome=outcome,
            logger=logger,
            counts=counts,
        )
        return

    if outcome.status == "failed":
        _emit_failed_result(
            doc=doc,
            result=result,
            outcome=outcome,
            logger=logger,
            counts=counts,
        )
        return

    _emit_processed_result(
        doc=doc,
        result=result,
        item=item,
        item_result=item_result,
        outcome=outcome,
        logger=logger,
        writer=writer,
        cfg=cfg,
        counts=counts,
        now=now,
    )


def _finalize_process_run(*, cp, cfg, logger, console, counts, dry_run):
    """process 命令收尾：保存 checkpoint + 汇总输出。

    与原实现等价：dry-run 时不写 state.json；非 dry-run 时记录 EVENT_STATE_WRITTEN。
    summary 与 next-hint 仍走 _pp 同一组 presenter，CLI 不做条件分支以外的展示决策。
    """
    if not dry_run:
        cp.save(active_profile=cfg.llm.active_profile)
        logger.emit(
            EVENT_STATE_WRITTEN,
            path=str(cfg.state.state_path),
            items_count=len(list(cp.all_items())),
        )

    console.print(_pp.format_summary(counts))
    for hint in _pp.format_next_hint(counts, vault_root=cfg.vault.root):
        console.print(hint, markup=False)


def _resolve_runtime_or_exit(*, cfg, file, limit, dry_run, prompts_dir, tracks, template):
    from .process_service import (
        ProcessError,
        ProcessRequest,
        resolve_process_runtime,
    )

    runtime_or_err = resolve_process_runtime(
        ProcessRequest(
            cfg=cfg,
            file=file,
            limit=limit,
            dry_run=dry_run,
            prompts_dir=prompts_dir,
            tracks=tracks,
            template=template,
        )
    )
    if isinstance(runtime_or_err, ProcessError):
        console.print(f"[red]✗ {runtime_or_err.message}[/red]")
        raise typer.Exit(code=2)
    return runtime_or_err


def _writer_for_runtime(cfg, runtime) -> CardWriter:
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


def _build_pipeline_or_exit(*, cfg, runtime, strategy: str):
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
    try:
        return build_strategy(strategy, strategy_ctx)
    except NotYetImplementedStrategyError as e:
        console.print(
            f"[yellow]✗ 策略 {strategy!r} 尚未实现（planned / not yet "
            f"implemented）；{e}[/yellow]"
        )
        raise typer.Exit(code=2) from None
    except UnknownStrategyError:
        console.print(
            f"[red]✗ 未知 strategy: {strategy!r}；可选：{available_strategies()}；"
            "运行 `mindforge strategies list` 查看所有策略。[/red]"
        )
        raise typer.Exit(code=2) from None


def _build_process_runtime_parts(*, cfg, runtime, strategy: str) -> _ProcessRuntimeParts:
    return _ProcessRuntimeParts(
        scanner=Scanner(cfg),
        checkpoint=Checkpoint.load(cfg.state.state_path, backup=cfg.state.backup_state),
        writer=_writer_for_runtime(cfg, runtime),
        pipeline=_build_pipeline_or_exit(cfg=cfg, runtime=runtime, strategy=strategy),
    )


def _source_path_keys(source_path: str, *, vault_root: Path) -> set[str]:
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


def _build_approved_source_index(cfg) -> _ApprovedSourceIndex:
    card_scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    source_ids: set[str] = set()
    source_paths: set[str] = set()
    for card in card_scan.cards:
        if card.status != "human_approved":
            continue
        if card.source_id:
            source_ids.add(card.source_id)
        if card.source_path:
            source_paths.update(_source_path_keys(card.source_path, vault_root=cfg.vault.root))
    return _ApprovedSourceIndex(
        source_ids=frozenset(source_ids),
        source_paths=frozenset(source_paths),
    )


def _emit_already_approved_source_skip(*, result, doc, logger, counts) -> None:
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
    console.print(_pp.format_skipped(
        source_path=doc.source_path,
        skip_reason="already_approved",
    ))


def _run_process_loop(*, cfg, parts: _ProcessRuntimeParts, file, limit, dry_run) -> None:
    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}
    attempted = 0
    approved_sources = _build_approved_source_index(cfg)
    with RunLogger(cfg.state.runs_path, command="process") as logger:
        parts.pipeline.logger = logger
        for result in parts.scanner.iter_results():
            if file is not None and Path(result.path).resolve() != file.resolve():
                continue
            counts["seen"] += 1
            if not result.ok:
                counts["failed"] += 1
                logger.emit(
                    EVENT_SOURCE_ERROR,
                    source_type=result.source_type,
                    adapter_name=result.adapter_name,
                    path=str(result.path),
                    error_message=result.error or "",
                )
                continue

            doc = result.document
            assert doc is not None
            if approved_sources.contains(
                source_id=doc.source_id,
                source_path=doc.source_path,
                vault_root=cfg.vault.root,
            ):
                _emit_already_approved_source_skip(
                    result=result,
                    doc=doc,
                    logger=logger,
                    counts=counts,
                )
                continue

            attempted += 1
            _process_one_result(
                result=result,
                cp=parts.checkpoint,
                pipeline=parts.pipeline,
                logger=logger,
                writer=parts.writer,
                cfg=cfg,
                console=console,
                counts=counts,
                dry_run=dry_run,
            )

            if limit is not None and attempted >= limit:
                break

        _finalize_process_run(
            cp=parts.checkpoint,
            cfg=cfg,
            logger=logger,
            console=console,
            counts=counts,
            dry_run=dry_run,
        )


@process_app.command()
def process(
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径",
    ),
    file: Path | None = typer.Option(
        None,
        "--file",
        "-f",
        help="只处理该单文件（绝对或相对 vault 的路径）",
    ),
    limit: int | None = typer.Option(
        None,
        "--limit",
        "-n",
        help="本次最多处理多少条",
    ),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="临时覆盖 llm.active_profile（仅本次进程，不改 yaml）",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="跑完整 pipeline 但不写卡片、不写 state.json；仅 runs/*.jsonl 留痕",
    ),
    prompts_dir: Path | None = typer.Option(
        None,
        "--prompts-dir",
        help="prompts 根目录；未传时使用 package 内置 prompts。",
    ),
    tracks: Path | None = typer.Option(
        None,
        "--tracks",
        help="learning_tracks.yaml 路径；未传时使用 package 内置 learning tracks。",
    ),
    template: Path | None = typer.Option(
        None,
        "--template",
        help="Knowledge Card 模板路径；未传时使用 package 内置模板。",
    ),
    strategy: str = typer.Option(
        DEFAULT_STRATEGY_NAME,
        "--strategy",
        help=(
            "Knowledge strategy 名称（opt-in）。默认沿用 five_stage（LLM 驱动，"
            "通过 fake provider 离线可跑）。可选 default_knowledge_card 走"
            "离线确定性策略。策略选择只依赖此显式选项，绝不从 source/adapter "
            "反推。"
        ),
    ),
) -> None:
    """对 inbox 中已 scan 的文件跑 5 stage pipeline，落地 Knowledge Card。

    硬约束：原始 source 文件不被改写；卡片默认 ``status: ai_draft``，
    必须人工修改 frontmatter 才晋升 ``human_approved``。
    """
    cfg = load_cfg(config, read_env=False)
    cfg = override_active_profile(cfg, profile)
    render_active_vault_resolution_notice(cfg)

    runtime = _resolve_runtime_or_exit(
        cfg=cfg,
        file=file,
        limit=limit,
        dry_run=dry_run,
        prompts_dir=prompts_dir,
        tracks=tracks,
        template=template,
    )

    if runtime.provider.requires_real_env:
        # 中文学习型注释：v0.5.1 把本地 smoke 路径收紧为“不读 .env”。
        # 只有用户显式切到真实 provider 时，才加载 .env 以解析 base_url /
        # api_key 等环境变量；fake provider 必须保持完全离线、无 secret 依赖。
        # v0.7.20：fake-safety 判断已下沉到 process_service.requires_real_env，
        # CLI 只负责实际 IO（load_dotenv），保持 service 无副作用。
        load_dotenv_silently(Path.cwd())
    if dry_run:
        console.print("[yellow]--dry-run：不会写卡片、不会写 state.json[/yellow]")
    console.print(f"active_profile = [bold]{cfg.llm.active_profile}[/bold]")

    parts = _build_process_runtime_parts(cfg=cfg, runtime=runtime, strategy=strategy)
    _run_process_loop(cfg=cfg, parts=parts, file=file, limit=limit, dry_run=dry_run)
