"""Runtime asset resolution for packaged installs.

中文学习型说明
================

v0.5.1 的 CLI 默认从仓库根读取 ``prompts/``、``templates/`` 和
``configs/learning_tracks.yaml``。这在 editable checkout 中可用，但 wheel
安装后仓库根并不存在。v0.5.2 把默认运行时资产放进 package，并用
``importlib.resources`` 解析：

- 用户显式传入路径时，永远优先使用用户路径；
- 用户未传时，使用包内默认资产；
- 需要真实文件系统路径的调用方通过 ``as_file`` 临时拿到 Path，并在命令
  执行期间保持上下文存活；
- 不改变 SourceAdapter / SourceDocument / processor / approval / recall
  架构，只修正默认资产定位。
"""

from __future__ import annotations

import atexit
from contextlib import ExitStack
from importlib.resources import as_file, files
from pathlib import Path
from typing import Final

ASSET_PACKAGE: Final[str] = "mindforge.assets"
_GLOBAL_ASSET_STACK = ExitStack()
atexit.register(_GLOBAL_ASSET_STACK.close)


def asset_root():
    """Return the package resource root as an importlib Traversable."""
    return files(ASSET_PACKAGE)


def bundled_asset_path(stack: ExitStack, *parts: str) -> Path:
    """Return a filesystem Path for a bundled asset during ``stack`` lifetime."""
    resource = asset_root().joinpath(*parts)
    return stack.enter_context(as_file(resource))


def bundled_asset_path_for_process(*parts: str) -> Path:
    """Return a process-lifetime filesystem Path for bundled assets.

    Some legacy code paths, notably ``mindforge init``, still copy files via
    ``Path.read_bytes``. A process-lifetime context keeps extracted package
    resources alive until CLI exit without leaking into user data directories.
    """
    return bundled_asset_path(_GLOBAL_ASSET_STACK, *parts)


def bundled_text(*parts: str) -> str:
    """Read a bundled UTF-8 text resource without assuming a repo checkout."""
    return asset_root().joinpath(*parts).read_text(encoding="utf-8")


def resolve_user_or_bundled_path(
    stack: ExitStack,
    user_path: Path | None,
    *asset_parts: str,
) -> Path:
    """Resolve explicit user path first, otherwise a bundled package asset."""
    if user_path is not None:
        return user_path.expanduser()
    return bundled_asset_path(stack, *asset_parts)


__all__ = [
    "asset_root",
    "bundled_asset_path",
    "bundled_asset_path_for_process",
    "bundled_text",
    "resolve_user_or_bundled_path",
]
