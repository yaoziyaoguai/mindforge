"""Workspace CLI adapter.

中文学习型说明：workspace 是用户需要理解的唯一 product concept。
configs/mindforge.yaml 是 workspace 内部实现细节，CLI 自动解析。
用户只需 ``mindforge workspace use <path>`` 一次，之后在任意目录
执行 status/web/runs/approve/library/recall/wiki/watch/import 都能
自动找到 active workspace。

全局 active workspace 文件 ``~/.mindforge/current_workspace.json``
只保存 workspace path、config path、updated_at；不包含 API key/token/secret。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, global_vault_override
from .presenters.local_status import (
    render_friendly_error,
    render_status_json,
    render_workspace_status,
)
from .services.local_status import build_local_status_snapshot, friendly_config_error
from .workspace_resolver import (
    WorkspaceResolutionError,
    clear_active_workspace,
    get_active_workspace,
    set_active_workspace,
)

workspace_app = typer.Typer(
    add_completion=False,
    help="管理 MindForge workspace。workspace 是产品核心概念，config 是它内部的实现细节。",
)


@workspace_app.command("current")
def workspace_current(
    as_json: bool = typer.Option(False, "--json", help="输出机器可读 JSON。"),
) -> None:
    """查看当前 active workspace 路径、config 路径和 vault 信息。

    不显示 API key、token 或任何 secret。
    """
    active = get_active_workspace()
    if active is None:
        if as_json:
            import json as _json

            print(
                _json.dumps(
                    {"active_workspace": None, "hint": "mindforge workspace use <path>"},
                    ensure_ascii=False,
                )
            )
            return
        console.print("[yellow]没有 active workspace。[/yellow]")
        console.print("设置 active workspace：[bold]mindforge workspace use <path>[/bold]")
        console.print("创建新 workspace：[bold]mindforge init[/bold]")
        return

    workspace_exists = active.workspace_path.is_dir()
    config_exists = active.config_path.is_file()

    if as_json:
        import json as _json

        print(
            _json.dumps(
                {
                    "active_workspace": str(active.workspace_path),
                    "config_path": str(active.config_path),
                    "workspace_exists": workspace_exists,
                    "config_exists": config_exists,
                    "updated_at": active.updated_at,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    console.print("[bold]Active Workspace[/bold]")
    console.print(f"  workspace : {active.workspace_path}")
    console.print(f"  config    : {active.config_path}")
    console.print(f"  updated   : {active.updated_at}")

    if not workspace_exists:
        console.print("  [red]✗ workspace 路径不存在[/red]")
        console.print("  重新设置：[bold]mindforge workspace use <path>[/bold]")
        return
    if not config_exists:
        console.print("  [red]✗ config 文件不存在[/red]")
        console.print("  重新设置：[bold]mindforge workspace use <path>[/bold]")
        return

    # 读取 vault 路径（不读 secret）
    try:
        import yaml

        data = yaml.safe_load(active.config_path.read_text(encoding="utf-8")) or {}
        vault = data.get("vault")
        if isinstance(vault, dict):
            vault_root = vault.get("root", "(未设置)")
            console.print(f"  vault     : {vault_root}")
    except Exception:
        pass

    console.print("  [green]✓ active workspace 可用[/green]")


@workspace_app.command("use")
def workspace_use(
    path: Path = typer.Argument(..., help="workspace 根路径（含 configs/mindforge.yaml）"),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="高级覆盖：直接指定 config 路径（而非 workspace 根路径）。",
    ),
) -> None:
    """设置全局 active workspace。之后可在任意目录运行 MindForge 命令。

    校验：path/configs/mindforge.yaml 必须存在，vault.root 必须合法。
    不读取 API key / token / secret。
    """
    # 支持直接指定 config 路径（高级模式）
    if config != Path("configs/mindforge.yaml"):
        # 用户显式传了 --config：设置 workspace path 为 config 文件所在目录的父目录
        cfg_path = config.expanduser().resolve()
        if not cfg_path.is_file():
            console.print(f"[red]✗ config 文件不存在：{cfg_path}[/red]")
            raise typer.Exit(code=2)
        if cfg_path.name == "mindforge.yaml" and cfg_path.parent.name == "configs":
            ws = cfg_path.parent.parent
        else:
            ws = cfg_path.parent
    else:
        ws = path.expanduser().resolve()

    try:
        active = set_active_workspace(ws)
    except WorkspaceResolutionError as exc:
        console.print(f"[red]✗ {exc}[/red]")
        raise typer.Exit(code=2) from exc

    console.print(f"[green]✓ active workspace 已设置为[/green] {active.workspace_path}")
    console.print(f"  config : {active.config_path}")
    console.print("  [dim]现在可以在任意目录运行 mindforge status / web 等命令。[/dim]")


@workspace_app.command("clear")
def workspace_clear(
    confirm: bool = typer.Option(
        False,
        "--confirm",
        help="显式确认清除 active workspace 指针。",
    ),
) -> None:
    """清除全局 active workspace 指针。

    只删除 ~/.mindforge/current_workspace.json 中的指针，
    不删除任何 workspace 数据或 vault 文件。
    """
    active = get_active_workspace()
    if active is None:
        console.print("当前没有 active workspace，无需清除。")
        return

    console.print(f"当前 active workspace：[bold]{active.workspace_path}[/bold]")
    if not confirm:
        console.print("加 [bold]--confirm[/bold] 确认清除（不删除任何 workspace 数据）。")
        return

    clear_active_workspace()
    console.print("[green]✓ active workspace 已清除。[/green]")
    console.print("  [dim]workspace 数据完整保留，未受影响。[/dim]")
    console.print("  重新设置：[bold]mindforge workspace use <path>[/bold]")


# 保留旧的 workspace status 作为兼容别名
@workspace_app.command("status", hidden=True)
def workspace_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    as_json: bool = typer.Option(False, "--json", help="输出机器可读 JSON。"),
) -> None:
    """查看 workspace/source/vault 状态；不读取 source 正文，不写 state。"""
    from .app_context import AppContextError

    try:
        snapshot = build_local_status_snapshot(
            config,
            vault_override=global_vault_override(),
            cwd=Path.cwd(),
        )
    except AppContextError as exc:
        render_friendly_error(console, friendly_config_error(config, str(exc)))
        raise typer.Exit(code=2) from exc
    if as_json:
        render_status_json(snapshot)
        return
    render_workspace_status(console, snapshot)


__all__ = ["workspace_app"]
