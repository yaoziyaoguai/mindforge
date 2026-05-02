"""Source Plugin Slice 4 — Cubox adapter safety boundary 契约 (TDD)。

为什么有这个文件
================

Cubox 是 v0.9 唯一持有"真实远端 API 入口"声明的 source（Slice 2 让
``CuboxApiAdapter.capabilities()`` 多出 ``"real_api"``）。Slice 4 的
任务是**用静态 / 行为测试把 Cubox 路径锁住**，让任何未来 PR 想要：

1. 让 ``CuboxApiAdapter`` 在 ``__init__`` 里读 .env / 联网；
2. 让 ``fetch_inbox`` 默默连接真实 HTTP；
3. 让 ``CuboxApiCredential.__repr__`` 把 token 明文打印；
4. 在 ``cubox_api.py`` / ``cubox_markdown.py`` 顶部 import requests /
   httpx / urllib3 / aiohttp；
5. 让 ``CuboxApiCredential.from_env`` 自动找默认变量名；

…都立刻被 CI 拒掉。

设计边界
========

- 本文件**只动 tests**，不动 production code（Cubox 现状已经满足契约，
  Slice 4 是把现状钉成不可回退的边界）。
- 用 monkeypatch 拦截 socket，证明 import + 实例化不会发起任何 TCP。
- 用 AST 静态扫 import 表，把网络库 / oss SDK 列为禁运清单。

Red / Green 期望
================

全部 **Green**（钉边界，无生产改动）。Slice 4 的 Red 来自未来回归——
任何想撕开 Cubox opt-in 闸门的 PR 都会被这一组测试钉住。
"""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

from mindforge.sources.cubox_api import (
    CuboxApiAdapter,
    CuboxApiCredential,
    CuboxApiNotConfigured,
)
from mindforge.sources.cubox_markdown import CuboxMarkdownAdapter


# ---------------------------------------------------------------------------
# 工具：AST import 扫描
# ---------------------------------------------------------------------------


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


_NETWORK_LIBS = {
    "requests",
    "httpx",
    "urllib3",
    "aiohttp",
    "urllib",  # urllib.request 也在 urllib 命名空间
    "http",  # http.client
    "websockets",
    "grpc",
}


# ---------------------------------------------------------------------------
# 1. CuboxApiAdapter 实例化必须 fake-safe
# ---------------------------------------------------------------------------


def test_cubox_api_adapter_instantiation_does_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """实例化 CuboxApiAdapter 不能 open 文件、不能开 socket。

    实例化阶段如果触发 IO，会让 ``capabilities()`` 探测、registry 构造、
    fake test 全部连锁需要 fixture。这条边界由本测试守护。
    """

    def _no_socket(*a: object, **kw: object) -> object:
        raise AssertionError("CuboxApiAdapter() 不得在实例化时开 socket")

    monkeypatch.setattr(socket, "socket", _no_socket)
    adapter = CuboxApiAdapter()
    assert adapter.name == "CuboxApiAdapter"
    # 同时确认默认无凭据
    assert adapter.credential.is_configured() is False


# ---------------------------------------------------------------------------
# 2. fetch_inbox 必须显式 NotImplementedError，credential 是否存在不影响
# ---------------------------------------------------------------------------


def test_fetch_inbox_raises_not_implemented_without_credential() -> None:
    adapter = CuboxApiAdapter()
    with pytest.raises(NotImplementedError):
        adapter.fetch_inbox()


def test_fetch_inbox_raises_not_implemented_even_with_credential() -> None:
    """有 credential 也必须 NotImplementedError —— opt-in 闸门是行为，不是配置。"""
    adapter = CuboxApiAdapter(credential=CuboxApiCredential(token="t-secret-xyz"))
    with pytest.raises(NotImplementedError):
        adapter.fetch_inbox()


# ---------------------------------------------------------------------------
# 3. CuboxApiCredential.__repr__ / __str__ 不得泄漏 token
# ---------------------------------------------------------------------------


def test_credential_repr_does_not_leak_token() -> None:
    cred = CuboxApiCredential(token="t-super-secret-DEADBEEF")
    assert "DEADBEEF" not in repr(cred)
    assert "t-super-secret" not in repr(cred)
    assert "DEADBEEF" not in str(cred)
    # 必须暴露 credential_present 信号供调试
    assert "credential_present=True" in repr(cred)


def test_credential_repr_marks_absence_when_unconfigured() -> None:
    cred = CuboxApiCredential()
    assert "credential_present=False" in repr(cred)


# ---------------------------------------------------------------------------
# 4. from_env 必须显式指定 var_name；缺失 / 空值必须 raise
# ---------------------------------------------------------------------------


def test_from_env_requires_explicit_var_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """``from_env`` 必须显式传入 var_name；缺值必须爆炸，绝不静默返回 None。

    对照 SoT：``CuboxApiCredential.from_env`` 不接受默认 var_name；调用
    ``from_env()`` 不传参，应报 TypeError；传未设置的变量名应报
    CuboxApiNotConfigured。
    """
    # 移除常见默认变量名以模拟"无环境配置"
    for n in (
        "CUBOX_TOKEN",
        "MINDFORGE_CUBOX_TOKEN",
        "CUBOX_API_TOKEN",
        "MINDFORGE_TEST_CUBOX_TOKEN_X",
    ):
        monkeypatch.delenv(n, raising=False)

    with pytest.raises(TypeError):
        CuboxApiCredential.from_env()  # type: ignore[call-arg]

    with pytest.raises(CuboxApiNotConfigured):
        CuboxApiCredential.from_env("MINDFORGE_TEST_CUBOX_TOKEN_X")


# ---------------------------------------------------------------------------
# 5. cubox_api.py / cubox_markdown.py 不得 import 任何网络库
# ---------------------------------------------------------------------------


def test_cubox_api_module_imports_no_network_library() -> None:
    import mindforge.sources.cubox_api as mod

    leaked = _module_imports(Path(mod.__file__)) & _NETWORK_LIBS
    assert not leaked, (
        f"cubox_api.py 不得 import 网络库 {leaked}；真实 HTTP 路径必须等到"
        " opt-in milestone 才能引入依赖"
    )


def test_cubox_markdown_module_imports_no_network_library() -> None:
    import mindforge.sources.cubox_markdown as mod

    leaked = _module_imports(Path(mod.__file__)) & _NETWORK_LIBS
    assert not leaked, f"cubox_markdown.py 不得 import 网络库 {leaked}"


# ---------------------------------------------------------------------------
# 6. capabilities() 是 Slice 2 契约的延续 —— Cubox API 是唯一持 real_api 的
# ---------------------------------------------------------------------------


def test_only_cubox_api_declares_real_api_capability() -> None:
    from mindforge.sources.registry import _BUILTIN_ADAPTERS

    real_api_holders = {
        name
        for name, cls in _BUILTIN_ADAPTERS.items()
        if "real_api" in cls().capabilities()
    }
    assert real_api_holders == {"CuboxApiAdapter"}, (
        f"只有 cubox_api 应持 real_api capability；当前 {real_api_holders}"
    )


# ---------------------------------------------------------------------------
# 7. CuboxMarkdownAdapter 仍是 fake-safe（无 real_api）
# ---------------------------------------------------------------------------


def test_cubox_markdown_adapter_does_not_declare_real_api() -> None:
    """CuboxMarkdownAdapter 走的是离线 .md 文件路径，不应有 real_api。"""
    caps = CuboxMarkdownAdapter().capabilities()
    assert "real_api" not in caps
    assert "fake_safe" in caps
    assert "local_file" in caps
