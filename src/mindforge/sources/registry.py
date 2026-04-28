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
from .cubox_markdown import CuboxMarkdownAdapter
from .plain_markdown import PlainMarkdownAdapter
from .stubs import (
    ChatExportAdapter,
    DocxAdapter,
    PdfAdapter,
    WebClipMarkdownAdapter,
)

# adapter 类名 → 类。新增 adapter 在此处加一行即可。
_BUILTIN_ADAPTERS: dict[str, Type[SourceAdapter]] = {
    "CuboxMarkdownAdapter": CuboxMarkdownAdapter,
    "PlainMarkdownAdapter": PlainMarkdownAdapter,
    "WebClipMarkdownAdapter": WebClipMarkdownAdapter,
    "PdfAdapter": PdfAdapter,
    "DocxAdapter": DocxAdapter,
    "ChatExportAdapter": ChatExportAdapter,
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


__all__ = [
    "AdapterRegistryError",
    "build_active_adapters",
]
