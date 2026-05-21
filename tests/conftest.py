"""MindForge 测试全局安全网。

中文学习型说明：本文件是 pytest 的 conftest 层级继承入口。
所有 ``tests/`` 子目录下的测试自动继承此处的 fixture。
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolate_runtime_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """全局测试安全网：隔离 runtime state metadata 目录，防止测试写入真实 ``~/.mindforge``。

    中文学习型说明：

    **为什么测试默认不能写真实 ``~/.mindforge``**

    ``workspace_resolver._active_workspace_dir()`` 默认返回
    ``Path.home() / ".mindforge"``。任何调用 ``set_active_workspace()``
    的测试都会在真实 HOME 下创建/写入 ``current_workspace.json``。
    这在以下场景会导致 ``PermissionError`` 或污染真实状态：

    - CI / clean checkout 环境（HOME 不可写或被 sandbox 限制）；
    - 开发者本地机器上有真实的 MindForge 全局 active workspace 状态；
    - macOS 的 TCC / sandbox 在特定条件下阻止写入 HOME。

    **为什么 clean checkout / CI 需要 fake runtime state dir**

    clean checkout 下 ``~/.mindforge/`` 可能不存在，且 HOME 可能不可写。
    测试必须自包含 — 所有运行时状态必须落在 ``tmp_path`` 内，pytest 在
    测试结束后自动清理。

    **为什么这是测试安全网，不是生产行为变更**

    本 fixture 通过 ``monkeypatch.setenv("MINDFORGE_RUNTIME_DIR", ...)``
    设置环境变量。这是 ``workspace_resolver`` 模块提供的**正式注入入口**。
    在非 pytest 进程（正常 CLI 调用）中，此 env var 未设置，
    ``_active_workspace_dir()`` 仍返回 ``Path.home() / ".mindforge"`` —
    生产行为完全不变。

    **为什么不能通过吞 PermissionError 或 skip 测试来解决**

    - 吞 PermissionError 会隐藏真实权限问题，让用户误以为写入成功；
    - skip / xfail 只是在掩盖症状，不修复根因；
    - 只有通过注入边界正确隔离 runtime state 目录，才能让测试覆盖
      真实的路径解析逻辑链（从 ``_active_workspace_dir()`` 到文件写入），
      同时不依赖真实 HOME 的可写性。

    **与局部 fixture 的关系**

    三个测试文件（test_workspace_resolution.py / test_v0_2_6.py /
    test_v0_4_3.py）中有同名的局部 ``_isolate_runtime_dir`` fixture。
    pytest 的 fixture override 机制保证局部版本优先。
    保留局部 fixture 原因：它们有各自语境下的 docstring，
    解释了为什么要为具体测试做隔离。
    """
    monkeypatch.setenv("MINDFORGE_RUNTIME_DIR", str(tmp_path / ".mindforge"))
