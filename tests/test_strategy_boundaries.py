"""KnowledgeStrategy seam AST 边界测试 — 静态守护策略层的反向依赖与禁飞。

设计意图（与其他 ``*_boundaries.py`` 同构但有意不共享 fixture）：

- 策略层是 process use-case 的内层；它**不**应该感知 CLI / Typer / Rich /
  RunLogger 实例 / dotenv / Obsidian 写入 / 真实 LLM provider；
- 策略 registry 必须保持稳定的公开 API（建立 fitness function，避免后续
  改动悄悄改变可被外部扩展的入口面）；
- 策略 seam 不允许"人话输出"——它只是组合层，所有 console / Rich 输出
  都应该回到 CLI 或 presenter 层。

学习提示：本文件的每条断言都对应一个具体的 Phase 1 安全/边界承诺。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PKG_ROOT = Path(__file__).resolve().parent.parent / "src" / "mindforge"
STRATEGIES_DIR = PKG_ROOT / "strategies"


def _load_module_source(name: str) -> str:
    return (STRATEGIES_DIR / name).read_text(encoding="utf-8")


def _imports(source: str) -> list[str]:
    """收集模块顶层与函数体内的所有 import 名。"""

    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            base = "." * node.level + node.module
            names.append(base)
            for alias in node.names:
                names.append(f"{base}.{alias.name}")
    return names


_MODULES = ["__init__.py", "base.py", "five_stage.py", "registry.py"]


@pytest.mark.parametrize("module", _MODULES)
def test_strategy_module_does_not_import_typer(module: str) -> None:
    src = _load_module_source(module)
    imports = _imports(src)
    assert not any("typer" in name.lower() for name in imports), (
        f"{module} 不应导入 Typer：策略 seam 是 use-case 内层，CLI 框架"
        f"细节必须留在 cli.py / obsidian_cli.py。实际 imports: {imports}"
    )


@pytest.mark.parametrize("module", _MODULES)
def test_strategy_module_does_not_import_rich(module: str) -> None:
    src = _load_module_source(module)
    imports = _imports(src)
    assert not any("rich" in name.lower() for name in imports), (
        f"{module} 不应导入 Rich：策略层不输出人话，所有 console / 渲染"
        f"必须回到 presenter 层。实际 imports: {imports}"
    )


@pytest.mark.parametrize("module", _MODULES)
def test_strategy_module_does_not_import_dotenv(module: str) -> None:
    src = _load_module_source(module)
    imports = _imports(src)
    assert not any("dotenv" in name.lower() for name in imports), (
        f"{module} 不应导入 dotenv：``.env`` 加载只走 env_loader，"
        f"策略层不允许触碰真实环境变量。实际 imports: {imports}"
    )


@pytest.mark.parametrize("module", _MODULES)
def test_strategy_module_does_not_import_run_logger_module(module: str) -> None:
    """策略层只把 ``RunLogger | None`` 作为 ``TYPE_CHECKING`` 注解使用。

    运行时 import RunLogger 模块会让策略层与 CLI 的事件总线发生编译期
    耦合 —— 而当前唯一持有 RunLogger 的是 CLI 的组合根。本测试允许在
    ``TYPE_CHECKING`` 下的 ``from ..run_logger import RunLogger``，但不
    允许任何顶层（非 TYPE_CHECKING 块）的 import。
    """

    src = _load_module_source(module)
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.If):
            test = node.test
            if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
                continue
        if isinstance(node, ast.ImportFrom) and node.module == "run_logger":
            pytest.fail(
                f"{module} 顶层 import RunLogger，运行时耦合泄漏；"
                f"应放入 if TYPE_CHECKING 块"
            )


def test_strategy_init_reexports_protocol_and_factory() -> None:
    src = _load_module_source("__init__.py")
    tree = ast.parse(src)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level >= 1:
            for alias in node.names:
                names.add(alias.asname or alias.name)
        # v0.12 Slice 4 Green：``build_strategy`` 在 package 层从纯 re-export
        # 演化为薄包装函数（仍委派给 :func:`registry.build_strategy`，新增
        # ``custom_path`` 关键字以便 preview-only 友好分流）。语义契约
        # 不变 —— 名字仍由 ``mindforge.strategies`` 公开导出 ——
        # 因此这里把"模块顶层 def / class / 赋值"也视为合法的公开导出
        # 证据，避免把"实现策略"误绑死成"必须 import 别人"。
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    must_export = {
        "KnowledgeStrategy",
        "StrategyContext",
        "build_strategy",
        "DEFAULT_STRATEGY_NAME",
    }
    missing = must_export - names
    assert not missing, (
        f"strategies/__init__.py 缺失公开 re-export：{missing}；"
        f"这些是被 CLI / 测试依赖的稳定入口面"
    )


def test_strategy_init_all_matches_reexports() -> None:
    src = _load_module_source("__init__.py")
    tree = ast.parse(src)
    all_value: list[str] | None = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "__all__"
            and isinstance(node.value, (ast.List, ast.Tuple))
        ):
            all_value = [
                elt.value
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            break
    assert all_value is not None, "strategies/__init__.py 必须显式声明 __all__"
    for name in (
        "KnowledgeStrategy",
        "StrategyContext",
        "build_strategy",
        "DEFAULT_STRATEGY_NAME",
        "build_five_stage_strategy",
        "available_strategies",
        "UnknownStrategyError",
    ):
        assert name in all_value, f"__all__ 缺少 {name}"


def test_registry_does_not_silently_fallback_on_unknown_name() -> None:
    """registry 不允许返回 None / 默认策略来掩盖未知名字。

    用 AST 检查 ``build_strategy`` 函数体里必须存在 ``raise`` 语句，
    防止后续重构悄悄把 ``raise`` 改成 ``return _FACTORIES[default]``。
    """

    src = _load_module_source("registry.py")
    tree = ast.parse(src)
    target: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "build_strategy":
            target = node
            break
    assert target is not None, "registry.py 必须定义 build_strategy"
    has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(target))
    assert has_raise, "build_strategy 必须 raise UnknownStrategyError，不能静默回退"


def test_five_stage_factory_only_wraps_pipeline_not_reimplements() -> None:
    """``five_stage.py`` 必须只是 ``Pipeline`` 的薄包装。

    通过 AST 检查模块里没有任何自己实现的"五段调用"循环 / stage 字符串
    字面量，避免未来不小心把 pipeline 逻辑复制进策略层造成双源。
    """

    src = _load_module_source("five_stage.py")
    tree = ast.parse(src)
    forbidden_stage_names = {"triage", "distill", "link_suggestion", "review_questions", "action_extraction"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value not in forbidden_stage_names, (
                f"five_stage.py 不应直接出现 stage 字符串字面量 {node.value!r}；"
                f"五段调用必须保留在 processors/pipeline.py 唯一一份"
            )


def test_strategy_layer_does_not_reach_into_cli_or_presenters() -> None:
    """策略层不允许反向 import CLI / presenter / approval_service / writer。

    用模块名最后一段（last component）做整词比较，避免把 ``LLMClient``
    误判为含 ``cli``。
    """

    forbidden_components = {
        "cli",
        "obsidian_cli",
        "approve_presenter",
        "review_presenter",
        "recall_presenter",
        "approval_service",
        "review_service",
        "writer",
    }
    for module in _MODULES:
        src = _load_module_source(module)
        for name in _imports(src):
            last = name.rsplit(".", 1)[-1]
            assert last not in forbidden_components, (
                f"{module} import 触及禁飞模块 {name!r}（last={last!r}）；"
                f"策略层只能依赖 processors / llm / sources / run_logger(类型)"
            )
