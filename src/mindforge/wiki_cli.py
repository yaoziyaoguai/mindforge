"""Wiki CLI —— 从 approved cards 生成和维护 Main Wiki。

中文学习型说明：CLI 只调用 WikiService，不直接操作文件。
Wiki 是 approved cards 的派生视图。LLM mode 只负责内容合成，
provenance 由代码追加，不读取 source 原文。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .wiki_service import (
    WikiError,
    get_wiki_status,
    llm_rebuild_wiki,
    read_main_wiki,
    rebuild_main_wiki,
)

wiki_app = typer.Typer(
    add_completion=False,
    help="管理 Main Wiki。Wiki 从 approved knowledge cards 生成，是只读派生视图。",
)


@wiki_app.command("rebuild")
def wiki_rebuild(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    mode: str = typer.Option("", "--mode", help="重建模式：deterministic | llm。默认使用 config wiki.mode。"),
) -> None:
    """从所有 approved cards 重建 Main Wiki。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    effective_mode = mode.strip() if mode.strip() else cfg.wiki.mode

    if effective_mode == "llm":
        try:
            result = llm_rebuild_wiki(cfg)
            console.print("[green]Wiki rebuilt (LLM synthesis).[/green]")
            console.print(f"  Path: {result.wiki_path}")
            console.print(f"  Cards included: {result.included_cards}")
            console.print(f"  Sections: {result.section_count}")
            console.print(f"  Additional cards: {result.additional_cards}")
            console.print(f"  Model: {result.model_id}")
            for w in result.warnings:
                console.print(f"  [yellow]Warning: {w}[/yellow]")
            console.print("[dim]Wiki is a derived view. Source files are not affected.[/dim]")
        except WikiError as e:
            console.print(f"[red]LLM rebuild failed: {e}[/red]")
            raise typer.Exit(code=1)
    elif effective_mode == "deterministic":
        result = rebuild_main_wiki(cfg)
        console.print("[green]Wiki rebuilt (deterministic).[/green]")
        console.print(f"  Path: {result.wiki_path}")
        console.print(f"  Cards included: {result.included_cards}")
        console.print(f"  Last rebuilt: {result.last_rebuilt_at}")
        console.print("[dim]Wiki is a derived view. Source files are not affected.[/dim]")
    else:
        console.print(f"[red]Unknown mode: {effective_mode!r}. Use deterministic or llm.[/red]")
        raise typer.Exit(code=1)


@wiki_app.command("show")
def wiki_show(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """显示当前 Main Wiki 内容（只读）。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    content = read_main_wiki(cfg)
    if content is None:
        console.print("[yellow]Wiki 不存在。运行 mindforge wiki rebuild 来生成。[/yellow]")
        raise typer.Exit(code=0)

    console.print(content, markup=False)


@wiki_app.command("status")
def wiki_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
) -> None:
    """显示 Main Wiki 状态摘要。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    status = get_wiki_status(cfg)
    console.print("[bold]Wiki status[/bold]")
    console.print(f"  Path: {status.wiki_path}")
    console.print(f"  Exists: {'yes' if status.exists else 'no'}")
    if status.exists:
        console.print(f"  Last rebuilt: {status.last_rebuilt_at}")
        console.print(f"  Cards in Wiki: {status.wiki_card_count}")
    console.print(f"  Approved cards available: {status.approved_card_count}")
    if not status.exists:
        console.print("\n[yellow]Wiki 不存在。运行 mindforge wiki rebuild 来生成。[/yellow]")
    elif status.approved_card_count != status.wiki_card_count:
        console.print("\n[yellow]Wiki may be out of date. Run mindforge wiki rebuild to refresh.[/yellow]")
