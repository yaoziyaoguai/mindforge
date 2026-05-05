"""Workspace CLI adapter.

中文学习型说明：`mindforge workspace status` 是真实本地数据的只读入口。
本模块只处理 Typer 参数和 presenter 调用；状态编排在
`services.local_status`，避免 root `cli.py` 扩成新的业务巨石。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .app_context import AppContextError
from .cli_runtime import console, global_vault_override
from .presenters.local_status import (
    render_friendly_error,
    render_status_json,
    render_workspace_status,
)
from .services.local_status import build_local_status_snapshot, friendly_config_error

workspace_app = typer.Typer(add_completion=False, help="真实本地 workspace/vault 只读状态。")


@workspace_app.command("status")
def workspace_status(
    config: Path = typer.Option(Path("configs/mindforge.yaml"), "--config", "-c"),
    as_json: bool = typer.Option(False, "--json", help="输出机器可读 JSON。"),
) -> None:
    """查看 workspace/source/vault 状态；不读取 source 正文，不写 state。"""

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
