"""CLI adapter runtime helpers.

中文学习型说明：这里是 Typer adapter 层的共享运行时边界，只放所有 CLI
命令都必须共用的入口能力：Console、配置加载、全局 vault override、
profile override 与 argv 归一化。它不是业务 ``utils/common`` 垃圾桶；
source / strategy / service / presenter 层都不应依赖本模块。
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import typer
from rich.console import Console

from .app_context import AppContextError, load_app_config
from .config import MindForgeConfig
from .env_loader import load_dotenv_silently

console = Console()


def global_vault_override() -> Path | None:
    """读取 CLI 入口设置的 vault override；不读取 `.env` 文件。"""
    import os as _os

    override = _os.environ.get("MINDFORGE_VAULT_OVERRIDE")
    if not override:
        return None
    return Path(override)


def load_cfg(config_path: Path, *, read_env: bool = True) -> MindForgeConfig:
    """CLI adapter 的统一配置入口。

    只有用户显式走需要真实 provider env 的 CLI 路径时才允许 ``read_env=True``；
    fake/safe 路径必须传 ``read_env=False``，从而保持 no API key required。
    """

    if read_env:
        load_dotenv_silently(Path.cwd())
    try:
        return load_app_config(config_path, vault_override=global_vault_override())
    except AppContextError as e:
        if e.kind == "missing_config":
            console.print(f"[red]✗ 配置文件不存在：{config_path}[/red]")
            console.print(
                "[dim]提示：可以从仓库中的 configs/mindforge.yaml 复制一份到目标位置，"
                "再用 --config 指定，或直接在仓库根运行命令。[/dim]"
            )
            raise typer.Exit(code=2) from e
        console.print(f"[red]✗ 配置错误：{e}[/red]")
        console.print(
            "[dim]提示：请检查 vault.root、sources.enabled、llm.active_profile "
            "三个字段是否合法。[/dim]"
        )
        raise typer.Exit(code=2) from e


def override_active_profile(
    cfg: MindForgeConfig, profile: str | None
) -> MindForgeConfig:
    """如果 CLI 传了 --profile，就基于现有 cfg 派生一份临时 LLMConfig。"""

    if not profile:
        return cfg
    if profile not in cfg.llm.profiles:
        console.print(
            f"[red]--profile {profile!r} 不在 llm.profiles 中；"
            f"已知：{sorted(cfg.llm.profiles)}[/red]"
        )
        raise typer.Exit(code=2)
    new_llm = replace(cfg.llm, active_profile=profile)
    return replace(cfg, llm=new_llm)


_COMMANDS_WITH_LOCAL_VAULT_OPTION = {"init", "obsidian", "setup"}


def normalize_post_command_global_options(argv: list[str]) -> list[str]:
    """把后置 ``--vault`` 归一化为 Typer 全局参数位置。

    ``init`` / ``obsidian`` / ``config init`` 拥有自己的局部 ``--vault``
    语义，不能搬动；其他命令的 ``--vault`` 表示全局 vault override。
    """

    if len(argv) < 3:
        return argv

    option_takes_value = {"--config", "-c", "--vault", "--obsidian-vault"}
    command_idx: int | None = None
    i = 1
    while i < len(argv):
        token = argv[i]
        if token == "--":
            return argv
        if token.startswith("-"):
            if token in option_takes_value and i + 1 < len(argv):
                i += 2
                continue
            i += 1
            continue
        command_idx = i
        break

    if command_idx is None:
        return argv
    nested_command = next(
        (a for a in argv[command_idx + 1:] if not a.startswith("-")),
        "",
    )
    if (
        argv[command_idx] in _COMMANDS_WITH_LOCAL_VAULT_OPTION
        or (argv[command_idx] == "config" and nested_command == "init")
    ):
        return argv

    moved: list[str] = []
    rest: list[str] = []
    i = 1
    while i < len(argv):
        token = argv[i]
        if i > command_idx and token == "--vault" and i + 1 < len(argv):
            moved.extend([token, argv[i + 1]])
            i += 2
            continue
        if i > command_idx and token.startswith("--vault="):
            moved.extend(["--vault", token.split("=", 1)[1]])
            i += 1
            continue
        rest.append(token)
        i += 1

    if not moved:
        return argv
    return [argv[0], *moved, *rest]
