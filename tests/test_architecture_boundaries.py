"""架构边界回归测试：防止纯逻辑模块再次耦合回 cli.py 巨石。

中文学习型说明：
- ``next_suggestions.py`` / ``services/doctor.py`` 是从历史 ``cli.py`` 4900+
  行巨石中拆出来的纯逻辑层；``presenters/doctor.py`` 是 Rich/markup 渲染层。
- 拆分的目的不是"为了减行数而搬运"，而是建立清晰的边界：
    * CLI/Typer 适配层只做参数解析与展示组合；
    * Presenter / console / Rich 渲染只在 cli.py 与 ``presenters/`` 边界出现；
    * ``next_suggestions`` / ``services/doctor`` 这种纯策略只接收配置 +
      文件系统观察事实，返回不可变值对象 / plain-data。
- 一旦再有人把 ``from .cli import …`` 或者 ``console`` / ``typer`` 渗回纯逻辑
  层，本测试就会红，提醒立刻挡回去。
- presenter 允许 import ``rich``，但不允许反向依赖 cli 或 service 业务逻辑。
"""

from __future__ import annotations

import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge"
PURE_LOGIC_MODULES = [
    _SRC / "next_suggestions.py",
    _SRC / "services" / "doctor.py",
]
PRESENTER_MODULES = [
    _SRC / "presenters" / "doctor.py",
]


def _import_lines(path: Path) -> list[str]:
    """只回 import / from 语句源码行，避免把 docstring 中的字符串误判成 import。"""

    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                lines.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = "." * node.level
            names = ", ".join(alias.name for alias in node.names)
            lines.append(f"from {level}{module} import {names}")
    return lines


def test_pure_logic_modules_do_not_import_cli_or_ui_stack() -> None:
    """纯逻辑模块禁止反向依赖 ``cli`` / Typer / Rich console / presenter。"""

    for module in PURE_LOGIC_MODULES:
        imports = _import_lines(module)
        joined = "\n".join(imports)
        assert "mindforge.cli" not in joined, f"{module.name}:\n{joined}"
        assert "from .cli" not in joined, f"{module.name}:\n{joined}"
        assert "from ..cli" not in joined, f"{module.name}:\n{joined}"
        for forbidden in ("typer", "rich", ".console_io", "..console_io", "presenters"):
            assert forbidden not in joined, (
                f"{forbidden!r} 不应出现在 {module.name} 的 import 中：\n{joined}"
            )


def test_next_suggestions_anchored_on_config_contract() -> None:
    """显式锚定纯逻辑层依赖的唯一上游契约：``MindForgeConfig``。"""

    imports = _import_lines(_SRC / "next_suggestions.py")
    assert any(
        "from .config" in line and "MindForgeConfig" in line for line in imports
    ), imports


def test_doctor_service_anchored_on_config_contract() -> None:
    """``services/doctor.py`` 必须以 ``MindForgeConfig`` 为唯一配置入口。"""

    imports = _import_lines(_SRC / "services" / "doctor.py")
    assert any(
        "from ..config" in line and "MindForgeConfig" in line for line in imports
    ), imports


def test_presenter_modules_do_not_import_cli_or_services() -> None:
    """presenter 不允许反向依赖 cli 或 service：它只翻译 plain-data。"""

    for module in PRESENTER_MODULES:
        imports = _import_lines(module)
        joined = "\n".join(imports)
        for forbidden in (
            "mindforge.cli",
            "from .cli",
            "from ..cli",
            "from ..services",
            "from .services",
            "typer",
        ):
            assert forbidden not in joined, (
                f"{forbidden!r} 不应出现在 {module.name} 的 import 中：\n{joined}"
            )
