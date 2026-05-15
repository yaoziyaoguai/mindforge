"""M1 Phase P7 — dry-run integration seam 契约测试。

测试 v0.2 source-layer dry-run helper：
- classify_source_path：路径分类（不调用 load）
- preview_source_load：显式 opt-in 预览加载（调用 load）
- 默认使用 create_default_registry()
- 不改变 import/watch/process 主链路默认行为

RFC_0001 §5.3 / §5.4 — AdapterRegistry dispatch + AdapterResult contract。
"""

from __future__ import annotations

import pytest


def _module_has_attr(module_name: str, attr: str) -> bool:
    try:
        import importlib

        mod = importlib.import_module(module_name)
        return hasattr(mod, attr)
    except ImportError:
        return False


_DRY_RUN_EXISTS = _module_has_attr("mindforge.sources.dry_run", "classify_source_path")


# =============================================================================
# A. classify_source_path — 路径分类
# =============================================================================


@pytest.mark.xfail(
    not _DRY_RUN_EXISTS,
    reason="v0.2 dry_run seam 尚未实现——预期 Red。Phase P7 实现后应 Green。",
    strict=True,
)
class TestClassifySourcePath:
    """classify_source_path 路径分类契约。

    纯查询：不调用 adapter.load、不读文件内容、不处理 secrets。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.dry_run import classify_source_path

        self.classify_source_path = classify_source_path

    # -- Markdown 匹配 -------------------------------------------------------

    @pytest.mark.parametrize("path", ["note.md", "NOTE.MD", "path/to/file.md"])
    def test_returns_matched_for_md(self, path: str) -> None:
        """classify_source_path 对 .md 文件应返回 matched。"""
        result = self.classify_source_path(path)
        assert result["matched"] is True
        assert result["status"] == "matched"
        assert result["adapter_name"] == "PlainMarkdownAdapter"
        assert result["source_type"] == "plain_markdown"
        assert result["path"] == path

    def test_returns_matched_for_markdown(self) -> None:
        """classify_source_path 对 .markdown 文件应返回 matched。"""
        result = self.classify_source_path("note.markdown")
        assert result["matched"] is True
        assert result["source_type"] == "plain_markdown"

    # -- TXT 匹配 ------------------------------------------------------------

    @pytest.mark.parametrize("path", ["note.txt", "NOTE.TXT", "path/to/file.txt"])
    def test_returns_matched_for_txt(self, path: str) -> None:
        """classify_source_path 对 .txt 文件应返回 matched（M2 TXT adapter）。"""
        result = self.classify_source_path(path)
        assert result["matched"] is True
        assert result["status"] == "matched"
        assert result["adapter_name"] == "TxtAdapter"
        assert result["source_type"] == "txt"
        assert result["path"] == path

    # -- 不支持的格式返回 unsupported ----------------------------------------

    # -- HTML 匹配 ------------------------------------------------------------

    @pytest.mark.parametrize("path", ["page.html", "PAGE.HTM", "path/to/file.html"])
    def test_returns_matched_for_html(self, path: str) -> None:
        """classify_source_path 对 .html/.htm 文件应返回 matched（M2 HTML adapter）。"""
        result = self.classify_source_path(path)
        assert result["matched"] is True
        assert result["status"] == "matched"
        assert result["adapter_name"] == "HtmlAdapter"
        assert result["source_type"] == "html"
        assert result["path"] == path

    # -- PDF 匹配 ------------------------------------------------------------

    def test_returns_matched_for_pdf(self) -> None:
        """classify_source_path 对 .pdf 文件应返回 matched（M3 PDF adapter）。"""
        result = self.classify_source_path("doc.pdf")
        assert result["matched"] is True
        assert result["status"] == "matched"
        assert result["adapter_name"] == "PdfTextAdapter"
        assert result["source_type"] == "pdf"

    # -- 不支持的格式返回 unsupported ----------------------------------------

    @pytest.mark.parametrize("path", [
        "report.docx", "data.csv",
    ])
    def test_returns_unsupported_for_other_formats(self, path: str) -> None:
        """不支持的格式应返回 unsupported summary。"""
        result = self.classify_source_path(path)
        assert result["matched"] is False
        assert result["status"] == "unsupported"
        assert result["adapter_name"] is None
        assert result["source_type"] is None
        assert result["path"] == path

    # -- 不调用 load --------------------------------------------------------

    def test_does_not_call_adapter_load(self) -> None:
        """classify_source_path 必须不调用 adapter.load。

        仅通过 registry.find_for_path → adapter.can_handle 判断，
        不加载文件内容。
        """
        result = self.classify_source_path("nonexistent.md")
        # 即使文件不存在，classify 也应返回 matched（它只看路径命名）
        assert result["matched"] is True
        assert result["source_type"] == "plain_markdown"

    # -- 返回 dict 结构完整性 ------------------------------------------------

    def test_result_has_expected_keys(self) -> None:
        """返回的 dict 必须包含所有契约字段。"""
        result = self.classify_source_path("note.md")
        expected_keys = {"matched", "status", "adapter_name", "source_type", "path"}
        assert set(result.keys()) == expected_keys


# =============================================================================
# B. preview_source_load — 显式 opt-in 预览加载
# =============================================================================


@pytest.mark.xfail(
    not _DRY_RUN_EXISTS,
    reason="v0.2 dry_run seam 尚未实现——预期 Red。",
    strict=True,
)
class TestPreviewSourceLoad:
    """preview_source_load 显式 opt-in 预览加载契约。

    调用 adapter.load(path)，返回 AdapterResult。
    仅供 tests / future CLI opt-in seam 使用，不接入默认主链路。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.dry_run import preview_source_load

        self.preview_source_load = preview_source_load

    # -- loaded -------------------------------------------------------------

    def test_loaded_for_valid_md(self, tmp_path) -> None:
        """合法 .md 文件应返回 AdapterResult.loaded。"""

        md = tmp_path / "note.md"
        md.write_text("# Hello\n\nWorld.\n", encoding="utf-8")
        result = self.preview_source_load(str(md))
        assert result.status == "loaded"
        assert result.document is not None
        assert result.document.source_type == "plain_markdown"

    def test_loaded_document_preserves_raw_text(self, tmp_path) -> None:
        """loaded document 应保留原文内容。"""

        md = tmp_path / "note.md"
        md.write_text("# Title\n\nBody paragraph.", encoding="utf-8")
        result = self.preview_source_load(str(md))
        assert result.document.raw_text == "# Title\n\nBody paragraph."

    def test_loaded_document_has_content_hash(self, tmp_path) -> None:
        """loaded document.content_hash 应非空且带 sha256: 前缀。"""

        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.preview_source_load(str(md))
        assert result.document.content_hash.startswith("sha256:")

    def test_loaded_document_extraction_warnings_empty(self, tmp_path) -> None:
        """正常 Markdown 的 extraction_warnings 应为空。"""

        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.preview_source_load(str(md))
        assert result.document.extraction_warnings == []

    def test_loaded_document_provenance_blocks_empty(self, tmp_path) -> None:
        """正常 Markdown 的 provenance_blocks 应为空。"""

        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.preview_source_load(str(md))
        assert result.document.provenance_blocks == []

    # -- skipped ------------------------------------------------------------

    def test_skipped_for_unsupported_suffix(self, tmp_path) -> None:
        """不支持格式应返回 AdapterResult.skipped。"""

        f = tmp_path / "test.xyz"
        f.write_text("content", encoding="utf-8")
        result = self.preview_source_load(str(f))
        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason is not None

    # -- failed -------------------------------------------------------------

    def test_failed_for_missing_file(self) -> None:
        """不存在的 .md 文件应返回 AdapterResult.failed。"""
        result = self.preview_source_load("/tmp/nonexistent_xyz789.md")
        assert result.status == "failed"
        assert result.document is None
        assert result.error_message is not None
        assert "nonexistent_xyz789" in result.error_message


