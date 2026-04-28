"""v0.1 stub adapters — 仅占位，调用 ``load()`` 抛 ``NotImplementedError``。

为什么要 stub？
---------------
1. **类型 / 目录 / 配置占位**：让 ``configs/mindforge.yaml.sources.registry``
   能合法引用这些 adapter 名，从而锁住"以后 PDF / Docx / WebClip / ChatExport
   会进哪个 inbox 子目录"。
2. **明确 v0.1 边界**：用户如果不小心把 PDF 放进 ``00-Inbox/PDFs/`` 并打开了
   ``enabled: true``，会立刻得到一个 ``NotImplementedError``，而不是被静默忽略
   或假装处理成功。
3. **协议演练**：每个 stub 仍然继承 ``SourceAdapter``，编译期保证 ``name`` /
   ``source_type`` / 抽象方法签名都是对的。

实现这些 adapter 是 ``M5 高级集成`` 的事，请不要在 M1/M2/M3 阶段动它们。
"""

from __future__ import annotations

from .base import SourceAdapter, SourceDocument


class _StubAdapter(SourceAdapter):
    """所有 stub adapter 的共同实现：can_handle 永远 False，load 抛错。"""

    def can_handle(self, path: str) -> bool:  # pragma: no cover - 永远 False
        return False

    def load(self, path: str) -> SourceDocument:
        raise NotImplementedError(
            f"{self.__class__.__name__} 在 v0.1 仅作占位，未实现。"
            "请参考 docs/ROADMAP.md M5 后再启用。"
        )


class WebClipMarkdownAdapter(_StubAdapter):
    """Web Clipper / MarkDownload 等保存的网页 Markdown，v0.1 仅占位。"""

    name = "WebClipMarkdownAdapter"
    source_type = "webclip_markdown"  # type: ignore[assignment]


class PdfAdapter(_StubAdapter):
    """PDF 适配器 stub。v0.1 不做 OCR / 表格抽取。"""

    name = "PdfAdapter"
    source_type = "pdf"  # type: ignore[assignment]


class DocxAdapter(_StubAdapter):
    """Docx 适配器 stub。v0.1 不解析复杂样式。"""

    name = "DocxAdapter"
    source_type = "docx"  # type: ignore[assignment]


class ChatExportAdapter(_StubAdapter):
    """ChatGPT / Claude / Copilot 对话导出 stub，v0.1 仅占位。"""

    name = "ChatExportAdapter"
    source_type = "chat_export"  # type: ignore[assignment]


__all__ = [
    "WebClipMarkdownAdapter",
    "PdfAdapter",
    "DocxAdapter",
    "ChatExportAdapter",
]
