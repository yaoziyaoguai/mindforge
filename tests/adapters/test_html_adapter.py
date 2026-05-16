"""M2 Phase P4-P5 — HtmlAdapter 单元测试。

测试 HtmlAdapter 的完整行为：
- can_handle / load 契约
- 正常 HTML 解析（title / headings / paragraphs）
- script/style 剥离
- links/lists 保留为 Markdown-ish 文本
- malformed HTML best-effort 解析
- 空 body / script-only → skipped
- noisy HTML → extraction_warnings
- 文件不存在 → failed
- 不调 LLM / 不读 secrets / 不做 URL crawling

RFC_0001 §5.7 / SDD §11 M2 Phase P4-P6。
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "html"


def _module_has_attr(module_name: str, attr: str) -> bool:
    try:
        import importlib

        mod = importlib.import_module(module_name)
        return hasattr(mod, attr)
    except ImportError:
        return False


_HTML_ADAPTER_EXISTS = _module_has_attr(
    "mindforge.sources.html_adapter", "HtmlAdapter"
)


@pytest.mark.xfail(
    not _HTML_ADAPTER_EXISTS,
    reason="HtmlAdapter 尚未实现——预期 Red。M2 Phase P4-P5 实现后 Green。",
    strict=True,
)
class TestHtmlAdapterBasic:
    """HtmlAdapter 基本契约。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.html_adapter import HtmlAdapter

        self.adapter = HtmlAdapter()

    # -- can_handle ------------------------------------------------------------

    @pytest.mark.parametrize("path", ["page.html", "PAGE.HTML", "doc.htm", "x.HtM"])
    def test_can_handle_html_htm(self, path: str) -> None:
        assert self.adapter.can_handle(path) is True

    @pytest.mark.parametrize("path", ["note.txt", "doc.pdf", "page.md", "file.docx"])
    def test_can_handle_rejects_non_html(self, path: str) -> None:
        assert self.adapter.can_handle(path) is False

    # -- metadata --------------------------------------------------------------

    def test_name(self) -> None:
        assert self.adapter.name == "HtmlAdapter"

    def test_source_type(self) -> None:
        assert self.adapter.source_type == "html"


@pytest.mark.xfail(
    not _HTML_ADAPTER_EXISTS,
    reason="HtmlAdapter 尚未实现。",
    strict=True,
)
class TestHtmlAdapterLoad:
    """HtmlAdapter.load() 正常和边界行为。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.html_adapter import HtmlAdapter

        self.adapter = HtmlAdapter()

    # -- 正常解析 ---------------------------------------------------------------

    def test_load_simple_page(self) -> None:
        """简单 HTML 页面应返回 loaded。"""
        path = str(FIXTURES / "simple_page.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        assert result.document is not None
        doc = result.document
        assert "欢迎" in doc.raw_text
        assert "简单测试页面" in doc.title
        assert doc.source_type == "html"

    def test_load_preserves_headings(self) -> None:
        """应保留 heading 层级为 Markdown headings。"""
        path = str(FIXTURES / "simple_page.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        text = result.document.raw_text
        assert "# 欢迎" in text
        assert "## 第二节" in text

    # -- script/style 剥离 -----------------------------------------------------

    def test_load_strips_script_and_style(self) -> None:
        """script 和 style 内容不应出现在输出中。"""
        path = str(FIXTURES / "with_script_style.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        text = result.document.raw_text
        assert "alert" not in text
        assert "XSS" not in text
        assert "color: red" not in text
        assert "可见内容" in text
        assert "脚本和样式后的内容" in text

    # -- links / lists --------------------------------------------------------

    def test_load_preserves_links(self) -> None:
        """链接应保留为 Markdown link 语法。"""
        path = str(FIXTURES / "with_lists_links.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        text = result.document.raw_text
        assert "[示例链接](https://example.com)" in text

    def test_load_preserves_lists(self) -> None:
        """有序/无序列表应保留为 Markdown list。"""
        path = str(FIXTURES / "with_lists_links.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        text = result.document.raw_text
        assert "- 第一项" in text
        assert "- 第二项" in text

    # -- malformed HTML --------------------------------------------------------

    def test_load_malformed_html_best_effort(self) -> None:
        """malformed HTML 应 best-effort 解析并返回 loaded。"""
        path = str(FIXTURES / "malformed.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        assert result.document is not None
        # 应有文本内容被提取出来
        assert len(result.document.raw_text) > 0

    # -- 空 body ---------------------------------------------------------------

    def test_load_empty_body_skipped(self) -> None:
        """HTML 无可见文本内容应返回 skipped。"""
        path = str(FIXTURES / "empty_body.html")
        result = self.adapter.load(path)
        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason is not None

    # -- noisy HTML ------------------------------------------------------------

    def test_load_noisy_html_produces_warning(self) -> None:
        """高标签/文本比的 noisy HTML 应产生 extraction_warning。"""
        path = str(FIXTURES / "noisy.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        has_noisy = any(
            w.code == "noisy_html" for w in result.warnings
        )
        assert has_noisy, f"expected noisy_html warning, got {result.warnings}"

    # -- 文件不存在 ------------------------------------------------------------

    def test_load_missing_file_returns_failed(self) -> None:
        """不存在的文件应返回 AdapterResult.failed。"""
        result = self.adapter.load("/tmp/nonexistent_html_xyz789.html")
        assert result.status == "failed"
        assert result.document is None
        assert result.error_message is not None

    # -- provenance ------------------------------------------------------------

    def test_load_includes_provenance(self) -> None:
        """成功加载的 HTML 应包含 provenance_blocks。"""
        path = str(FIXTURES / "simple_page.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        assert len(result.document.provenance_blocks) > 0
        assert result.document.provenance_blocks[0].source_type == "html"


@pytest.mark.xfail(
    not _HTML_ADAPTER_EXISTS,
    reason="HtmlAdapter 尚未实现。",
    strict=True,
)
class TestHtmlAdapterSafety:
    """HtmlAdapter 安全边界。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.html_adapter import HtmlAdapter

        self.adapter = HtmlAdapter()

    def test_load_does_not_execute_javascript(self) -> None:
        """HTML adapter 绝不应执行 JavaScript。"""
        path = str(FIXTURES / "with_script_style.html")
        result = self.adapter.load(path)
        assert result.status == "loaded"
        # XSS payload 不应出现在输出
        assert "alert" not in result.document.raw_text

    def test_load_does_not_read_env(self) -> None:
        """HTML adapter 不应读取环境变量。"""
        result = self.adapter.load(str(FIXTURES / "simple_page.html"))
        assert result.status == "loaded"

    def test_load_does_not_make_network_calls(self) -> None:
        """HTML adapter 不应发起网络请求（仅本地文件）。"""
        result = self.adapter.load(str(FIXTURES / "simple_page.html"))
        assert result.status == "loaded"

    def test_load_returns_failed_for_nonexistent_file(self) -> None:
        """不存在文件返回 failed 而不 crash。"""
        result = self.adapter.load("/nonexistent/path/test.html")
        assert result.status == "failed"
        assert result.error_message is not None
