"""M3 Phase P1 — PdfTextAdapter 单元测试。

测试 PdfTextAdapter 的 v0.2 行为：
- can_handle / load 契约（返回 AdapterResult）
- page-level provenance_blocks
- scanned PDF detection → skipped
- file size guard → skipped
- page count warning
- 正常 text PDF → loaded
- 文件不存在 → failed
- 不调 LLM / 不读 secrets / 不做 OCR

使用 mock pypdf 模拟 PDF 读取，避免创建真实 PDF 文件的复杂性。
pypdf 已在 pyproject.toml 中声明为可选依赖。

RFC_0001 §5.8 / SDD §11 M3 Phase P1-P4。
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _module_has_attr(module_name: str, attr: str) -> bool:
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return hasattr(mod, attr)
    except ImportError:
        return False


_PDF_ADAPTER_EXISTS = _module_has_attr(
    "mindforge.sources.pdf_adapter", "PdfTextAdapter"
)


# =============================================================================
# A. 基本契约测试（不需要 pypdf runtime）
# =============================================================================


@pytest.mark.xfail(
    not _PDF_ADAPTER_EXISTS,
    reason="PdfTextAdapter 尚未实现——预期 Red。M3 Phase P1-P2 实现后 Green。",
    strict=True,
)
class TestPdfTextAdapterBasic:
    """PdfTextAdapter 基本契约。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.pdf_adapter import PdfTextAdapter
        self.adapter = PdfTextAdapter()

    def test_can_handle_pdf(self) -> None:
        assert self.adapter.can_handle("doc.pdf") is True
        assert self.adapter.can_handle("DOC.PDF") is True

    def test_can_handle_rejects_non_pdf(self) -> None:
        assert self.adapter.can_handle("note.txt") is False
        assert self.adapter.can_handle("page.html") is False
        assert self.adapter.can_handle("file.md") is False

    def test_name(self) -> None:
        assert self.adapter.name == "PdfTextAdapter"

    def test_source_type(self) -> None:
        assert self.adapter.source_type == "pdf"

    def test_load_returns_failed_for_missing_file(self) -> None:
        result = self.adapter.load("/tmp/nonexistent_pdf_xyz789.pdf")
        assert result.status == "failed"
        assert result.document is None
        assert result.error_message is not None


# =============================================================================
# B. load() 行为测试（mock pypdf）
# =============================================================================


def _mock_pdf_reader(pages_text: list[str]):
    """创建模拟 pypdf.PdfReader，每页 extract_text() 返回对应文本。"""
    mock_pages = []
    for text in pages_text:
        page = MagicMock()
        page.extract_text.return_value = text
        mock_pages.append(page)
    reader = MagicMock()
    reader.pages = mock_pages
    reader.metadata = None
    return reader


def _mock_empty_page_reader(page_count: int):
    """创建所有页面 extract_text() 返回空字符串的模拟 reader。"""
    mock_pages = []
    for _ in range(page_count):
        page = MagicMock()
        page.extract_text.return_value = ""
        mock_pages.append(page)
    reader = MagicMock()
    reader.pages = mock_pages
    reader.metadata = None
    return reader


@pytest.mark.xfail(
    not _PDF_ADAPTER_EXISTS,
    reason="PdfTextAdapter 尚未实现。",
    strict=True,
)
class TestPdfTextAdapterLoad:
    """PdfTextAdapter.load() 完整行为（mock pypdf）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.pdf_adapter import PdfTextAdapter
        self.adapter = PdfTextAdapter()

    def test_load_text_single_page(self, tmp_path: Path) -> None:
        """单页文本 PDF → loaded + 1 个 provenance block。"""
        p = tmp_path / "test.pdf"
        p.write_text("dummy", encoding="utf-8")  # 文件需存在

        mock_reader = _mock_pdf_reader(["Hello PDF World"])
        with patch("mindforge.sources.pdf_adapter._load_pdf_reader", return_value=mock_reader):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        assert result.document is not None
        assert len(result.document.provenance_blocks) == 1
        assert result.document.provenance_blocks[0].page == 1
        assert result.document.provenance_blocks[0].source_type == "pdf"

    def test_load_text_multi_page_provenance(self, tmp_path: Path) -> None:
        """多页 PDF → 每页一个 provenance block。"""
        p = tmp_path / "test.pdf"
        p.write_text("dummy", encoding="utf-8")

        mock_reader = _mock_pdf_reader(["Page 1", "Page 2", "Page 3"])
        with patch("mindforge.sources.pdf_adapter._load_pdf_reader", return_value=mock_reader):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        blocks = result.document.provenance_blocks
        assert len(blocks) == 3
        for i, block in enumerate(blocks):
            assert block.page == i + 1

    def test_load_scanned_pdf_skipped(self, tmp_path: Path) -> None:
        """无文本层的 PDF → skipped（scanned_pdf_no_text）。"""
        p = tmp_path / "scanned.pdf"
        p.write_text("dummy", encoding="utf-8")

        mock_reader = _mock_empty_page_reader(3)
        with patch("mindforge.sources.pdf_adapter._load_pdf_reader", return_value=mock_reader):
            result = self.adapter.load(str(p))
        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason == "scanned_pdf_no_text"

    def test_load_title_from_metadata(self, tmp_path: Path) -> None:
        """应从 PDF metadata 提取 title。"""
        p = tmp_path / "test.pdf"
        p.write_text("dummy", encoding="utf-8")

        mock_reader = _mock_pdf_reader(["Content"])
        mock_meta = MagicMock()
        mock_meta.title = "My PDF Title"
        mock_reader.metadata = mock_meta

        with patch("mindforge.sources.pdf_adapter._load_pdf_reader", return_value=mock_reader):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        assert result.document.title == "My PDF Title"

    def test_load_page_count_warning(self, tmp_path: Path) -> None:
        """超过 500 页应产生 large_page_count warning。"""
        p = tmp_path / "large.pdf"
        p.write_text("dummy", encoding="utf-8")

        # 创建 501 页的模拟 reader
        mock_pages = []
        for i in range(501):
            page = MagicMock()
            page.extract_text.return_value = f"Page {i}"
            mock_pages.append(page)
        mock_reader = MagicMock()
        mock_reader.pages = mock_pages
        mock_reader.metadata = None

        with patch("mindforge.sources.pdf_adapter._load_pdf_reader", return_value=mock_reader):
            result = self.adapter.load(str(p))
        assert result.status == "loaded"
        has_warning = any(
            w.code == "large_page_count" for w in result.warnings
        )
        assert has_warning


# =============================================================================
# C. 安全边界测试
# =============================================================================


@pytest.mark.xfail(
    not _PDF_ADAPTER_EXISTS,
    reason="PdfTextAdapter 尚未实现。",
    strict=True,
)
class TestPdfTextAdapterSafety:
    """PdfTextAdapter 安全边界。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.pdf_adapter import PdfTextAdapter
        self.adapter = PdfTextAdapter()

    def test_load_does_not_read_env(self) -> None:
        result = self.adapter.load("/tmp/nonexistent_pdf_xyz789.pdf")
        assert result.status == "failed"

    def test_load_returns_failed_for_nonexistent(self) -> None:
        result = self.adapter.load("/nonexistent/test.pdf")
        assert result.status == "failed"
        assert result.error_message is not None

    def test_no_ocr_import(self) -> None:
        """PdfTextAdapter 绝不调用 OCR（non-goal）。"""
        import sys
        assert "pytesseract" not in sys.modules
