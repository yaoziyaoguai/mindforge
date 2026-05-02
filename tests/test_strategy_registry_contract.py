"""v0.11 StrategyRegistry Slice 1 — Red contract tests.

为什么本切片只做 registry basics / metadata / list / unknown error
====================================================================

v0.10 已经把 strategy 输出统一到公共 envelope，writer / presenter /
process_service 都成为 envelope 消费者。下一步要让 CLI 可以列出策略、
让 strategy 自报家门（id / version / 显示名 / 描述），把"策略元信息"
这条职责从散落的字符串字面量收敛到统一来源。

本切片**只**关心：
- registry 的查询契约（lookup / list / unknown error）
- built-in strategy 的元数据自描述（``STRATEGY_ID`` / ``STRATEGY_VERSION``
  / ``STRATEGY_DISPLAY_NAME`` / ``STRATEGY_DESCRIPTION``）
- 一个统一的 ``StrategyMetadata`` 数据结构，让 CLI 与未来 v0.12 custom
  strategy 都能消费同一形状
- 一个最小的 CLI ``mindforge strategies list`` 命令，让用户在不调用任何
  LLM / .env / Cubox / Obsidian 的前提下就能看到"我能选哪些策略"

本切片**不**做：
- StrategyRegistry production 实现（这是 Green 阶段的事）
- custom / 声明式 / 脚本 strategy
- registry 调用 LLM / 写文件 / 读 .env / approve
- registry 变成 provider registry / prompt 巨石 / writer/presenter 巨石

本文件全部为 test-only Red 契约：production code 在 Slice 1 Green
之前应当让这些测试**因 production gap 失败**，而不是因为环境/导入问题
失败。
"""

from __future__ import annotations

from dataclasses import is_dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from mindforge.strategies import (
    DEFAULT_STRATEGY_NAME,
    UnknownStrategyError,
    available_strategies,
    build_strategy,
)
from mindforge.strategies import registry as registry_mod


# ---------------------------------------------------------------------------
# Family A — registry basics（多数为 Green baseline，锁定既有契约不退化）
# ---------------------------------------------------------------------------


def test_available_strategies_returns_sorted_tuple_snapshot() -> None:
    """`available_strategies()` 必须返回稳定按字典序排序的元组快照。

    Green baseline：避免后续重构把它改成 list / 无序 dict_keys，破坏
    "registry lookup 无副作用且结果稳定" 的契约。
    """

    names = available_strategies()
    assert isinstance(names, tuple)
    assert list(names) == sorted(names)
    assert DEFAULT_STRATEGY_NAME in names


def test_unknown_strategy_error_message_includes_available_hint() -> None:
    """未知策略名错误必须列出可选项，让 CLI / 测试可以直接展示。"""

    with pytest.raises(UnknownStrategyError) as excinfo:
        build_strategy("does_not_exist_xyz", ctx=_ctx())

    msg = str(excinfo.value)
    assert "does_not_exist_xyz" in msg
    for name in available_strategies():
        assert name in msg


def test_registry_module_does_not_import_provider_or_io_modules() -> None:
    """registry 必须保持"只做派发"，不依赖 provider / writer / presenter /
    approval / Cubox / .env，避免在 Slice 1 Green 之后无意把它扩成新巨石。
    """

    src = Path(registry_mod.__file__).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import httpx",
        "from .writer",
        "from .presenter",
        "from .cubox_adapter",
        "from .approval_service",
        "load_dotenv",
        "UPSTAGE_API_KEY",
        "human_approved",
    )
    for token in forbidden:
        assert token not in src, (
            f"registry.py 出现了越界引用 {token!r}；"
            "registry 必须只做 strategy lookup / metadata。"
        )


# ---------------------------------------------------------------------------
# Family B — built-in strategy metadata（核心 Red 缺口）
# ---------------------------------------------------------------------------


REQUIRED_METADATA_CONSTANTS = (
    "STRATEGY_ID",
    "STRATEGY_VERSION",
    "STRATEGY_DISPLAY_NAME",
    "STRATEGY_DESCRIPTION",
)


@pytest.mark.parametrize("strategy_name", ["default_knowledge_card", "five_stage"])
def test_builtin_strategy_module_exposes_metadata_constants(strategy_name: str) -> None:
    """每个内建策略模块必须在 module 级导出四项元数据常量。

    Red 期望：``five_stage`` 模块当前完全没有这些常量；
    ``default_knowledge_card`` 也缺 ``DISPLAY_NAME`` / ``DESCRIPTION``。
    Slice 1 Green 必须把它们补齐到 strategy 模块顶层（不是埋在 docstring 里）。
    """

    import importlib

    mod = importlib.import_module(f"mindforge.strategies.{strategy_name}")
    missing = [c for c in REQUIRED_METADATA_CONSTANTS if not hasattr(mod, c)]
    assert not missing, (
        f"strategy 模块 {strategy_name!r} 缺少元数据常量：{missing}；"
        f"Green 必须在 module 级补齐 {REQUIRED_METADATA_CONSTANTS}。"
    )

    for const in REQUIRED_METADATA_CONSTANTS:
        value = getattr(mod, const)
        assert isinstance(value, str) and value.strip(), (
            f"{strategy_name}.{const} 必须是非空字符串，实际：{value!r}"
        )


def test_builtin_strategy_id_constant_matches_registry_name() -> None:
    """每个内建策略模块的 ``STRATEGY_ID`` 必须等于其在 registry 中的注册名，
    避免 pipeline 输出 envelope 里的 ``strategy_id`` 与 CLI ``--strategy``
    传入的名字不一致。
    """

    import importlib

    for name in available_strategies():
        mod = importlib.import_module(f"mindforge.strategies.{name}")
        sid = getattr(mod, "STRATEGY_ID", None)
        assert sid == name, (
            f"strategy 模块 {name!r} 的 STRATEGY_ID={sid!r} 与注册名不一致；"
            "metadata 必须是单一来源。"
        )


