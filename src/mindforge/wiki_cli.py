"""Wiki CLI —— 查看 Main Wiki 状态和内容。

v0.5: Wiki rebuild（LLM synthesis / deterministic template）已废弃。
Wiki 现在是 runtime View，通过 TopicPresenter 动态生成。
旧 `mindforge wiki rebuild` 入口已移除。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, load_cfg, render_active_vault_resolution_notice
from .wiki_service import (
    get_wiki_status,
    read_main_wiki,
)

wiki_app = typer.Typer(
    add_completion=False,
    help="管理 Main Wiki。Wiki 是只读派生视图，由 TopicPresenter 动态生成。",
)


@wiki_app.command("rebuild", hidden=True)
def wiki_rebuild(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    mode: str = typer.Option(
        "",
        "--mode",
        hidden=True,
    ),
) -> None:
    """(Deprecated) Wiki rebuild 已在 v0.5 废弃。Wiki 现在是 runtime View。"""
    cfg = load_cfg(config, read_env=False)
    render_active_vault_resolution_notice(cfg)

    console.print(
        "[yellow]Wiki rebuild 已在 v0.5 废弃。[/yellow]\n"
        "Wiki 现在是 runtime View，不再通过 LLM synthesis 或 deterministic template 生成持久化 Markdown。\n"
        "请使用 TopicPresenter（CLI: mindforge topic view <name> / Web: GET /api/topics/{name}）获取知识视图。"
    )
    raise typer.Exit(code=0)


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