# =============================================================================
# C. 默认 registry 使用
# =============================================================================


@pytest.mark.xfail(
    not _DRY_RUN_EXISTS,
    reason="v0.2 dry_run seam 尚未实现——预期 Red。",
    strict=True,
)
class TestDryRunDefaultRegistry:
    """dry-run seam 默认使用 create_default_registry()。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.dry_run import classify_source_path, preview_source_load

        self.classify_source_path = classify_source_path
        self.preview_source_load = preview_source_load

    def test_classify_default_registry_markdown_txt_html_pdf(self) -> None:
        """默认 registry 支持 Markdown + TXT + HTML + PDF（M2/M3 实现）。"""
        assert self.classify_source_path("note.md")["matched"] is True
        assert self.classify_source_path("note.txt")["matched"] is True
        assert self.classify_source_path("page.html")["matched"] is True
        assert self.classify_source_path("doc.pdf")["matched"] is True
        assert self.classify_source_path("report.docx")["matched"] is False

    def test_preview_default_registry_supported_formats(self, tmp_path) -> None:
        """默认 registry preview 支持 Markdown + TXT + HTML。PDF 需要 pypdf runtime。"""

        md = tmp_path / "note.md"
        md.write_text("# Hi", encoding="utf-8")
        assert self.preview_source_load(str(md)).status == "loaded"

        txt = tmp_path / "note.txt"
        txt.write_text("text", encoding="utf-8")
        assert self.preview_source_load(str(txt)).status == "loaded"

        html = tmp_path / "page.html"
        html.write_text("<html><body><h1>Hi</h1></body></html>", encoding="utf-8")
        assert self.preview_source_load(str(html)).status == "loaded"


# =============================================================================
# D. 注入 custom registry 用于测试
# =============================================================================


@pytest.mark.xfail(
    not _DRY_RUN_EXISTS,
    reason="v0.2 dry_run seam 尚未实现——预期 Red。",
    strict=True,
)
class TestDryRunWithCustomRegistry:
    """dry-run seam 接受注入 registry 用于测试隔离。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.dry_run import classify_source_path

        self.classify_source_path = classify_source_path

    def test_accepts_injected_registry(self) -> None:
        """classify_source_path 应接受 external registry。"""
        from mindforge.sources.registry import AdapterRegistry
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        reg = AdapterRegistry()
        reg.register(PlainMarkdownAdapter())
        result = self.classify_source_path("note.md", registry=reg)
        assert result["matched"] is True

    def test_injected_registry_overrides_default(self) -> None:
        """注入空 registry 应导致所有路径返回 unsupported。"""
        from mindforge.sources.registry import AdapterRegistry

        empty_reg = AdapterRegistry()
        result = self.classify_source_path("note.md", registry=empty_reg)
        assert result["matched"] is False


# =============================================================================
# E. 安全 / 边界守卫
# =============================================================================


@pytest.mark.xfail(
    not _DRY_RUN_EXISTS,
    reason="v0.2 dry_run seam 尚未实现——预期 Red。",
    strict=True,
)
class TestDryRunSafety:
    """dry-run seam 安全边界。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.dry_run import classify_source_path, preview_source_load

        self.classify_source_path = classify_source_path
        self.preview_source_load = preview_source_load

    def test_classify_does_not_read_files(self) -> None:
        """classify 不应读文件内容（即使路径不存在也能返回 matched）。"""
        result = self.classify_source_path("/nonexistent/path/note.md")
        assert result["matched"] is True

    def test_classify_does_not_read_env(self) -> None:
        """classify 不应依赖环境变量。"""
        result = self.classify_source_path("note.md")
        assert result["matched"] is True

    def test_preview_does_not_read_env_for_unsupported(self, tmp_path) -> None:
        """preview 对不支持格式不应依赖环境变量。"""

        f = tmp_path / "test.xyz"
        f.write_text("content", encoding="utf-8")
        result = self.preview_source_load(str(f))
        assert result.status == "skipped"
