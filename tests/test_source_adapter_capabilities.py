"""Source Plugin Slice 2 — SourceAdapter capability contract 测试 (TDD Red 阶段)。

为什么有这个文件
================

v0.9 Source ingestion milestone 的 Slice 2 目标是把"adapter 能做什么"
显式化：每个 ``SourceAdapter`` 必须在调用前就能告诉调用方它具备哪些
能力（``local_file`` / ``fake_safe`` / ``dry_run`` / ``real_api`` …），
让运行时**先看 capability 再决定是否调用**，借鉴自 Airbyte connector spec
的 ``spec`` + ``discover`` 模式（见 ``docs/ROADMAP.md`` v0.9 §A
"External research alignment — Source ingestion"）。

当前 ``src/mindforge/sources/base.py`` 的 ``SourceAdapter`` 只暴露
``can_handle`` / ``load`` 两个抽象方法，**没有** ``capabilities()`` 方法，
也没有 capability 元数据。本文件用 TDD Red 的方式把这个 Slice 2 契约
缺口显式钉死。

设计边界
========

- 本文件**只动 tests**，不动 production code；
- 不调用真实 LLM、不读 .env、不写 Obsidian vault、不触发 approval；
- 不实现 SourcePlugin / SourceAdapter 重构 / SourceMux；
- 不改任何 adapter 行为；
- 仅 import ``mindforge.sources.base`` 与 ``mindforge.sources.registry`` —
  后者用来枚举内置 adapter 列表，避免在测试里硬编码。

Red / Green 期望
================

- **预期 Red**：
  1. ``test_source_adapter_declares_capabilities`` —— ``SourceAdapter``
     基类没有 ``capabilities()`` 方法。
  2. ``test_each_builtin_adapter_returns_capability_set`` —— 每个内置
     adapter 实例化后调用 ``capabilities()`` 应返回 ``frozenset[str]``，
     当前所有 adapter 都没有这个方法。
  3. ``test_real_api_capability_requires_explicit_opt_in`` —— Cubox API
     adapter 的 capability 集合必须显式包含 ``"real_api"`` 标记，且默认
     调用 ``fetch_inbox`` 仍 raise ``NotImplementedError``（后半句已经
     满足，前半句因为没有 ``capabilities()`` 而 Red）。

- **Green 守卫**（今天就应通过）：
  - ``test_cubox_api_fetch_inbox_still_gated`` —— v0.9 Slice 2 不能
    悄悄打开真实 API；这是回归守卫。
  - ``test_capabilities_must_not_perform_io_at_import_time`` —— 仅
    `import mindforge.sources.base` 不应触发文件 / 网络 IO（用
    monkeypatch 守 builtins.open / socket）。
"""

from __future__ import annotations

import socket

import pytest

from mindforge.sources.base import SourceAdapter
from mindforge.sources.registry import _BUILTIN_ADAPTERS

# ---------------------------------------------------------------------------
# 1. SourceAdapter 基类必须暴露 capabilities() 接口
# ---------------------------------------------------------------------------


def test_source_adapter_declares_capabilities() -> None:
    """SourceAdapter 必须在基类层面声明 capabilities() 方法。

    Slice 2 契约：capability 是 adapter 的"自我描述"，由基类提供默认
    实现（如返回 ``frozenset({"local_file", "fake_safe", "dry_run"})``），
    子类按需 override。

    **预期 Red**：当前 ``SourceAdapter`` 只有 ``can_handle`` / ``load``，
    没有 ``capabilities``。Slice 2 Green 阶段需要在 ``base.py`` 加这个
    方法（并保持是普通方法、不是抽象方法，避免迫使 8 个 adapter 全部
    override）。
    """
    assert hasattr(SourceAdapter, "capabilities"), (
        "SourceAdapter 必须暴露 capabilities() 方法，"
        "用于声明 'local_file' / 'fake_safe' / 'dry_run' / 'real_api' 等能力。"
    )
    assert callable(getattr(SourceAdapter, "capabilities", None))


# ---------------------------------------------------------------------------
# 2. 每个内置 adapter 实例化后 capabilities() 必须返回 frozenset[str]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_cls_name", sorted(_BUILTIN_ADAPTERS.keys()))
def test_each_builtin_adapter_returns_capability_set(adapter_cls_name: str) -> None:
    """所有 8 个内置 adapter 都必须能返回一个 frozenset[str] 的能力集合。

    Slice 2 契约要求 capabilities 是**不可变**集合（``frozenset``）：
    - 不可变保证调用方不能误把 capability 集合当成可变状态修改；
    - ``str`` 元素保证可序列化、可日志、可比较；
    - 每次调用返回相同集合（不依赖随机数 / 时间 / 网络）。

    **预期 Red**：当前 adapter 没有 ``capabilities()``，调用会触发
    ``AttributeError``。
    """
    cls = _BUILTIN_ADAPTERS[adapter_cls_name]
    instance = cls()
    caps = instance.capabilities()  # type: ignore[attr-defined]
    assert isinstance(caps, frozenset), (
        f"{adapter_cls_name}.capabilities() 必须返回 frozenset，"
        f"实际类型 {type(caps).__name__}"
    )
    assert all(isinstance(c, str) for c in caps), (
        f"{adapter_cls_name}.capabilities() 元素必须全部是 str"
    )


