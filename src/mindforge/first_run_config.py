"""First-run local config bootstrap for `mindforge web`.

中文学习型说明：`configs/mindforge.yaml` 是每台机器的 runtime config，不能
提交到 Git。clean clone 只有 `configs/mindforge_example.yaml`，因此 Web
首次启动需要生成一份无 secret、无模型、无 legacy profile 的本地配置，让用户
进入 Setup 后再显式添加模型和 API key。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .app_context import find_project_root


DEFAULT_CONFIG_PATH = Path("configs/mindforge.yaml")


@dataclass(frozen=True)
class LocalConfigBootstrapResult:
    created: bool
    config_path: Path | None
    workspace_root: Path | None
    message: str | None = None


def maybe_bootstrap_local_config(
    config_path: Path,
    *,
    cwd: Path | None = None,
    allow_unmarked_workspace: bool = False,
) -> LocalConfigBootstrapResult:
    """Create a safe local runtime config for a clean-clone Web workspace.

    只在明确识别到 MindForge workspace root 时创建，避免用户从任意错误目录
    运行 `mindforge web` 时被写入 `configs/mindforge.yaml`。

    中文学习型说明：`allow_unmarked_workspace` 只给显式 `mindforge web
    --workspace /path` 使用。此时用户已经给出了工作区根目录，允许空目录首次
    初始化；默认路径仍要求 repo/workspace 标记，防止错误 cwd 被静默写入。
    """

    base_cwd = (cwd or Path.cwd()).expanduser().resolve()
    requested = config_path.expanduser()
    workspace_root = _workspace_root_for_config(
        requested,
        cwd=base_cwd,
        allow_unmarked_workspace=allow_unmarked_workspace,
    )
    if workspace_root is None:
        return LocalConfigBootstrapResult(
            created=False,
            config_path=None,
            workspace_root=None,
            message=(
                "Run from a MindForge workspace, or pass --workspace /path/to/mindforge. "
                "No local config was created."
            ),
        )

    target = _target_config_path(requested, workspace_root, cwd=base_cwd)
    if target.exists():
        return LocalConfigBootstrapResult(
            created=False,
            config_path=target,
            workspace_root=workspace_root,
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_safe_first_run_config(), encoding="utf-8")
    return LocalConfigBootstrapResult(
        created=True,
        config_path=target,
        workspace_root=workspace_root,
        message="Created local config at configs/mindforge.yaml from safe defaults.",
    )


def _workspace_root_for_config(
    config_path: Path,
    *,
    cwd: Path,
    allow_unmarked_workspace: bool = False,
) -> Path | None:
    if config_path == DEFAULT_CONFIG_PATH:
        project_root = find_project_root(cwd)
        if project_root is not None and _is_mindforge_workspace(project_root):
            return project_root
        return None

    absolute = config_path if config_path.is_absolute() else (cwd / config_path)
    if absolute.name == "mindforge.yaml" and absolute.parent.name == "configs":
        candidate = absolute.parent.parent.resolve()
        if _is_mindforge_workspace(candidate) or allow_unmarked_workspace:
            return candidate
    return None


def _target_config_path(config_path: Path, workspace_root: Path, *, cwd: Path) -> Path:
    if config_path == DEFAULT_CONFIG_PATH:
        return workspace_root / DEFAULT_CONFIG_PATH
    return config_path if config_path.is_absolute() else (cwd / config_path)


def _is_mindforge_workspace(path: Path) -> bool:
    return (
        (path / "configs" / "mindforge_example.yaml").is_file()
        or (
            (path / "pyproject.toml").is_file()
            and (path / "src" / "mindforge").is_dir()
        )
    )


def _safe_first_run_config() -> str:
    return """# MindForge local runtime config.
#
# Created automatically by `mindforge web` on first run.
# This file is local-only and gitignored. Do not commit it.
# API keys are stored by Web Setup in .mindforge/secrets.json, not in YAML.

version: 0.7

vault:
  root: "vault"

llm:
  default_model: null
  models: {}
  routing: {}

wiki:
  # mode 为 deprecated/compatibility 字段。Web UI 不暴露 mode 选择器，
  # 统一走 LLM synthesis 主路径。此处的 deterministic 是安全回退默认值，
  # 确保无模型时不会错误触发 LLM 调用。
  mode: deterministic
  model: null
  auto_rebuild_on_approve: false

telemetry:
  enabled: true
  local_only: true
"""


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "LocalConfigBootstrapResult",
    "maybe_bootstrap_local_config",
]
