"""Process Typer adapter.

中文学习型说明：这里保留 process use-case 的副作用编排：RunLogger、
Checkpoint、CardWriter 与 Console 输出。纯资源解析仍在 process_service，
展示文本仍在 process_presenter，strategy 选择仍只来自显式 CLI flag。
"""
from __future__ import annotations

from pathlib import Path

import typer

from . import process_presenter as _pp
from .cli_runtime import (
    apply_provider_selection,
    console,
    load_cfg,
    render_active_vault_resolution_notice,
)
from .env_loader import load_dotenv_silently
from .ingestion_diagnostics import print_provider_failure, provider_failure_detail
from .llm.base import ProviderError
from .process_executor import (
    ProcessRuntimeParts,
    build_approved_source_index,
    build_process_runtime_parts,
    emit_already_approved_source_skip,
    emit_source_error,
    finalize_process_run,
    process_one_result,
)
from .run_logger import RunLogger
from .strategies import (
    DEFAULT_STRATEGY_NAME,
    NotYetImplementedStrategyError,
    UnknownStrategyError,
    available_strategies,
)

process_app = typer.Typer(add_completion=False)

# ---------------------------------------------------------------------------
# process — M2 主入口：跑五 stage + 写 Card
# ---------------------------------------------------------------------------


def _format_process_status(result, *, cfg, status: str, message: str | None, dry_run: bool) -> None:
    doc = result.document
    assert doc is not None
    if status == "skipped":
        console.print(_pp.format_skipped(source_path=doc.source_path, skip_reason=message))
    elif status == "failed":
        console.print(_pp.format_failed(source_path=doc.source_path, error_stage=None, error_message=message))
    elif dry_run and status == "processed":
        console.print(_pp.format_processed_dry_run(source_path=doc.source_path, target_dir=cfg.vault.cards_path))
    else:
        console.print(_pp.format_processed_real(
            source_path=doc.source_path,
            output_path=Path(message or ""),
            conflict=(status == "conflict"),
        ))


def _finalize_process_run(*, cp, cfg, logger, console, counts, dry_run):
    """process 命令收尾：保存 checkpoint + 汇总输出。

    与原实现等价：dry-run 时不写 state.json；非 dry-run 时记录 EVENT_STATE_WRITTEN。
    summary 与 next-hint 仍走 _pp 同一组 presenter，CLI 不做条件分支以外的展示决策。
    """
    finalize_process_run(cp=cp, cfg=cfg, logger=logger, counts=counts, dry_run=dry_run)

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


def _build_process_runtime_parts(*, cfg, runtime, strategy: str) -> ProcessRuntimeParts:
    try:
        return build_process_runtime_parts(cfg=cfg, runtime=runtime, strategy=strategy)
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
    except ProviderError as exc:
        # 中文学习型说明：process 是 advanced/troubleshooting，但 provider
        # 选择语义仍与 watch/import 一致。这里仅展示 selected provider 的
        # 诊断，不 fallback fake，也不打印 env value / prompt / source 正文。
        print_provider_failure(console, provider_failure_detail(cfg, str(exc)))
        raise typer.Exit(code=2) from None


def _run_process_loop(*, cfg, parts: ProcessRuntimeParts, file, limit, dry_run) -> None:
    counts = {"processed": 0, "skipped": 0, "failed": 0, "seen": 0}
    attempted = 0
    approved_sources = build_approved_source_index(cfg)
    with RunLogger(cfg.state.runs_path, command="process") as logger:
        parts.pipeline.logger = logger
        for result in parts.scanner.iter_results():
            if file is not None and Path(result.path).resolve() != file.resolve():
                continue
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
                console.print(_pp.format_skipped(
                    source_path=doc.source_path,
                    skip_reason="already_approved",
                ))
                continue

            attempted += 1
            status, message = process_one_result(
                result=result,
                cp=parts.checkpoint,
                pipeline=parts.pipeline,
                logger=logger,
                writer=parts.writer,
                cfg=cfg,
                counts=counts,
                dry_run=dry_run,
            )
            _format_process_status(
                result,
                cfg=cfg,
                status=status,
                message=message,
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
        help="Legacy alias for --provider；临时覆盖 provider（仅本次进程，不改 yaml）",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="高级临时覆盖 llm.active 指向的 provider（仅本次进程，不改 yaml）",
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
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)
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
