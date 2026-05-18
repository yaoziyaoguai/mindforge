"""M4 SourceLocation dataclass — SDD §8.1。

为每种 source_type 定义精确的 source 位置格式。
不可变，所有字段为可选——仅设置与 source_type 相关的字段。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLocation:
    """卡片内容在源文件中的精确位置。

    根据 source_type，仅部分字段有值：
    - plain_markdown: heading_path, line_start, line_end
    - txt: line_start, line_end
    - html: heading_path, css_selector
    - pdf: page_number
    - docx: paragraph_start, paragraph_end
    """

    source_type: str
    heading_path: tuple[str, ...] | None = None
    line_start: int | None = None
    line_end: int | None = None
    page_number: int | None = None
    paragraph_start: int | None = None
    paragraph_end: int | None = None
    css_selector: str | None = None

    def to_display(self) -> str:
        if self.source_type == "plain_markdown":
            return _display_markdown(self)
        if self.source_type == "txt":
            return _display_txt(self)
        if self.source_type == "html":
            return _display_html(self)
        if self.source_type == "pdf":
            return _display_pdf(self)
        if self.source_type == "docx":
            return _display_docx(self)
        return "Source file"


def _display_markdown(loc: SourceLocation) -> str:
    parts: list[str] = []
    if loc.heading_path:
        parts.append("§ " + " > ".join(loc.heading_path))
    if loc.line_start is not None or loc.line_end is not None:
        start = loc.line_start if loc.line_start is not None else "?"
        end = loc.line_end if loc.line_end is not None else "?"
        parts.append(f"lines {start}-{end}")
    return ", ".join(parts) if parts else "Source file"


def _display_txt(loc: SourceLocation) -> str:
    if loc.line_start is not None or loc.line_end is not None:
        start = loc.line_start if loc.line_start is not None else "?"
        end = loc.line_end if loc.line_end is not None else "?"
        return f"Lines {start}-{end}"
    return "Source file"


def _display_html(loc: SourceLocation) -> str:
    parts: list[str] = []
    if loc.heading_path:
        parts.append(" > ".join(loc.heading_path))
    if loc.css_selector:
        parts.append(loc.css_selector)
    return ", ".join(parts) if parts else "Source file"


def _display_pdf(loc: SourceLocation) -> str:
    if loc.page_number is not None:
        return f"Page {loc.page_number}"
    return "Source file"


def _display_docx(loc: SourceLocation) -> str:
    if loc.paragraph_start is not None or loc.paragraph_end is not None:
        start = loc.paragraph_start if loc.paragraph_start is not None else "?"
        end = loc.paragraph_end if loc.paragraph_end is not None else "?"
        return f"Paragraphs {start}-{end}"
    return "Source file"