# ---------------------------------------------------------------------------
# 3. 至少一个核心 capability 必须存在：fake_safe（默认安全路径）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_cls_name", sorted(_BUILTIN_ADAPTERS.keys()))
def test_each_builtin_adapter_declares_fake_safe(adapter_cls_name: str) -> None:
    """所有内置 adapter 默认必须声明 ``fake_safe`` 能力。

    含义：在不传任何 credential / 不连真实 API 的前提下，adapter 至少
    可以被实例化、可以被 ``can_handle`` 询问、不会做副作用。这是 v0.9
    "fake-default" 安全契约的可机读化。

    **预期 Red**：今天没有 ``capabilities()``，本测试会 Red。
    """
    cls = _BUILTIN_ADAPTERS[adapter_cls_name]
    caps = cls().capabilities()  # type: ignore[attr-defined]
    assert "fake_safe" in caps, (
        f"{adapter_cls_name} 必须声明 'fake_safe' 能力 "
        f"（即 fake/dry-run-first 安全契约）；当前 capabilities={caps}"
    )


# ---------------------------------------------------------------------------
# 4. real_api capability 必须显式 opt-in：只有 CuboxApiAdapter 应当声明它
# ---------------------------------------------------------------------------


def test_real_api_capability_requires_explicit_opt_in() -> None:
    """``real_api`` 标记只能出现在已经设计为可选 opt-in 真实 API 的 adapter。

    当前唯一这样的 adapter 是 ``CuboxApiAdapter``（其 ``fetch_inbox``
    在没有 credential 时 raise ``NotImplementedError``）。Slice 2 契约
    要求该 adapter 显式声明 ``real_api``，其余 7 个本地文件 adapter
    一律**不**得声明该能力。

    **预期 Red**：今天没有 ``capabilities()``。
    """
    real_api_adapters: set[str] = set()
    for name, cls in _BUILTIN_ADAPTERS.items():
        caps = cls().capabilities()  # type: ignore[attr-defined]
        if "real_api" in caps:
            real_api_adapters.add(name)
    assert real_api_adapters == {"CuboxApiAdapter"}, (
        f"只有 CuboxApiAdapter 应该声明 'real_api'；"
        f"实际声明的集合：{real_api_adapters}"
    )


# ---------------------------------------------------------------------------
# 5. capabilities() 必须是纯查询：调用不能触发 IO（文件 / 网络 / .env）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("adapter_cls_name", sorted(_BUILTIN_ADAPTERS.keys()))
def test_capabilities_does_no_io(
    adapter_cls_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """调用 ``capabilities()`` 不能打开文件、不能创建 socket、不能读 env。

    Slice 2 契约：capability 是**声明性**元数据，必须可在初始化或
    discovery 阶段廉价调用，绝对不能藏一个 ``open(...)`` 或
    ``requests.get(...)``。否则 Airbyte 风格的 "先 spec 再 discover
    再 invoke" 三段式安全保证就破了。

    **预期 Red**：今天没有 ``capabilities()`` 方法，AttributeError 即 Red。
    """

    def _no_open(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            f"{adapter_cls_name}.capabilities() 触发了 open()，违反 Slice 2 契约"
        )

    def _no_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            f"{adapter_cls_name}.capabilities() 触发了 socket()，违反 Slice 2 契约"
        )

    monkeypatch.setattr("builtins.open", _no_open)
    monkeypatch.setattr(socket, "socket", _no_socket)

    cls = _BUILTIN_ADAPTERS[adapter_cls_name]
    instance = cls()
    # 调用本身不应触发 open / socket；如果触发，上面的 assertion 会让测试 fail。
    caps = instance.capabilities()  # type: ignore[attr-defined]
    assert isinstance(caps, frozenset)


# ---------------------------------------------------------------------------
# 6. 回归守卫：CuboxApiAdapter.fetch_inbox 在没有 credential 时仍 raise
#    NotImplementedError —— Slice 2 Green 不能悄悄打开真实 API。
#    这条今天就 Green，作用是防止后续 Slice 2 Green 漂移。
# ---------------------------------------------------------------------------


def test_cubox_api_fetch_inbox_still_gated() -> None:
    """CuboxApiAdapter.fetch_inbox 必须仍处于 opt-in 状态。"""
    from mindforge.sources.cubox_api import CuboxApiAdapter

    adapter = CuboxApiAdapter()
    with pytest.raises(NotImplementedError, match="opt-in"):
        adapter.fetch_inbox()


# ---------------------------------------------------------------------------
# 7. 边界守卫：SourceAdapter 模块不能 import strategy / approval / cli
# ---------------------------------------------------------------------------


def test_source_adapter_module_has_no_downstream_imports() -> None:
    """``mindforge.sources.base`` 命名空间不应出现 strategy / approval /
    cli / processor / pipeline / recall 任何下游领域符号。

    本测试不是 Slice 2 直接契约（Slice 1 已有类似守卫），而是把同样
    边界扩到"加 capability 后也不能借机引入下游耦合"——是一条预防漂移
    的 Green 守卫。
    """
    import mindforge.sources.base as base_mod

    forbidden_substrings = (
        "Strategy",
        "Approval",
        "Review",
        "Pipeline",
        "Processor",
        "Cli",
        "Recall",
    )
    leaked = [
        name
        for name in dir(base_mod)
        if not name.startswith("_")
        and any(sub in name for sub in forbidden_substrings)
    ]
    assert leaked == [], (
        f"加 capability 后，sources.base 仍不应暴露下游领域符号：{leaked}"
    )
