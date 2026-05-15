"""M4 Phase P1-P3 — DocxTextAdapter 单元测试。

测试 DocxTextAdapter 的 v0.2 行为：
- can_handle / load 契约（返回 AdapterResult）
- heading style → Markdown heading
- paragraphs → 保留段落结构
- tables → Markdown table
- extraction_warnings（table_loss）
- 空文档 → skipped
- 文件不存在 → failed
- 不执行宏 / 不读 secrets

使用 mock python-docx 避免创建真实 .docx 文件。
python-docx 已在 pyproject.toml 中声明为可选依赖。

RFC_0001 §5.9 / SDD §11 M4 Phase P1-P3。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _module_has_attr(module_name: str, attr: str) -> bool:
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return hasattr(mod, attr)
    except ImportError:
        return False


_DOCX_ADAPTER_EXISTS = _module_has_attr(
    "mindforge.sources.docx_adapter", "DocxTextAdapter"
)


def _make_mock_paragraph(text: str, style_name: str = "Normal"):
    """创建模拟 docx paragraph。"""
    para = MagicMock()
    para.text = text
    style = MagicMock()
    style.name = style_name
    para.style = style
    return para


def _make_mock_table(rows: list[list[str]]):
    """创建模拟 docx table。"""
    table = MagicMock()
    mock_rows = []
    for row_data in rows:
        row = MagicMock()
        cells = [MagicMock() for _ in row_data]
        for cell, text in zip(cells, row_data):
            cell.text = text
        row.cells = cells
        mock_rows.append(row)
    table.rows = mock_rows
    return table


# =============================================================================
# A. 基本契约测试（不需要 python-docx runtime）
# =============================================================================


@pytest.mark.xfail(
    not _DOCX_ADAPTER_EXISTS,
    reason="DocxTextAdapter 尚未实现——预期 Red。M4 Phase P1-P3 实现后 Green。",
    strict=True,
)
class TestDocxTextAdapterBasic:
    """DocxTextAdapter 基本契约。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.docx_adapter import DocxTextAdapter
        self.adapter = DocxTextAdapter()

    def test_can_handle_docx(self) -> None:
        assert self.adapter.can_handle("doc.docx") is True
        assert self.adapter.can_handle("DOC.DOCX") is True

    def test_can_handle_rejects_non_docx(self) -> None:
        assert self.adapter.can_handle("note.txt") is False
        assert self.adapter.can_handle("page.html") is False
        assert self.adapter.can_handle("file.doc") is False  # legacy .doc
        assert self.adapter.can_handle("file.docx") is True

    def test_name(self) -> None:
        assert self.adapter.name == "DocxTextAdapter"

    def test_source_type(self) -> None:
        assert self.adapter.source_type == "docx"

    def test_load_returns_failed_for_missing_file(self) -> None:
        result = self.adapter.load("/tmp/nonexistent_docx_xyz789.docx")
        assert result.status == "failed"
        assert result.document is None
        assert result.error_message is not None


# =============================================================================
# B. load() 行为测试（mock python-docx）
# =============================================================================


