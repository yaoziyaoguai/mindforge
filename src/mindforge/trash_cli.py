"""Knowledge Card Trash CLI。

中文学习型说明：CLI 只是 trash_service 的参数边界，不直接操作文件。
所有 path validation / move / restore 逻辑均在 trash_service 层，
CLI 只负责解析参数、调用 service、输出安全 summary。
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .trash_service import (
    TrashError,
    list_trashed_cards,
    move_card_to_trash,
    read_trashed_card,
    restore_trashed_card,
)

trash_app = typer.Typer(
    add_completion=False,
    help="管理 Trash 中的 Knowledge Card。Trash 只移动卡片，不删除 source 文件。",
)


@trash_app.command("list")
def trash_list(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """列出 Trash 中所有卡片的安全摘要。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)
    cards = list_trashed_cards(cfg)
    if not cards:
        console.print("[dim]Trash 为空。[/dim]")
        return

    table = Table(title="Trash", show_lines=False)
    table.add_column("path", overflow="fold")
    table.add_column("title")
    table.add_column("previous_status")
    table.add_column("trashed_at")
    for c in cards:
        table.add_row(
            c.trash_rel_path,
            c.title or "(untitled)",
            c.previous_status,
            c.trashed_at[:16] if c.trashed_at else "-",
        )
    console.print(table)


@trash_app.command("show")
def trash_show(
    trash_path: str = typer.Argument(..., help="Trash 中卡片的相对路径（从 trash list 获取）"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """查看 Trash 中单张卡片的 metadata 和正文预览。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    try:
        result = read_trashed_card(cfg, trash_path)
    except TrashError as exc:
        console.print(f"[red]错误：{exc}[/red]")
        raise typer.Exit(code=1)

    if result is None:
        console.print(f"[red]Trash 中未找到：{trash_path}[/red]")
        raise typer.Exit(code=1)

    fm, body = result
    console.print(f"[bold]Title:[/bold] {fm.get('title', '(untitled)')}")
    console.print(f"[bold]Previous status:[/bold] {fm.get('previous_status', '?')}")
    console.print(f"[bold]Trashed at:[/bold] {fm.get('trashed_at', '?')}")
    console.print(f"[bold]Original path:[/bold] {fm.get('original_path', '?')}")
    console.print(f"[bold]Track:[/bold] {fm.get('track', '-')}")
    tags = fm.get("tags", [])
    if isinstance(tags, list) and tags:
        console.print(f"[bold]Tags:[/bold] {', '.join(str(t) for t in tags)}")
    if body:
        preview = body[:500] + ("..." if len(body) > 500 else "")
        console.print("\n[bold]Body preview:[/bold]")
        console.print(preview, markup=False)


@trash_app.command("restore")
def trash_restore(
    trash_path: str = typer.Argument(..., help="Trash 中卡片的相对路径"),
    confirm: bool = typer.Option(False, "--confirm", help="显式确认 restore 操作"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """从 Trash 恢复卡片到 Review 或 Library。

    Restore 将卡片移回原路径并恢复 previous_status。
    不删除 source 文件，不覆盖已有卡片。
    """
    if not confirm:
        console.print("[yellow]restore 需要 --confirm 显式确认。[/yellow]")
        console.print("此操作将卡片从 Trash 移回原路径，不删除 source 文件。")
        raise typer.Exit(code=1)

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    try:
        result = restore_trashed_card(cfg, trash_path)
        console.print(f"[green]Card restored: {result.title}[/green]")
        console.print(f"  Restored path: {result.restored_path}")
        console.print(f"  Previous status: {result.previous_status}")
        if result.conflict_resolved:
            console.print("[yellow]  Conflict resolved: original path was occupied, safe filename used.[/yellow]")
    except TrashError as exc:
        console.print(f"[red]错误：{exc}[/red]")
        raise typer.Exit(code=1)


@trash_app.command("move")
def trash_move(
    card_path: str = typer.Argument(..., help="Knowledge Card 的文件路径"),
    confirm: bool = typer.Option(False, "--confirm", help="显式确认 move to trash 操作"),
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """将 Knowledge Card 移到 Trash。

    只移动卡片 .md 文件，不删除 source 原文。
    适用于 ai_draft 和 human_approved 卡片。
    """
    if not confirm:
        console.print("[yellow]move to trash 需要 --confirm 显式确认。[/yellow]")
        console.print("此操作只移动 Knowledge Card 到 Trash，不删除 source 文件。")
        console.print("Restore: mindforge trash restore <path> --confirm")
        raise typer.Exit(code=1)

    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    try:
        result = move_card_to_trash(cfg, Path(card_path))
        console.print(f"[green]Card moved to Trash: {result.title}[/green]")
        console.print(f"  Previous status: {result.previous_status}")
        console.print(f"  Trash path: {result.trash_rel_path}")
        console.print("  Source file 未被删除。Restore: mindforge trash restore <path> --confirm")
    except TrashError as exc:
        console.print(f"[red]错误：{exc}[/red]")
        raise typer.Exit(code=1)
