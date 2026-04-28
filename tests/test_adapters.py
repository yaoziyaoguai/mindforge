"""PlainMarkdownAdapter / CuboxMarkdownAdapter / stubs 单测。

使用 ``tests/fixtures/`` 下的真实 .md 文件作为输入，验证：
- frontmatter 字段正确映射；
- raw_text 不含 frontmatter；
- content_hash 稳定；
- Cubox highlights 段被正确拆出；
- stubs 抛 NotImplementedError。
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mindforge.sources.cubox_markdown import CuboxMarkdownAdapter
from mindforge.sources.plain_markdown import PlainMarkdownAdapter
from mindforge.sources.stubs import (
    ChatExportAdapter,
    DocxAdapter,
    PdfAdapter,
    WebClipMarkdownAdapter,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Plain Markdown
# ---------------------------------------------------------------------------


def test_plain_markdown_loads_frontmatter() -> None:
    adapter = PlainMarkdownAdapter()
    doc = adapter.load(str(FIXTURES / "sample_plain_note.md"))
    assert doc.source_type == "plain_markdown"
    assert doc.title == "Sample Plain Note"
    assert doc.author == "me"
    assert "note" in doc.tags
    assert doc.raw_text.startswith("# Sample Plain Note")
    assert "frontmatter" in doc.metadata
    assert doc.content_hash.startswith("sha256:")


def test_plain_markdown_can_handle() -> None:
    a = PlainMarkdownAdapter()
    assert a.can_handle("x.md")
    assert not a.can_handle("x.pdf")


def test_plain_markdown_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        PlainMarkdownAdapter().load("/tmp/__definitely_not_exist__.md")


def test_plain_markdown_hash_stable() -> None:
    a = PlainMarkdownAdapter()
    d1 = a.load(str(FIXTURES / "sample_plain_note.md"))
    d2 = a.load(str(FIXTURES / "sample_plain_note.md"))
    assert d1.content_hash == d2.content_hash


# ---------------------------------------------------------------------------
# Cubox Markdown
# ---------------------------------------------------------------------------


def test_cubox_markdown_loads_frontmatter_and_highlights() -> None:
    adapter = CuboxMarkdownAdapter()
    doc = adapter.load(str(FIXTURES / "sample_cubox_note.md"))
    assert doc.source_type == "cubox_markdown"
    assert doc.title == "ReAct Loop 中加 checkpoint 的两种方式"
    assert doc.source_url == "https://example.com/post/react-checkpoint"
    assert doc.author == "Some Author"
    assert "agent" in doc.tags
    assert doc.created_at is not None
    assert doc.captured_at is not None
    # raw_text 不含 frontmatter
    assert not doc.raw_text.lstrip().startswith("---")
    # highlights
    assert len(doc.highlights) == 3
    assert "step-level" in doc.highlights[0].text
    assert doc.highlights[0].note and "我自己的批注" in doc.highlights[0].note
    # 后两条没有 note
    assert doc.highlights[1].note is None
    assert doc.highlights[2].note is None


def test_cubox_markdown_hash_changes_when_url_changes(tmp_path: Path) -> None:
    """虽然 raw_text 一样，但关键 metadata 变化也应改变 hash。"""
    src = (FIXTURES / "sample_cubox_note.md").read_text(encoding="utf-8")
    p1 = tmp_path / "a.md"
    p1.write_text(src, encoding="utf-8")
    p2 = tmp_path / "b.md"
    p2.write_text(src.replace("react-checkpoint", "react-checkpoint-v2"), encoding="utf-8")

    a = CuboxMarkdownAdapter()
    d1 = a.load(str(p1))
    d2 = a.load(str(p2))
    assert d1.content_hash != d2.content_hash


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cls,expected_type",
    [
        (WebClipMarkdownAdapter, "webclip_markdown"),
        (PdfAdapter, "pdf"),
        (DocxAdapter, "docx"),
        (ChatExportAdapter, "chat_export"),
    ],
)
def test_stub_load_raises_not_implemented(cls, expected_type) -> None:
    a = cls()
    assert a.source_type == expected_type
    assert a.can_handle("x") is False
    with pytest.raises(NotImplementedError, match="v0.1"):
        a.load("/tmp/whatever")