@pytest.mark.xfail(
    not _DOCX_ADAPTER_EXISTS,
    reason="DocxTextAdapter 尚未实现。",
    strict=True,
)
class TestDocxTextAdapterLoad:
    """DocxTextAdapter.load() 完整行为（mock python-docx）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.docx_adapter import DocxTextAdapter
        self.adapter = DocxTextAdapter()

    def test_load_simple_paragraphs(self, tmp_path: Path) -> None:
        """简单段落文档 → loaded。"""
        p = tmp_path / "test.docx"
        p.write_text("dummy", encoding="utf-8")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            _make_mock_paragraph("First paragraph."),
            _make_mock_paragraph("Second paragraph."),
        ]
        mock_doc.tables = []
        mock_doc.core_properties = None

        mock_docx = MagicMock()
        mock_docx.Document = MagicMock(return_value=mock_doc)

        import sys

        with patch.dict(sys.modules, {"docx": mock_docx}):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        assert result.document is not None
        assert "First paragraph" in result.document.raw_text
        assert "Second paragraph" in result.document.raw_text

    def test_load_headings_structure(self, tmp_path: Path) -> None:
        """Heading style 段落 → Markdown heading。"""
        p = tmp_path / "test.docx"
        p.write_text("dummy", encoding="utf-8")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            _make_mock_paragraph("Introduction", "Heading 1"),
            _make_mock_paragraph("Some content.", "Normal"),
            _make_mock_paragraph("Details", "Heading 2"),
            _make_mock_paragraph("More details.", "Normal"),
        ]
        mock_doc.tables = []
        mock_doc.core_properties = None

        mock_docx = MagicMock()
        mock_docx.Document = MagicMock(return_value=mock_doc)

        import sys

        with patch.dict(sys.modules, {"docx": mock_docx}):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        text = result.document.raw_text
        assert "# Introduction" in text
        assert "## Details" in text

    def test_load_tables_to_markdown(self, tmp_path: Path) -> None:
        """表格 → Markdown table。"""
        p = tmp_path / "test.docx"
        p.write_text("dummy", encoding="utf-8")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            _make_mock_paragraph("Below is a table.", "Normal"),
        ]
        mock_doc.tables = [
            _make_mock_table([
                ["Name", "Age"],
                ["Alice", "30"],
                ["Bob", "25"],
            ]),
        ]
        mock_doc.core_properties = None

        mock_docx = MagicMock()
        mock_docx.Document = MagicMock(return_value=mock_doc)

        import sys

        with patch.dict(sys.modules, {"docx": mock_docx}):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        text = result.document.raw_text
        assert "| Name | Age |" in text
        assert "| Alice | 30 |" in text

    def test_load_empty_docx_skipped(self, tmp_path: Path) -> None:
        """无文本的 .docx → skipped。"""
        p = tmp_path / "empty.docx"
        p.write_text("dummy", encoding="utf-8")

        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.tables = []
        mock_doc.core_properties = None

        mock_docx = MagicMock()
        mock_docx.Document = MagicMock(return_value=mock_doc)

        import sys

        with patch.dict(sys.modules, {"docx": mock_docx}):
            result = self.adapter.load(str(p))
        assert result.status == "skipped"
        assert result.document is None

    def test_load_title_from_core_properties(self, tmp_path: Path) -> None:
        """应从 core_properties 提取 title。"""
        p = tmp_path / "test.docx"
        p.write_text("dummy", encoding="utf-8")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [_make_mock_paragraph("Content.")]
        mock_doc.tables = []
        cp = MagicMock()
        cp.title = "My Document Title"
        mock_doc.core_properties = cp

        mock_docx = MagicMock()
        mock_docx.Document = MagicMock(return_value=mock_doc)

        import sys

        with patch.dict(sys.modules, {"docx": mock_docx}):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        assert result.document.title == "My Document Title"

    def test_load_table_loss_warning(self, tmp_path: Path) -> None:
        """表格提取失败时应产生 warning。"""
        p = tmp_path / "test.docx"
        p.write_text("dummy", encoding="utf-8")

        mock_doc = MagicMock()
        mock_doc.paragraphs = [_make_mock_paragraph("Content.")]
        # table that raises on iteration
        bad_table = MagicMock()
        bad_table.rows = MagicMock()
        bad_table.rows.__iter__.side_effect = Exception("corrupt table")
        mock_doc.tables = [bad_table]
        mock_doc.core_properties = None

        mock_docx = MagicMock()
        mock_docx.Document = MagicMock(return_value=mock_doc)

        import sys

        with patch.dict(sys.modules, {"docx": mock_docx}):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        has_table_loss = any(
            w.code == "table_loss" for w in result.warnings
        )
        assert has_table_loss


# =============================================================================
# C. 安全 / boundary 测试
# =============================================================================


@pytest.mark.xfail(
    not _DOCX_ADAPTER_EXISTS,
    reason="DocxTextAdapter 尚未实现。",
    strict=True,
)
class TestDocxTextAdapterSafety:
    """DocxTextAdapter 安全边界。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.docx_adapter import DocxTextAdapter
        self.adapter = DocxTextAdapter()

    def test_load_does_not_read_env(self) -> None:
        result = self.adapter.load("/tmp/nonexistent_docx_xyz789.docx")
        assert result.status == "failed"

    def test_load_does_not_execute_macros(self) -> None:
        """DocxTextAdapter 绝不执行宏。"""
        # 不 import win32com 或其他宏执行库
        import sys
        assert "win32com" not in sys.modules

    def test_load_legacy_doc_rejected(self) -> None:
        """Legacy .doc 应被 can_handle 拒绝。"""
        assert self.adapter.can_handle("legacy.doc") is False

    def test_load_returns_failed_for_nonexistent(self) -> None:
        result = self.adapter.load("/nonexistent/test.docx")
        assert result.status == "failed"
        assert result.error_message is not None
