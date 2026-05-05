"""Library CLI adapter."""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg
from .library_presenter import (
    render_library_detail,
    render_library_list,
    render_library_stats,
)
from .library_service import build_library_inventory, show_library_card

library_app = typer.Typer(
    add_completion=False,
    invoke_without_command=True,
    help="查看本地 Knowledge Library 的只读 inventory，不读取 source 正文。",
)


@library_app.callback(invoke_without_command=True)
def library(
    ctx: typer.Context,
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """默认显示 library stats。"""
    if ctx.invoked_subcommand is not None:
        return
    cfg = load_cfg(config, read_env=False)
    render_library_stats(console, build_library_inventory(cfg).stats)


@library_app.command("stats")
def library_stats(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """显示知识库统计摘要。"""
    cfg = load_cfg(config, read_env=False)
    render_library_stats(console, build_library_inventory(cfg).stats)


@library_app.command("list")
def library_list(
    limit: int = typer.Option(200, "--limit", min=1),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """列出卡片安全 metadata；默认不显示正文。"""
    cfg = load_cfg(config, read_env=False)
    render_library_list(console, build_library_inventory(cfg, limit=limit))


@library_app.command("show")
def library_show(
    card: str = typer.Argument(..., help="card id、文件名、绝对路径或 vault-relative path"),
    show_content: bool = typer.Option(
        False,
        "--show-content",
        help="显式展示 card body；仍不展示 source 正文。",
    ),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """查看单张卡片 metadata；正文需显式 --show-content。"""
    cfg = load_cfg(config, read_env=False)
    result = show_library_card(cfg, card, show_content=show_content)
    if hasattr(result, "exit_code"):
        console.print(f"[red]{result.message}[/red]")  # type: ignore[attr-defined]
        raise typer.Exit(code=result.exit_code)  # type: ignore[attr-defined]
    render_library_detail(console, result)  # type: ignore[arg-type]


__all__ = ["library_app"]
