"""One-shot import CLI for simple ingestion."""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .ingestion_service import import_sources


def import_cmd(
    target: Path = typer.Argument(..., help="一次性导入的文件或文件夹"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """一次性处理当前内容，不加入 watched source registry。"""

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    summary = import_sources(cfg, target)
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
