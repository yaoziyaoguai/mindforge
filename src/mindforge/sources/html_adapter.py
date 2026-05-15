"""v0.2 HtmlAdapter — 本地 HTML 文件的 SourceAdapter。

RFC_0001 §5.7 要求 HTML adapter 剥离 script/style、提取 title/headings/links/
lists、保留 Markdown-ish 文本，且仅处理本地文件。本实现使用标准库
``html.parser.HTMLParser``，不做 URL crawling、不执行 script、不引入重依赖。

设计边界：不接 processor/approval/wiki；所有跳过通过 AdapterResult 表达。
"""

from __future__ import annotations

import hashlib
from html.parser import HTMLParser
from pathlib import Path

from mindforge.sources.adapter_result import (
    AdapterResult,
    ExtractionWarning,
    ProvenanceBlock,
    SkipReason,
)
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.sources.source_adapter import SourceAdapter

_MAX_HTML_BYTES = 50 * 1024 * 1024


class _HtmlToMarkdownParser(HTMLParser):
    """将 HTML 解析为 Markdown-ish 文本，保留 headings/links/lists。

    中文学习型说明：stdlib HTMLParser 是事件驱动 SAX 风格解析器，
    不构建完整 DOM。对 malformed HTML 有 best-effort 容错能力。
    所有 I/O 和格式决策都在此 parser 外处理。
    """

    def __init__(self) -> None:
        super().__init__()
        self._output: list[str] = []
        self._skip_depth = 0  # 嵌套 script/style 深度计数
        self._in_skip = False  # 是否正在跳过 script/style 内容
        self._list_depth = 0
        self._title_text: str | None = None
        self._in_title = False
        self._tag_count = 0
        self._text_chars = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag_lower in ("script", "style"):
            self._in_skip = True
            self._skip_depth += 1
            return

        if self._in_skip:
            self._skip_depth += 1
            return

        self._tag_count += 1

        if tag_lower == "title":
            self._in_title = True
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag_lower[1])
            self._output.append("\n" + "#" * level + " ")
        elif tag_lower == "p":
            self._output.append("\n\n")
        elif tag_lower == "br":
            self._output.append("\n")
        elif tag_lower == "li":
            self._output.append("\n" + "  " * max(self._list_depth - 1, 0) + "- ")
        elif tag_lower in ("ul", "ol"):
            self._list_depth += 1
        elif tag_lower == "a":
            href = attrs_dict.get("href", "")
            if href:
                self._output.append("[")
                self._href = href
        elif tag_lower in ("blockquote",):
            self._output.append("\n> ")
        elif tag_lower == "hr":
            self._output.append("\n\n---\n")
        elif tag_lower == "table":
            self._output.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        if tag_lower in ("script", "style"):
            self._skip_depth -= 1
            if self._skip_depth <= 0:
                self._in_skip = False
                self._skip_depth = 0
            return

        if self._in_skip:
            self._skip_depth -= 1
            if self._skip_depth <= 0:
                self._in_skip = False
                self._skip_depth = 0
            return

        if tag_lower == "title":
            self._in_title = False
        elif tag_lower in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._output.append("\n")
        elif tag_lower in ("ul", "ol"):
            self._list_depth = max(self._list_depth - 1, 0)
        elif tag_lower == "a":
            href = getattr(self, "_href", "")
            if href:
                self._output.append(f"]({href})")
                self._href = ""

    def handle_data(self, data: str) -> None:
        if self._in_skip:
            return

        stripped = data.strip()
        if not stripped:
            return

        self._text_chars += len(stripped)

        if self._in_title:
            self._title_text = (self._title_text or "") + stripped
        else:
            self._output.append(stripped)

    def get_title(self) -> str | None:
        return self._title_text.strip() if self._title_text else None

    def get_body(self) -> str:
        raw = "".join(self._output)
        raw = raw.strip()
        # 规整多余空行
        import re

        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw

    def tag_to_text_ratio(self) -> float:
        """标签文本比 = 提取文本字符数 / 标签数。低比值表示 noisy HTML。"""
        if self._tag_count == 0:
            return 1.0
        return self._text_chars / self._tag_count


class HtmlAdapter(SourceAdapter):
    """把本地 ``.html`` / ``.htm`` 文件解析为 ``SourceDocument``。

    设计边界：
    - 仅处理本地文件（不 fetch URL）
    - 剥离 script/style 标签及内容
    - 保留 headings/links/lists 为 Markdown-ish 文本
    - 不执行 JavaScript、不加载外部资源
    - 所有正常跳过通过 AdapterResult 表达
    """

    name = "HtmlAdapter"
    source_type = "html"

    def can_handle(self, path: str) -> bool:
        return Path(path).suffix.lower() in (".html", ".htm")

    def load(self, path: str) -> AdapterResult:
        p = Path(path)

        if not p.exists():
            return AdapterResult(
                status="failed",
                error_message=f"FileNotFoundError: {p}",
            )

        try:
            size = p.stat().st_size
        except OSError as exc:
            return AdapterResult(
                status="failed",
                error_message=f"{type(exc).__name__}: {p}",
            )

        if size > _MAX_HTML_BYTES:
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.FILE_TOO_LARGE,
            )

        try:
            raw_html = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.DECODE_ERROR,
            )
        except OSError as exc:
            return AdapterResult(
                status="failed",
                error_message=f"{type(exc).__name__}: {p}",
            )

        parser = _HtmlToMarkdownParser()
        try:
            parser.feed(raw_html)
        except Exception:
            # malformed HTML → best-effort, 用已解析内容
            pass

        body = parser.get_body()
        warnings: list[ExtractionWarning] = []

        if not body.strip():
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.EMPTY_FILE,
            )

        # Noisy HTML detection（RFC_0001 §5.7：标签占比过高时 warning）
        if parser.tag_to_text_ratio() < 0.5:
            warnings.append(
                ExtractionWarning(
                    code="noisy_html",
                    message="HTML contains high tag-to-text ratio; "
                    "extracted content may be sparse.",
                )
            )

        title = parser.get_title() or _first_heading(body) or p.stem

        provenance_blocks = [
            ProvenanceBlock(source_type=self.source_type, extracted_as="text")
        ]

        document = SourceDocument(
            source_id="sha1:" + hashlib.sha1(str(p).encode("utf-8")).hexdigest(),
            source_type=self.source_type,
            source_path=str(p),
            title=title,
            raw_text=body,
            metadata={},
            content_hash=compute_content_hash(body, {"title": title}),
            adapter_name=self.name,
            extraction_warnings=list(warnings),
            provenance_blocks=provenance_blocks,
        )

        return AdapterResult(status="loaded", document=document, warnings=warnings)


def _first_heading(body: str) -> str | None:
    """从 Markdown body 中提取第一个 heading 文本。"""
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


__all__ = ["HtmlAdapter"]
