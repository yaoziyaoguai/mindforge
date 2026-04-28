"""v0.1 stub adapters — 仅占位，调用 ``load()`` 抛 ``NotImplementedError``。

为什么仍然保留 stub？
---------------------
v0.2.4 已经把 ``WebClipMarkdownAdapter`` 与 ``ChatExportAdapter`` 升级为真实
adapter（见同目录下 ``webclip_markdown.py`` / ``chat_export.py``）。本文件
只剩 ``PdfAdapter`` / ``DocxAdapter`` 两个 stub：

1. **类型 / 目录 / 配置占位**：让 ``configs/mindforge.yaml.sources.registry``
   能合法引用这些 adapter 名，从而锁住"PDF / Docx 会进哪个 inbox 子目录"。
2. **明确边界**：用户如果不小心把 PDF 放进 ``00-Inbox/PDFs/`` 并打开了
   ``enabled: true``，会立刻得到一个 ``NotImplementedError``，而不是被静默
   忽略或假装处理成功。
3. **协议演练**：每个 stub 仍然继承 ``SourceAdapter``，编译期保证 ``name`` /
   ``source_type`` / 抽象方法签名都是对的。

为什么 PDF/Docx 仍然先轻量预留？
-------------------------------
PDF 千差万别（扫描件 / 文字 PDF / 复杂表格 / 多列学术论文 …），盲目实现
很容易掉进 OCR 工程化的无底洞。v0.2.4 的策略是：

- 先把"协议位置"留好（registry 条目 + stub 类）；
- 实现细节由 ``docs/M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md`` 描述；
- 真要做最小文本抽取，等到有真实需求再一次性做掉，避免假抽象。
"""

from __future__ import annotations

from .base import SourceAdapter, SourceDocument


class _StubAdapter(SourceAdapter):
    """所有 stub adapter 的共同实现：can_handle 永远 False，load 抛错。"""

    def can_handle(self, path: str) -> bool:  # pragma: no cover - 永远 False
        return False

    def load(self, path: str) -> SourceDocument:
        raise NotImplementedError(
            f"{self.__class__.__name__} 在当前版本仅作占位，未实现。"
            "请参考 docs/M5_1_PDF_DOCX_ADAPTER_PROTOCOL.md。"
        )


class PdfAdapter(_StubAdapter):
    """PDF 适配器 stub。当前不做 OCR / 表格抽取 / 复杂版式还原。"""

    name = "PdfAdapter"
    source_type = "pdf"  # type: ignore[assignment]


class DocxAdapter(_StubAdapter):
    """Docx 适配器 stub。当前不解析复杂样式 / 表格。"""

    name = "DocxAdapter"
    source_type = "docx"  # type: ignore[assignment]


__all__ = [
    "PdfAdapter",
    "DocxAdapter",
]
