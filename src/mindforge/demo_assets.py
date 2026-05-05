"""Packaged demo assets for installed CLI dogfood.

中文学习型说明
==============

``mindforge demo`` 和 ``mindforge dogfood init-demo`` 面向的是安装态用户，
不能假设当前工作目录是仓库根，也不能要求用户知道 ``examples/demo-vault``
在哪里。本模块是 demo asset 的唯一边界：

- 只从 ``mindforge.assets`` package resources 读取 demo fixture / demo vault；
- 复制目标由用户显式传入，默认拒绝覆盖；
- 不读取 ``.env``、不读取真实 vault、不调用 LLM / Cubox API；
- 不生成审批结果，也不自动 approve。

这样 CLI adapter 只负责参数解析和输出，路径查找不会散落到各命令里。
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from importlib.resources.abc import Traversable
from pathlib import Path

from .assets_runtime import asset_root


DEMO_VAULT_ASSET = ("examples", "demo-vault")
DEMO_CUBOX_FIXTURE_ASSET = ("fixtures", "sample_cubox_api_export.json")


@dataclass(frozen=True)
class DemoVaultInitResult:
    """demo vault bootstrap 的结构化结果，供 CLI/presenter 渲染。"""

    target: Path
    files_copied: int
    force: bool


def demo_cubox_fixture_path() -> Path:
    """返回安装态可访问的 Cubox JSON fixture 路径。

    ``CuboxApiAdapter.parse_export`` 目前接收 ``Path``，因此这里复用
    process-lifetime asset path。调用者只读该文件，不会写 package asset。
    """

    from .assets_runtime import bundled_asset_path_for_process

    return bundled_asset_path_for_process(*DEMO_CUBOX_FIXTURE_ASSET)


def demo_vault_path() -> Path:
    """返回安装态可访问的只读 demo vault asset 路径。"""

    from .assets_runtime import bundled_asset_path_for_process

    return bundled_asset_path_for_process(*DEMO_VAULT_ASSET)


def init_demo_vault(target: Path, *, force: bool = False) -> DemoVaultInitResult:
    """把 package 内置 demo vault 复制到用户指定目标。

    默认拒绝覆盖已有路径，避免误删用户自己的工作区。``force=True`` 只会先
    删除 ``target`` 本身，再复制 package demo；调用方应把这个开关暴露成
    显式 CLI 选项。
    """

    target = target.expanduser().resolve()
    if target.exists():
        if not force:
            raise FileExistsError(str(target))
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()

    source = asset_root().joinpath(*DEMO_VAULT_ASSET)
    count = _copy_tree_resource(source, target)
    return DemoVaultInitResult(target=target, files_copied=count, force=force)


def _copy_tree_resource(source: Traversable, target: Path) -> int:
    """递归复制 importlib resource tree，返回复制文件数。"""

    if not source.is_dir():
        raise FileNotFoundError("packaged demo vault asset is missing")
    target.mkdir(parents=True, exist_ok=True)
    copied = 0
    for child in source.iterdir():
        child_target = target / child.name
        if child.is_dir():
            copied += _copy_tree_resource(child, child_target)
        else:
            child_target.parent.mkdir(parents=True, exist_ok=True)
            child_target.write_bytes(child.read_bytes())
            copied += 1
    return copied


__all__ = [
    "DEMO_CUBOX_FIXTURE_ASSET",
    "DEMO_VAULT_ASSET",
    "DemoVaultInitResult",
    "demo_cubox_fixture_path",
    "demo_vault_path",
    "init_demo_vault",
]
