"""`mindforge web` CLI adapter.

中文学习型说明：本模块只负责 CLI 参数、启动 server 和安全摘要提示。
FastAPI app/router/facade 都在 `mindforge_web`，避免把 Web server 逻辑塞回
root `cli.py`。
"""

from __future__ import annotations

from pathlib import Path

import typer

from .cli_runtime import console, global_vault_override
from .first_run_config import DEFAULT_CONFIG_PATH, maybe_bootstrap_local_config


def web(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="绑定地址；默认 127.0.0.1，MindForge Web 不应默认对外暴露。",
    ),
    port: int = typer.Option(8765, "--port", min=1, max=65535, help="本地端口。"),
    open_browser: bool = typer.Option(False, "--open", help="启动后打开浏览器。"),
    no_open: bool = typer.Option(False, "--no-open", help="显式不打开浏览器（smoke/CI 友好）。"),
    vault: Path | None = typer.Option(
        None,
        "--vault",
        help="临时覆盖配置中的 vault.root（不修改 yaml）。",
    ),
    config: Path = typer.Option(
        Path("configs/mindforge.yaml"),
        "--config",
        "-c",
        help="mindforge.yaml 路径。",
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        "-w",
        help=(
            "工作区根路径。自动推导 --config 为 <workspace>/configs/mindforge.yaml、"
            "--vault 为 <workspace>/vault。explicit --config / --vault 优先覆盖。"
        ),
    ),
) -> None:
    """启动 MindForge Local Console。"""

    should_open = open_browser and not no_open

    # --workspace 推导 config / vault（explicit --config / --vault 优先）
    if workspace is not None:
        ws = workspace.expanduser().resolve()
        if config == Path("configs/mindforge.yaml"):  # 默认值，未显式设置
            config = ws / "configs" / "mindforge.yaml"
        if vault is None:  # 未显式设置
            vault = ws / "vault"

    effective_vault = vault or global_vault_override()
    bootstrap = maybe_bootstrap_local_config(config)
    if bootstrap.config_path is None and not config.expanduser().exists():
        console.print(
            "[red]Run from a MindForge workspace, or pass --workspace /path/to/mindforge.[/red]"
        )
        console.print(
            "[dim]No local configs/mindforge.yaml was created because no workspace root was found.[/dim]"
        )
        raise typer.Exit(code=2)
    if bootstrap.config_path is not None and config == DEFAULT_CONFIG_PATH:
        config = bootstrap.config_path
    if bootstrap.created and bootstrap.message:
        console.print(f"[green]{bootstrap.message}[/green]")

    if host not in {"127.0.0.1", "localhost"}:
        console.print(
            "[yellow]Warning: MindForge Web is designed as a single-user local console.[/yellow]"
        )
    console.print("[bold]MindForge Local Console[/bold]")
    console.print(f"URL       : http://{host}:{port}")
    console.print(f"host      : {host}")
    console.print(f"vault     : {effective_vault if effective_vault else '(from config)'}")
    console.print("safety    : local-first; approval requires explicit confirmation")
    from mindforge_web.server import run_server

    run_server(
        host=host,
        port=port,
        open_browser=should_open,
        config_path=config,
        vault_override=effective_vault,
    )
