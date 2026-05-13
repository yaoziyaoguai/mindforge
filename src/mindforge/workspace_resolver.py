"""统一 workspace / config 解析，让用户只需理解 workspace，无需每天关心 config file path。

中文学习型说明：MindForge CLI 可在任意目录运行。本模块提供统一解析入口：
从显式 --config/--workspace → cwd 向上查找 → 全局 active workspace 的优先级链，
最后找不到时给出友好的可操作错误提示。

全局 active workspace 文件 ``~/.mindforge/current_workspace.json`` 只保存
workspace path、config path 和 updated_at；不写入 API key、token 或任何 secret。
secret 永远只属于 local secret store (``.mindforge/secrets.json``) 或 env var，
不进入全局配置。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_ACTIVE_WORKSPACE_DIR = Path.home() / ".mindforge"
_ACTIVE_WORKSPACE_FILE = _ACTIVE_WORKSPACE_DIR / "current_workspace.json"
_DEFAULT_CONFIG_RELATIVE = Path("configs") / "mindforge.yaml"


@dataclass(frozen=True)
class ActiveWorkspace:
    """全局 active workspace 的只读快照；不包含 secret。"""

    workspace_path: Path
    config_path: Path
    updated_at: str

    @property
    def exists(self) -> bool:
        """active workspace 路径和 config 都仍然存在。"""
        return self.workspace_path.is_dir() and self.config_path.is_file()

    def to_dict(self) -> dict[str, str]:
        return {
            "workspace_path": str(self.workspace_path),
            "config_path": str(self.config_path),
            "updated_at": self.updated_at,
        }


def get_active_workspace() -> ActiveWorkspace | None:
    """读取全局 active workspace 指针；不访问 secret。"""
    if not _ACTIVE_WORKSPACE_FILE.is_file():
        return None
    try:
        data = json.loads(_ACTIVE_WORKSPACE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    workspace_path = data.get("workspace_path")
    config_path = data.get("config_path")
    if not workspace_path or not config_path:
        return None
    return ActiveWorkspace(
        workspace_path=Path(str(workspace_path)),
        config_path=Path(str(config_path)),
        updated_at=str(data.get("updated_at", "")),
    )


def set_active_workspace(workspace_path: Path) -> ActiveWorkspace:
    """把 workspace 设为全局 active workspace。

    校验：workspace 必须包含 configs/mindforge.yaml 且 vault.root 合法。
    不读取 secret value，不调用 LLM，不修改 workspace 数据。
    """
    ws = workspace_path.expanduser().resolve()
    config_path = ws / _DEFAULT_CONFIG_RELATIVE

    if not config_path.is_file():
        raise WorkspaceResolutionError(
            kind="invalid_workspace",
            message=(
                f"不是有效的 MindForge workspace：{ws}\n"
                f"缺少 {_DEFAULT_CONFIG_RELATIVE}\n"
                "请确认路径正确，或运行 mindforge init 创建新 workspace。"
            ),
        )

    # 校验 vault.root 合法（只读 yaml，不读 secret）
    try:
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        vault = data.get("vault")
        if isinstance(vault, dict):
            vault_root = vault.get("root")
            if not vault_root or not isinstance(vault_root, str):
                raise WorkspaceResolutionError(
                    kind="invalid_workspace",
                    message=f"配置中缺少 vault.root：{config_path}",
                )
    except ImportError:
        pass  # 不应发生；yaml 是核心依赖
    except Exception as exc:
        raise WorkspaceResolutionError(
            kind="invalid_workspace",
            message=f"无法读取配置：{config_path}\n{exc}",
        ) from exc

    _ACTIVE_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    active = ActiveWorkspace(
        workspace_path=ws,
        config_path=config_path,
        updated_at=_now(),
    )
    _write_active_workspace(active)
    return active


def clear_active_workspace() -> None:
    """清除全局 active workspace 指针；不删除任何 workspace 数据。"""
    try:
        _ACTIVE_WORKSPACE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def global_workspace_override() -> Path | None:
    """读取 CLI 入口设置的 workspace override（--workspace）。"""
    override = os.environ.get("MINDFORGE_WORKSPACE_OVERRIDE")
    if not override:
        return None
    return Path(override)


def resolve_workspace_config(
    config_path: Path,
    *,
    workspace_override: Path | None = None,
    cwd: Path | None = None,
) -> Path:
    """按统一优先级解析 config 路径。

    优先级：
    1. 显式 --config（非默认值，且文件存在）
    2. 显式 --workspace → <workspace>/configs/mindforge.yaml
    3. 从当前目录向上查找 configs/mindforge.yaml
    4. 全局 active workspace（~/.mindforge/current_workspace.json）
    5. 友好错误提示
    """
    current = (cwd or Path.cwd()).expanduser().resolve()

    # 将相对 config_path 按 cwd 解析为绝对路径
    resolved_explicit = config_path.expanduser()
    if not resolved_explicit.is_absolute():
        resolved_explicit = current / resolved_explicit

    is_default_path = (config_path == _DEFAULT_CONFIG_RELATIVE)

    # 1) 显式 --config 如果文件存在，直接使用
    # 当 --workspace 也提供了，默认 config_path 的 cwd 解析不应抢占
    # workspace 路径，否则用户显式指定的 workspace 会被 cwd 的 config 覆盖。
    if not is_default_path or workspace_override is None:
        if resolved_explicit.is_file():
            return resolved_explicit.resolve()

    # 非默认路径且文件不存在 → 显式指定的 config 不存在，不应 fallback
    if not is_default_path:
        raise WorkspaceResolutionError(
            kind="missing_config",
            message=f"配置文件不存在：{resolved_explicit}",
        )

    # 2) 显式 --workspace
    if workspace_override is not None:
        ws = workspace_override.expanduser().resolve()
        derived = ws / _DEFAULT_CONFIG_RELATIVE
        if derived.is_file():
            return derived
        raise WorkspaceResolutionError(
            kind="missing_config",
            message=(
                f"指定的 workspace 中未找到配置：{derived}\n"
                f"请确认 {ws} 是 MindForge workspace（含 configs/mindforge.yaml）。"
            ),
        )

    # 3) 向上查找（仅默认路径）
    from .app_context import find_project_root

    project_root = find_project_root(current)
    if project_root is not None:
        found = project_root / _DEFAULT_CONFIG_RELATIVE
        if found.is_file():
            return found

    # 4) 全局 active workspace
    active = get_active_workspace()
    if active is not None:
        if active.exists:
            return active.config_path
        # active workspace 路径失效 — 提示用户重新设置
        raise WorkspaceResolutionError(
            kind="stale_workspace",
            message=(
                f"Active workspace 不再可用：{active.workspace_path}\n"
                f"config 文件不存在：{active.config_path}\n"
                "请重新设置：mindforge workspace use <path>"
            ),
        )

    # 5) 友好错误提示
    raise WorkspaceResolutionError(
        kind="no_workspace",
        message=_friendly_no_workspace_message(),
    )


def _friendly_no_workspace_message() -> str:
    return (
        "当前目录不是 MindForge workspace，也没有可用 active workspace。\n"
        "\n"
        "你可以：\n"
        "1. 创建新 workspace：\n"
        "   mindforge init\n"
        "\n"
        "2. 切换到已有 workspace：\n"
        "   mindforge workspace use /path/to/workspace\n"
        "\n"
        "3. 临时指定 workspace：\n"
        "   mindforge status --workspace /path/to/workspace\n"
        "\n"
        "4. 高级方式指定配置：\n"
        "   mindforge status --config /path/to/configs/mindforge.yaml"
    )


class WorkspaceResolutionError(ValueError):
    """workspace/config 解析失败的结构化错误。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


def _write_active_workspace(active: ActiveWorkspace) -> None:
    """写入全局 active workspace 文件；不写入 secret。"""
    _ACTIVE_WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    payload = active.to_dict()
    tmp = _ACTIVE_WORKSPACE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(_ACTIVE_WORKSPACE_FILE)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


__all__ = [
    "ActiveWorkspace",
    "WorkspaceResolutionError",
    "get_active_workspace",
    "set_active_workspace",
    "clear_active_workspace",
    "global_workspace_override",
    "resolve_workspace_config",
]
