"""版本一致性边界测试 — 防止 ``__version__`` / ``pyproject.toml`` 静默漂移。

历史背景：v0.7.22 关闭 Architecture Quality Milestone 时发现，
``src/mindforge/__init__.py`` 的 ``__version__`` 字面量长期停留在 ``0.7.19``，
而 ``pyproject.toml`` 已升至 ``0.7.22``。``mindforge --version`` /
``mindforge commands`` / ``mindforge doctor`` 三个用户可见入口因此对外
报告了错误的版本号。

本文件用最小、纯只读的 fitness function 锁住三条不可漂移的事实：

1. 包级 ``__version__`` 必须等于 ``pyproject.toml`` 中 ``[project].version``。
2. ``importlib.metadata.version("mindforge")`` 必须等于 ``__version__``
   （即 distribution metadata 与运行时常量同源）。
3. ``__init__.py`` 中的后备字面量必须与 ``pyproject.toml`` 一致 —— 即使
   importlib.metadata 失败，回退路径也不会报告错误版本。

这是边界保护，不是行为测试。它**只读**仓库源码，不启动 CLI，不联网。
"""

from __future__ import annotations

import ast
import importlib.metadata
import re
import sys
import tomllib
from pathlib import Path

import mindforge

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
INIT_FILE = REPO_ROOT / "src" / "mindforge" / "__init__.py"


def _pyproject_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["version"]


def _fallback_literal() -> str:
    """从 ``__init__.py`` AST 中取出 except 分支里的字面量。

    我们不通过 import 触发 except 分支（在已安装的 venv 里走不到），
    而是用 AST 静态读取，这样无论运行环境是否安装 distribution 都能校验。
    """
    tree = ast.parse(INIT_FILE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__version__"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise AssertionError("__init__.py 缺少后备 __version__ 字面量")


def test_runtime_version_matches_pyproject() -> None:
    assert mindforge.__version__ == _pyproject_version(), (
        "mindforge.__version__ 与 pyproject.toml 不一致，"
        "用户可见的 mindforge --version 将报告错误版本"
    )


def test_distribution_metadata_matches_runtime_version() -> None:
    metadata_version = importlib.metadata.version("mindforge")
    assert metadata_version == mindforge.__version__, (
        "importlib.metadata 报告的版本与 mindforge.__version__ 不一致，"
        "通常意味着需要重新执行 `pip install -e .`"
    )


def test_fallback_literal_matches_pyproject() -> None:
    assert _fallback_literal() == _pyproject_version(), (
        "__init__.py 的后备 __version__ 字面量未跟随 pyproject.toml 更新；"
        "在未安装为 distribution 的环境（如某些打包检查路径）下会报告错误版本"
    )


def test_pyproject_version_is_pep440_like() -> None:
    """轻量 sanity check：版本号至少形如 ``MAJOR.MINOR.PATCH``。"""

    pattern = r"^\d+\.\d+\.\d+([a-zA-Z0-9.+\-]*)?$"
    assert re.match(pattern, _pyproject_version()), (
        f"pyproject 版本号格式异常：{_pyproject_version()!r}"
    )


def test_python_version_is_supported() -> None:
    """与 pyproject 声明的 ``requires-python = '>=3.11'`` 对齐的最小校验。"""

    assert sys.version_info >= (3, 11), "MindForge 要求 Python 3.11+"
