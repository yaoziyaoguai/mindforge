"""v0.12 Innovation #1 — Custom strategy import-boundary architecture tests.

灵感来源：OpenAI Agents SDK 的 guardrails、LangGraph 的 interrupt/
checkpoint 边界、Dify 的 Knowledge pipeline 节点隔离。这些产品都把
"哪些模块绝不能耦合"用静态契约固化下来，避免后续重构悄悄打破信任链。

本文件给 v0.12 custom strategy 这条 use-case 路径补上**轻量 AST
import-boundary 守卫**：用 ``ast`` 静态解析 ``preview_packet`` /
``custom`` / ``custom_loader`` 三个文件的 ``import`` 语句，禁止它们
反向依赖 CLI、approval、writer、llm、provider、process / review /
recall / obsidian 等运行期模块。

为什么是 AST 而不是 ``import``？
================================
真去 import 这些模块会触发它们的 import-time 副作用，反而无法
*只检查 import graph*。AST 走源码、零副作用、可在 CI 早期失败。

为什么是单独文件而不是塞进现有 boundary 测试？
==============================================
``test_strategy_boundaries.py`` 已经管"strategies 包对外 re-export
契约"；本文件管"custom 三件套对内部 runtime 模块的反向依赖禁令"。
两个关注点不同，单独成文保持高内聚。

本文件不做的事
==============
- 不执行 custom strategy；
- 不构造 LLM 客户端；
- 不读 dotenv；
- 不写 vault；
- 不 import 任何被检查模块（只读源码）。
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# 中文学习型注释：被守卫文件 = custom strategy 的"安全前室"。
# 这三个文件一旦反向 import runtime 模块（cli / approval / writer / llm
# / provider / process_service / review_service / recall_service /
# obsidian），custom 路径就可能在 import-time 触达执行/写入/审批副作用。
_GUARDED_FILES: tuple[Path, ...] = (
    Path("src/mindforge/strategies/preview_packet.py"),
    Path("src/mindforge/strategies/custom.py"),
    Path("src/mindforge/strategies/custom_loader.py"),
)

# 中文学习型注释：黑名单按"模块前缀"匹配，覆盖
# ``import x`` / ``from x import y`` / ``from x.sub import y``。
# 刻意不列 ``mindforge.strategies`` 自身——同包内互引（如
# preview_packet 引 custom）是允许的高内聚关系。
_FORBIDDEN_IMPORT_PREFIXES: tuple[str, ...] = (
    "mindforge.cli",
    "mindforge.app_context",
    "mindforge.approval_service",
    "mindforge.approver",
    "mindforge.approve_presenter",
    "mindforge.writer",
    "mindforge.cards",
    "mindforge.llm",
    "mindforge.process_service",
    "mindforge.review_service",
    "mindforge.review_presenter",
    "mindforge.recall_service",
    "mindforge.recall_presenter",
    "mindforge.obsidian",
    "mindforge.obsidian_cli",
    "mindforge.obsidian_stage",
    "mindforge.obsidian_workflow",
    "mindforge.cubox_cli",
    "mindforge.cubox_dryrun_presenter",
    "mindforge.env_loader",
    "mindforge.processors",
    "dotenv",
    "requests",
    "httpx",
)


def _collect_imports(path: Path) -> list[str]:
    """返回文件里所有 import 的"模块全名"。

    覆盖：
    - ``import a.b`` → ``a.b``
    - ``from a.b import c`` → ``a.b``
    - ``from . import x`` 与 ``from .sib import y`` 的相对 import
      由调用方按"同包允许"过滤掉（Module 名为空时跳过）。
    """

    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and not node.module:
                continue
            if node.level:
                # 相对 import，模块名实际为同包子模块——视为同包内引
                continue
            if node.module:
                names.append(node.module)
    return names


@pytest.mark.parametrize("path", _GUARDED_FILES, ids=lambda p: p.name)
def test_custom_strategy_files_do_not_import_runtime_modules(
    path: Path,
) -> None:
    """custom 三件套不允许 import CLI / runtime / provider / IO 模块。

    一旦未来谁 PR 里悄悄 ``from mindforge.approval_service import …`` 进
    custom_loader.py，本测试在 CI 早期 hard-fail，而不是等到运行时
    custom YAML 触达 approve 路径才发现。
    """

    assert path.exists(), f"被守卫文件缺失: {path}"
    imports = _collect_imports(path)
    violations = sorted(
        {
            name
            for name in imports
            for prefix in _FORBIDDEN_IMPORT_PREFIXES
            if name == prefix or name.startswith(prefix + ".")
        }
    )
    assert not violations, (
        f"{path} 反向 import runtime 模块: {violations}; "
        "custom strategy 路径必须保持 declarative + presentation 边界, "
        "不允许耦合 CLI / approval / writer / llm / provider / IO."
    )


def test_preview_packet_does_not_import_strategies_init() -> None:
    """preview_packet 不允许 import 包根 ``mindforge.strategies``。

    包根含 build_strategy / discover_strategies 等运行期入口；preview
    packet 作为下游展示层应当"被 CLI 调用"而不是"反过来调用 registry"。
    这条规则把箭头方向钉死：cli -> preview_packet -> custom，禁止
    preview_packet -> strategies(包根) 的回旋反向依赖。
    """

    path = Path("src/mindforge/strategies/preview_packet.py")
    imports = _collect_imports(path)
    bad = [n for n in imports if n == "mindforge.strategies"]
    assert not bad, (
        f"preview_packet.py 反向 import 包根: {bad}; 应只 import "
        "兄弟模块 (.custom 等)."
    )
