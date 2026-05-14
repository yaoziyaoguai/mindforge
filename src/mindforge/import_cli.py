"""One-shot import CLI for simple ingestion."""

from __future__ import annotations

from pathlib import Path

import typer
from .cli_runtime import (
    apply_provider_selection,
    console,
    load_cfg,
    render_active_vault_resolution_notice,
    resolve_source_path_for_cli,
)
from .cli_processing_runtime import config_path_from_cfg, start_cli_processing_run
from .strategy_selection import StrategySelectionError, resolve_strategy_selection


def import_cmd(
    target: Path = typer.Argument(..., help="一次性导入的文件或文件夹"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        hidden=True,
        help="Internal compatibility option.",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        hidden=True,
        help="Internal compatibility option.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "--no-triage",
        help=(
            "显式覆盖 triage 低分拦截并生成 ai_draft；"
            "不会绕过 already_processed / already_approved。"
        ),
    ),
    strategy: str | None = typer.Option(
        None,
        "--strategy",
        help="临时覆盖 strategy.active；只影响本次 import，不修改 YAML。",
    ),
) -> None:
    """一次性导入 source，并启动后台 processing。"""

    cfg = load_cfg(config, read_env=False)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)
    render_active_vault_resolution_notice(cfg)
    try:
        selected_strategy = resolve_strategy_selection(cfg, explicit_strategy=strategy)
    except StrategySelectionError as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc
    console.print(
        f"active strategy: {selected_strategy.strategy_id} ({selected_strategy.source})",
        markup=False,
    )
    source_path = resolve_source_path_for_cli(cfg, target)
    run = start_cli_processing_run(
        cfg,
        config_path=config_path_from_cfg(cfg, config),
        source_ref=str(source_path.resolve()),
        source_path=source_path,
        mode="import",
        worker_args=[
            "--mode",
            "import",
            "--target",
            str(source_path.resolve()),
            *(["--provider", provider] if provider else []),
            *(["--profile", profile] if profile else []),
            *([] if not force else ["--force"]),
            *([] if selected_strategy.strategy_id is None else ["--strategy", selected_strategy.strategy_id]),
        ],
    )
    console.print("[bold]Source import registered[/bold]")
    console.print(f"target: {source_path}", markup=False, soft_wrap=True)
    console.print("Registry: not added to watched sources.", markup=False)
    console.print("Boundary: generated cards remain ai_draft until explicit approve --confirm.", markup=False)
    _print_background_run_hint(run.record.run_id, reused_existing=run.reused_existing)


def _print_background_run_hint(run_id: str, *, reused_existing: bool = False) -> None:
    """CLI import 主路径只启动后台 run，不同步等待 pipeline。"""

    if reused_existing:
        console.print("Background processing is already active.", markup=False)
    else:
        console.print("Background processing started.", markup=False)
    console.print(f"run_id: {run_id}", markup=False)
    console.print("You can continue using MindForge.", markup=False)
    console.print(f"Check progress: mindforge runs show {run_id}", markup=False)
    console.print("Or: mindforge status", markup=False)
    console.print("Drafts appear in: mindforge approve list after processing succeeds.", markup=False)
    console.print(
        "If model setup is incomplete, this run will fail with next actions; retry after setup is fixed.",
        markup=False,
        soft_wrap=True,
    )

__all__ = ["import_cmd"]
