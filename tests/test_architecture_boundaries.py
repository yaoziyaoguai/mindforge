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


# ---------------------------------------------------------------------------
# v2.0 分层架构边界测试
# 中文学习型说明：验证 Data / Policy / Adapter / Service / CLI / Web 六层
# 之间的 import 方向不违反分层规则。规则定义在 docs/dev/architecture-map.md。
# ---------------------------------------------------------------------------

_WEB_SRC = Path(__file__).resolve().parents[1] / "src" / "mindforge_web"

# Data Layer（只能 import stdlib、yaml）
DATA_MODULES = [
    _SRC / "cards.py",
    _SRC / "models.py",
    _SRC / "checkpoint.py",
]

# Policy Layer（不能 import Service / CLI / Web）
POLICY_MODULES = [
    _SRC / "safety_policy.py",
    _SRC / "input_safety.py",
    _SRC / "obsidian_manifest_policy.py",
    _SRC / "provider_readiness.py",
]

# 核心 Service 模块（不能 import CLI / Web）
CORE_SERVICE_MODULES = [
    _SRC / "approval_service.py",
    _SRC / "review_service.py",
    _SRC / "library_service.py",
    _SRC / "recall_service.py",
    _SRC / "lexical_index.py",
    _SRC / "card_workspace_service.py",
    _SRC / "trash_service.py",
    _SRC / "relations" / "graph_builder.py",
    _SRC / "relations" / "community.py",
    _SRC / "relations" / "related_cards.py",
    _SRC / "relations" / "scoring.py",
    _SRC / "relations" / "discovery_context.py",
    _SRC / "health" / "health_service.py",
]

# Adapter 模块（不能 import Service）
ADAPTER_MODULES = [
    _SRC / "llm" / "fake.py",
    _SRC / "obsidian_stage.py",
    _SRC / "obsidian_workflow.py",
    _SRC / "cubox_readiness.py",
]

# Fake provider 绝不可 import 真实 provider
FAKE_PROVIDER = _SRC / "llm" / "fake.py"
REAL_PROVIDER_NAMES = ["openai_compatible", "anthropic_compatible"]


def _import_modules(path: Path) -> set[str]:
    """返回该文件所有 import 的模块名集合（仅 mindforge.* 和 mindforge_web.*）。"""
    imports = _import_lines(path)
    modules: set[str] = set()
    for line in imports:
        if "mindforge" in line:
            modules.add(line.strip())
    return modules


def test_core_service_modules_do_not_import_web() -> None:
    """核心 Service 层不得 import mindforge_web（Web 可 import Service，反之不可）。"""
    for module in CORE_SERVICE_MODULES:
        if not module.exists():
            continue
        all_imports = _import_modules(module)
        web_imports = [i for i in all_imports if "mindforge_web" in i]
        assert not web_imports, (
            f"{module.name} 违反分层规则：Service 层 import 了 Web 模块：\n"
            + "\n".join(web_imports)
        )


def test_policy_modules_do_not_import_service_or_cli() -> None:
    """Policy 层不得 import 业务 Service 或 CLI 或 Web。"""
    for module in POLICY_MODULES:
        if not module.exists():
            continue
        all_imports = _import_modules(module)
        for forbidden_pattern in ("_service", "_cli", "mindforge_web", "cli."):
            violations = [i for i in all_imports if forbidden_pattern in i]
            assert not violations, (
                f"{module.name} 违反分层规则：Policy 层 import 了 {forbidden_pattern}：\n"
                + "\n".join(violations)
            )


def test_adapter_modules_do_not_import_service() -> None:
    """Adapter 层不得 import 业务 Service。"""
    for module in ADAPTER_MODULES:
        if not module.exists():
            continue
        all_imports = _import_modules(module)
        service_imports = [i for i in all_imports if "_service" in i and "mindforge" in i]
        assert not service_imports, (
            f"{module.name} 违反分层规则：Adapter 层 import 了 Service：\n"
            + "\n".join(service_imports)
        )


def test_fake_provider_does_not_import_real_providers() -> None:
    """Fake provider 绝不可依赖真实 provider 模块。"""
    imports = _import_modules(FAKE_PROVIDER)
    joined = "\n".join(imports)
    for name in REAL_PROVIDER_NAMES:
        assert name not in joined, (
            f"Fake provider 不应 import {name}（真实 provider）。"
            f" 这会让 fake = default 安全边界失效。"
        )


def test_data_modules_do_not_import_service_or_cli() -> None:
    """Data 层只应依赖 stdlib / yaml，不得 import 业务 Service / CLI。"""
    for module in DATA_MODULES:
        if not module.exists():
            continue
        all_imports = _import_modules(module)
        violations = [i for i in all_imports if "mindforge" in i and "_service" in i]
        assert not violations, (
            f"{module.name} 违反分层规则：Data 层 import 了 Service：\n"
            + "\n".join(violations)
        )