# ---------------------------------------------------------------------------
# Family C — StrategyMetadata 统一数据结构与 list/get API
# ---------------------------------------------------------------------------


def test_registry_exposes_strategy_metadata_dataclass() -> None:
    """registry 必须提供一个 ``StrategyMetadata`` frozen dataclass，
    把 ``strategy_id`` / ``strategy_version`` / ``display_name`` /
    ``description`` 四项元数据收敛成单一类型，供 CLI list / 文档生成 /
    未来 v0.12 custom strategy 共用。
    """

    from mindforge import strategies as strategies_pkg

    cls = getattr(strategies_pkg, "StrategyMetadata", None)
    assert cls is not None, (
        "mindforge.strategies 必须导出 StrategyMetadata；"
        "Slice 1 Green 在 registry 模块定义并 re-export。"
    )
    assert is_dataclass(cls), "StrategyMetadata 必须是 dataclass"

    fields = {f for f in cls.__dataclass_fields__}
    expected = {"strategy_id", "strategy_version", "display_name", "description"}
    assert expected <= fields, (
        f"StrategyMetadata 缺字段：{expected - fields}"
    )


def test_registry_exposes_get_strategy_metadata_for_known_name() -> None:
    """``get_strategy_metadata(name)`` 必须返回该策略的 ``StrategyMetadata``。

    Red 期望：当前 registry 没有这个函数。
    """

    from mindforge import strategies as strategies_pkg

    fn = getattr(strategies_pkg, "get_strategy_metadata", None)
    assert fn is not None, (
        "mindforge.strategies 必须导出 get_strategy_metadata(name)。"
    )

    meta = fn(DEFAULT_STRATEGY_NAME)
    assert meta.strategy_id == DEFAULT_STRATEGY_NAME
    assert meta.strategy_version, "strategy_version 必须非空"
    assert meta.display_name, "display_name 必须非空"
    assert meta.description, "description 必须非空"


def test_get_strategy_metadata_for_unknown_name_raises_unknown_strategy_error() -> None:
    """``get_strategy_metadata`` 在未知策略名时必须复用 ``UnknownStrategyError``，
    而不是返回 None / 抛 KeyError —— 错误类型是契约的一部分。
    """

    from mindforge import strategies as strategies_pkg

    fn = getattr(strategies_pkg, "get_strategy_metadata", None)
    assert fn is not None
    with pytest.raises(UnknownStrategyError):
        fn("does_not_exist_xyz")


def test_registry_exposes_list_strategies_returning_metadata_tuple() -> None:
    """``list_strategies()`` 必须返回所有内建策略的 ``StrategyMetadata`` 元组，
    顺序与 ``available_strategies()`` 一致，作为 CLI list 的数据源。
    """

    from mindforge import strategies as strategies_pkg

    fn = getattr(strategies_pkg, "list_strategies", None)
    assert fn is not None, "mindforge.strategies 必须导出 list_strategies()"

    metas = fn()
    assert isinstance(metas, tuple)
    assert tuple(m.strategy_id for m in metas) == available_strategies()


# ---------------------------------------------------------------------------
# Family D — pipeline 不再硬编码 strategy_id 字面量
# ---------------------------------------------------------------------------


def test_pipeline_does_not_hardcode_five_stage_strategy_id_literal() -> None:
    """``processors/pipeline.py::_build_card_payload`` 不应硬编码字符串
    ``"five_stage"`` / ``"0.10.0"``，而应从 strategy 模块的 metadata 常量
    读取，避免 envelope 与 strategy 自描述出现双源漂移。

    Red 期望：当前 pipeline.py 用字符串字面量直接拼 envelope。
    """

    src = Path("src/mindforge/processors/pipeline.py").read_text(encoding="utf-8")
    assert '"five_stage"' not in src, (
        "pipeline.py 当前硬编码 'five_stage' 字面量；"
        "Slice 1 Green 必须从 mindforge.strategies.five_stage.STRATEGY_ID 读取。"
    )
    assert '"0.10.0"' not in src, (
        "pipeline.py 当前硬编码 '0.10.0' 字面量；"
        "Slice 1 Green 必须从 mindforge.strategies.five_stage.STRATEGY_VERSION 读取。"
    )


# ---------------------------------------------------------------------------
# Family E — CLI `strategies list` 命令（用户可见入口）
# ---------------------------------------------------------------------------


def test_cli_strategies_list_command_exists_and_lists_known_names() -> None:
    """``mindforge strategies list`` 必须存在，并在不调用任何 LLM / .env /
    Cubox 的前提下打印所有内建策略的 ``strategy_id``。

    Red 期望：当前 CLI 没有 ``strategies`` 子命令组。
    """

    from mindforge.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["strategies", "list"])
    assert result.exit_code == 0, (
        f"`mindforge strategies list` 不存在或失败：\n{result.output}"
    )
    for name in available_strategies():
        assert name in result.output, (
            f"输出缺少 strategy_id={name!r}；output=\n{result.output}"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx():
    """构造一个最小、离线、无 client 的 StrategyContext，仅用于 lookup 错误路径
    测试 —— 这条路径在 build_strategy 里 unknown 名字会先抛错，根本不会
    执行到 strategy 工厂，因此 client=None 是安全的。
    """

    from mindforge.strategies import StrategyContext

    return StrategyContext()
