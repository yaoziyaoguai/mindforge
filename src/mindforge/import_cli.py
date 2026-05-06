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
from .env_loader import load_dotenv_silently
from .ingestion_diagnostics import print_ingestion_diagnostics
from .ingestion_service import import_sources
from .process_service import FAKE_PROFILE
from .strategy_selection import StrategySelectionError, resolve_strategy_selection


def import_cmd(
    target: Path = typer.Argument(..., help="一次性导入的文件或文件夹"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    profile: str | None = typer.Option(
        None,
        "--profile",
        "-p",
        help="Legacy alias for --provider；临时覆盖 provider，不修改 YAML。",
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="高级临时覆盖 llm.active 指向的 provider（不修改 YAML）。",
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
    """一次性处理当前内容，不加入 watched source registry。"""

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
    if cfg.llm.active_profile != FAKE_PROFILE and selected_strategy.metadata.provider_mode != "deterministic":
        # CLI adapter 是读取 .env 的边界；service 只编排 ingestion，不持有 IO 副作用。
        load_dotenv_silently(Path.cwd())
    try:
        summary = import_sources(
            cfg,
            source_path,
            bypass_triage_gate=force,
            strategy=selected_strategy,
        )
    except RuntimeError as exc:
        console.print(str(exc), markup=False, soft_wrap=True)
        raise typer.Exit(code=2) from exc
    console.print("[bold]imported[/bold]")
    console.print(f"target: {summary.target}", markup=False, soft_wrap=True)
    console.print(
        "processed={processed} skipped={skipped} failed={failed} seen={seen}".format(
            processed=summary.counts.get("processed", 0),
            skipped=summary.counts.get("skipped", 0),
            failed=summary.counts.get("failed", 0),
            seen=summary.counts.get("seen", 0),
        ),
        markup=False,
    )
    print_ingestion_diagnostics(console, summary)
    console.print("Registry: not added to watched sources.", markup=False)
    console.print("Next: mindforge approve list", markup=False)
    console.print("Boundary: generated cards remain ai_draft until explicit approve --confirm.", markup=False)

__all__ = ["import_cmd"]
