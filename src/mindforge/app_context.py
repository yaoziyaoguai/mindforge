"""CLI 可复用的 config / path resolution helper。

中文学习型说明：AppContext 层只做"把用户给的 config path 解析成本次命令可用
的本地路径集合"。它不做 recall/approve/review/Obsidian 业务判断，不依赖
Typer/Rich，不读取 `.env`，也不调用 LLM。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .config import ConfigError, MindForgeConfig, load_mindforge_config


class AppContextError(ValueError):
    """config/path resolution 的结构化错误，由 CLI 决定如何展示。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class AppPaths:
    config_path: Path
    vault_root: Path
    inbox_path: Path
    cards_path: Path
    projects_path: Path
    state_workdir: Path
    runs_path: Path


@dataclass(frozen=True)
class AppContext:
    config: MindForgeConfig
    paths: AppPaths


def load_app_config(config_path: Path, *, vault_override: Path | None = None) -> MindForgeConfig:
    """加载 config 并应用本次命令的 vault override；不读 `.env`。

    中文学习型说明：是否加载 `.env` 仍由 CLI 入口显式决定。这里保持纯
    config/path resolution，避免 service/context 层悄悄改变 provider 环境。
    """
    if not config_path.exists():
        raise AppContextError("missing_config", f"配置文件不存在：{config_path}")
    try:
        cfg = load_mindforge_config(config_path)
    except ConfigError as e:
        raise AppContextError("invalid_config", str(e)) from e
    return apply_vault_override(cfg, vault_override)


def build_app_context(config_path: Path, *, vault_override: Path | None = None) -> AppContext:
    """构建 console-independent AppContext；不创建目录、不写文件。"""
    cfg = load_app_config(config_path, vault_override=vault_override)
    return AppContext(
        config=cfg,
        paths=AppPaths(
            config_path=config_path,
            vault_root=cfg.vault.root,
            inbox_path=cfg.vault.inbox_path,
            cards_path=cfg.vault.cards_path,
            projects_path=cfg.vault.projects_path,
            state_workdir=cfg.state.workdir,
            runs_path=cfg.state.runs_path,
        ),
    )


def apply_vault_override(cfg: MindForgeConfig, vault_override: Path | None) -> MindForgeConfig:
    """只覆盖 vault.root，不修改 yaml，也不改变 cards_dir 等相对目录字段。"""
    if vault_override is None:
        return cfg
    new_vault = replace(cfg.vault, root=vault_override.expanduser().resolve())
    return replace(cfg, vault=new_vault)
