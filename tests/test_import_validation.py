"""v2.4 U5 Import Validation tests — 导入安全校验。

中文学习型说明：验证导入管线的安全边界 —— 拒绝空标题/空内容、
拒绝系统路径、校验 frontmatter 合法性。
所有测试使用合成数据，不调用 LLM、不访问真实文件。

v4.8 Slice 3: 方法已从 WebFacade 移至 WebImportExportService。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mindforge_web.services.web_import_export_service import WebImportExportService


class TestParseMarkdownTitleBody:
    """_parse_markdown_title_body 静态方法测试。"""

    def test_extracts_yaml_title(self):
        """从 YAML frontmatter 提取 title。"""
        raw = "---\ntitle: Hello World\ntags: [a]\n---\n\nBody content here."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "test.md")
        assert title == "Hello World"
        assert "Body content here" in body

    def test_extracts_yaml_title_with_space(self):
        """YAML key 后有空格的 title : value 格式。"""
        raw = "---\ntitle :  Test Card  \n---\nBody."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "test.md")
        assert title == "Test Card"

    def test_extracts_yaml_title_quoted(self):
        """双引号内的 title。"""
        raw = '---\ntitle: "Quoted Title"\n---\nBody.'
        title, body = WebImportExportService._parse_markdown_title_body(raw, "test.md")
        assert title == "Quoted Title"

    def test_falls_back_to_h1_heading(self):
        """无 YAML title 时 fallback 到 # heading。"""
        raw = "# My Heading\n\nSome content."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "test.md")
        assert title == "My Heading"

    def test_falls_back_to_filename(self):
        """既无 YAML title 也无 # heading 时 fallback 到文件名。"""
        raw = "Just some markdown content without a heading."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "my-cool-note.md")
        assert title == "my cool note"

    def test_falls_back_to_filename_with_underscores(self):
        raw = "Just content."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "learning_notes_2025.md")
        assert title == "learning notes 2025"

    def test_ignores_h2_and_deeper_headings(self):
        """只认 # heading，不认 ## 或更深。"""
        raw = "## Sub heading\n# Real Title\n\nContent."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "test.md")
        assert title == "Real Title"

    def test_empty_raw_returns_filename_title(self):
        raw = ""
        title, body = WebImportExportService._parse_markdown_title_body(raw, "empty.md")
        assert title == "empty"

    def test_body_excludes_frontmatter(self):
        """提取的 body 不包含 frontmatter。"""
        raw = "---\ntitle: Card\n---\nActual content here."
        title, body = WebImportExportService._parse_markdown_title_body(raw, "test.md")
        assert "---" not in body
        assert "title:" not in body
        assert body == "Actual content here."


class TestFolderImportSecurity:
    """文件夹导入安全检查测试。"""

    def test_rejects_hidden_files(self):
        """隐藏文件（. 开头）应被过滤。"""
        is_rejected = any(
            p(".hidden.md") for p in WebImportExportService._REJECTED_FILENAME_PATTERNS
        )
        assert is_rejected

    def test_rejects_ds_store(self):
        """macOS .DS_Store 应被过滤。"""
        is_rejected = any(
            p(".DS_Store") for p in WebImportExportService._REJECTED_FILENAME_PATTERNS
        )
        assert is_rejected

    def test_rejects_non_markdown(self):
        """非 .md 文件应被过滤。"""
        is_rejected = any(
            p("notes.txt") for p in WebImportExportService._REJECTED_FILENAME_PATTERNS
        )
        assert is_rejected

    def test_allows_valid_markdown(self):
        """合法 .md 文件不被过滤。"""
        is_rejected = any(
            p("valid-note.md") for p in WebImportExportService._REJECTED_FILENAME_PATTERNS
        )
        assert not is_rejected

    def test_max_file_size_limit(self):
        """MAX_IMPORT_FILE_BYTES 应为合理值。"""
        assert WebImportExportService._MAX_IMPORT_FILE_BYTES == 1_048_576


class TestDedupDetection:
    """v2.4 U2 去重检测逻辑测试。

    _find_duplicates 通过 iter_cards 查询已有卡片，使用 mock cfg + mock iter_cards。
    """

    @staticmethod
    def _make_service():
        """创建带 mock config 的最小可用 service。"""
        cfg = MagicMock()
        return WebImportExportService(cfg)

    def test_empty_title_no_duplicates(self):
        """空标题应返回空列表。"""
        svc = self._make_service()
        with patch("mindforge_web.services.web_import_export_service.iter_cards", return_value=[]):
            dups = svc._find_duplicates("")
            assert dups == []

    def test_no_cards_no_duplicates(self):
        """无卡片时 _find_duplicates 返回空列表。"""
        svc = self._make_service()
        with patch("mindforge_web.services.web_import_export_service.iter_cards", return_value=[]):
            dups = svc._find_duplicates("Some Unique Title")
            assert isinstance(dups, list)
            assert dups == []
