"""SourceAdapter 注册表 — 把配置中的 adapter 名解析为具体类实例。

为什么有这个文件？
------------------
- ``configs/mindforge.yaml.sources.registry.<source_type>.adapter`` 写的是
  字符串（adapter 类名），代码层需要一个"名字 → 类"的映射；
- 加新 adapter 的唯一改动点：在本文件 ``_BUILTIN_ADAPTERS`` 加一行，外加
  在 yaml 里加 registry 条目。Scanner / 业务层都不用改。
"""

from __future__ import annotations

from typing import Type

from ..config import SourcesConfig
from .base import SourceAdapter
from .chat_export import ChatExportAdapter
from .common_document import CommonDocumentAdapter
from .cubox_api import CuboxApiAdapter
from .cubox_markdown import CuboxMarkdownAdapter
from .docx import DocxAdapter
from .obsidian_vault import ObsidianVaultSourceAdapter
from .pdf import PdfAdapter
from .plain_markdown import PlainMarkdownAdapter
from .webclip_markdown import WebClipMarkdownAdapter

# adapter 类名 → 类。新增 adapter 在此处加一行即可。
_BUILTIN_ADAPTERS: dict[str, Type[SourceAdapter]] = {
    "CuboxMarkdownAdapter": CuboxMarkdownAdapter,
    "CuboxApiAdapter": CuboxApiAdapter,
    "PlainMarkdownAdapter": PlainMarkdownAdapter,
    "WebClipMarkdownAdapter": WebClipMarkdownAdapter,
    "PdfAdapter": PdfAdapter,
    "DocxAdapter": DocxAdapter,
    "ChatExportAdapter": ChatExportAdapter,
    "ObsidianVaultSourceAdapter": ObsidianVaultSourceAdapter,
    "CommonDocumentAdapter": CommonDocumentAdapter,
}


class AdapterRegistryError(RuntimeError):
    """adapter 名找不到对应类，或 source_type / 类不一致。"""


def build_active_adapters(sources: SourcesConfig) -> dict[str, SourceAdapter]:
    """根据 SourcesConfig 实例化所有"启用"的 adapter。

    返回 ``source_type -> SourceAdapter`` 的 dict，便于 Scanner 按子目录派发。

    校验：
    - adapter 类名必须存在于 ``_BUILTIN_ADAPTERS``；
    - adapter 类的 ``source_type`` 必须与配置中的 source_type 一致（防止
      两边对不上）。
    """
    result: dict[str, SourceAdapter] = {}
    for entry in sources.active_entries():
        cls = _BUILTIN_ADAPTERS.get(entry.adapter)
        if cls is None:
            raise AdapterRegistryError(
                f"未注册的 adapter 类 {entry.adapter!r}（source_type={entry.source_type}）"
            )
        if cls.source_type != entry.source_type:
            raise AdapterRegistryError(
                f"adapter {entry.adapter} 的 source_type={cls.source_type!r} "
                f"与 registry 中的 {entry.source_type!r} 不一致"
            )
        result[entry.source_type] = cls()
    return result


# ---------------------------------------------------------------------------
# v0.2 AdapterRegistry — source-layer dispatch boundary
#
# RFC_0001 §5.3：按优先级派发 adapter，不改变 processing / approval / wiki 语义。
# 与 v0.1 ``build_active_adapters()`` 并存，互不干扰。
# ---------------------------------------------------------------------------


class AdapterRegistry:
    """v0.2 SourceAdapter 注册表。

    维护已注册的 v0.2 adapter，按注册顺序派发：
    1. 逐个调用 ``adapter.can_handle(path)``
    2. 返回第一个匹配的 adapter
    3. 无匹配 → 返回 None

    registry 只做 source-layer dispatch，不负责：
    - load result 解释
    - processing / approval / wiki
    - dependency loading for future adapters
    """

    def __init__(self) -> None:
        self._adapters: list = []  # type: ignore[type-arg] — 暂不绑定 SourceAdapter 泛型

    def register(self, adapter) -> None:  # type: ignore[no-untyped-def]
        """注册一个 SourceAdapter。

        后注册的优先级低于先注册的（先注册先匹配）。
        adapter 必须实现 can_handle / load / capabilities。
        """
        self._adapters.append(adapter)

    def find_for_path(self, path: str):
        """按注册顺序查找第一个能处理 path 的 adapter。

        逐个调用 adapter.can_handle(path)，返回第一个返回 True 的。
        找不到则返回 None——不抛异常作为正常 unsupported 行为。
        """
        for adapter in self._adapters:
            if adapter.can_handle(path):
                return adapter
        return None

    def find_for_type(self, source_type: str):
        """按 source_type 查找 adapter（RFC_0001 §5.3）。"""
        for adapter in self._adapters:
            if adapter.source_type == source_type:
                return adapter
        return None

    def list_adapters(self) -> tuple:
        """返回已注册 adapter 的不可变只读视图。"""
        return tuple(self._adapters)


def create_default_registry() -> AdapterRegistry:
    """创建默认 registry，仅注册 PlainMarkdownAdapter。

    M1 阶段不注册 TXT/HTML/PDF/DOCX。
    不接入 CLI/import/watch 主链路。
    """
    from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

    registry = AdapterRegistry()
    registry.register(PlainMarkdownAdapter())
    return registry


__all__ = [
    "AdapterRegistryError",
    "build_active_adapters",
    "AdapterRegistry",
    "create_default_registry",
]
