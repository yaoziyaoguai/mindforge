"""向后兼容 shim：v0.2.5 起 PdfAdapter / DocxAdapter 已升级为真实 adapter。

- ``PdfAdapter`` 已迁移到 ``mindforge.sources.pdf``；
- ``DocxAdapter`` 已迁移到 ``mindforge.sources.docx``；

本文件仅作为旧 import 路径（``from mindforge.sources.stubs import ...``）
的兼容层。M5.1 协议见 ``docs/M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md``。
"""

from .docx import DocxAdapter
from .pdf import OptionalDependencyError, PdfAdapter, PdfNoTextError

__all__ = [
    "PdfAdapter",
    "DocxAdapter",
    "OptionalDependencyError",
    "PdfNoTextError",
]
