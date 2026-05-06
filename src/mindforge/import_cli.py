"""One-shot import CLI for simple ingestion."""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import (
    apply_provider_selection,
    console,
    load_cfg,
    render_active_vault_resolution_notice,
)
from .env_loader import load_dotenv_silently
from .ingestion_service import import_sources
from .process_service import FAKE_PROFILE


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
) -> None:
    """一次性处理当前内容，不加入 watched source registry。"""

    cfg = load_cfg(config, read_env=False)
    cfg = apply_provider_selection(cfg, provider=provider, legacy_profile=profile)
    render_active_vault_resolution_notice(cfg)
    if cfg.llm.active_profile != FAKE_PROFILE:
        # CLI adapter 是读取 .env 的边界；service 只编排 ingestion，不持有 IO 副作用。
        load_dotenv_silently(Path.cwd())
    try:
        summary = import_sources(cfg, target)
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
    if summary.counts.get("skipped", 0):
        console.print("skipped reasons may include already_processed or already_approved.", markup=False)
    console.print("Registry: not added to watched sources.", markup=False)
    console.print("Next: mindforge approve list", markup=False)
    console.print("Boundary: generated cards remain ai_draft until explicit approve --confirm.", markup=False)


__all__ = ["import_cmd"]
