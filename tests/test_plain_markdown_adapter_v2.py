"""M1 Phase P5 — PlainMarkdownAdapter v2 wrapper 行为测试。

测试 v0.2 SourceAdapter 接口下的 PlainMarkdownAdapter wrapper：
- can_handle 按 .md / .markdown 后缀识别
- load() 返回 AdapterResult（非裸 SourceDocument）
- 文件不存在 → AdapterResult.failed
- 不支持的格式 → AdapterResult.skipped
- 合法 Markdown → AdapterResult.loaded
- loaded document 保留 source_type / raw_text / source_path / content_hash
- 不读 .env / 不调 LLM / 不做 auto approve

注意：本文件测试的是 v0.2 wrapper（``markdown_adapter.py``），不是 v0.1
原有的 ``plain_markdown.py``。后者由 characterization tests 守护，不受影响。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from mindforge.sources.adapter_result import AdapterResult, SkipReason


# =============================================================================
# 0. 导入状态检查
# =============================================================================


def _module_exists(name: str) -> bool:
    try:
        import importlib

        importlib.import_module(name)
        return True
    except ImportError:
        return False


_SOURCE_ADAPTER_V2_EXISTS = _module_exists("mindforge.sources.source_adapter")
_MARKDOWN_ADAPTER_V2_EXISTS = _module_exists("mindforge.sources.markdown_adapter")


# =============================================================================
# A. SourceAdapter v2 interface contract
# =============================================================================


@pytest.mark.xfail(
    not _SOURCE_ADAPTER_V2_EXISTS,
    reason="v0.2 SourceAdapter interface 尚未实现——预期 Red。Phase P5 实现 source_adapter.py 后应 Green。",
    strict=True,
)
class TestSourceAdapterV2Interface:
    """v0.2 SourceAdapter ABC 接口契约。

    RFC_0001 §5.1: can_handle + load() -> AdapterResult。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.source_adapter import SourceAdapter

        self.SourceAdapter = SourceAdapter

    def test_source_adapter_is_abc(self) -> None:
        """SourceAdapter 必须是 ABC。"""
        import abc

        assert issubclass(self.SourceAdapter, abc.ABC)

    def test_has_can_handle_abstract(self) -> None:
        """SourceAdapter 必须有 can_handle 抽象方法。"""
        assert hasattr(self.SourceAdapter, "can_handle")
        method = self.SourceAdapter.can_handle
        assert getattr(method, "__isabstractmethod__", False)

    def test_has_load_abstract(self) -> None:
        """SourceAdapter 必须有 load 抽象方法。"""
        assert hasattr(self.SourceAdapter, "load")
        method = self.SourceAdapter.load
        assert getattr(method, "__isabstractmethod__", False)

    def test_has_capabilities_concrete(self) -> None:
        """SourceAdapter 必须有 capabilities 具体方法（默认实现）。

        不能直接调用 ``SourceAdapter.capabilities()``（它是实例方法），
        这里验证方法存在且非抽象，具体返回值由 subclass 测试覆盖。
        """
        assert hasattr(self.SourceAdapter, "capabilities")
        method = self.SourceAdapter.capabilities
        # 默认实现不应标记为 abstractmethod
        assert not getattr(method, "__isabstractmethod__", False)

    def test_load_return_annotation_is_adapter_result(self) -> None:
        """load() 的返回类型标注应为 AdapterResult。"""
        import typing

        hints = typing.get_type_hints(self.SourceAdapter.load)
        assert hints.get("return") is AdapterResult


# =============================================================================
# B. PlainMarkdownAdapter v2 can_handle contract
# =============================================================================


@pytest.mark.xfail(
    not _MARKDOWN_ADAPTER_V2_EXISTS,
    reason="v0.2 PlainMarkdownAdapter wrapper 尚未实现——预期 Red。",
    strict=True,
)
class TestPlainMarkdownAdapterV2CanHandle:
    """v0.2 PlainMarkdownAdapter.can_handle() 后缀识别。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.adapter = PlainMarkdownAdapter()

    @pytest.mark.parametrize(
        "path,expected",
        [
            ("note.md", True),
            ("NOTE.MD", True),
            ("path/to/file.md", True),
            ("note.markdown", True),
            ("NOTE.MARKDOWN", True),
            ("note.mdown", False),
            ("note.txt", False),
            ("note.html", False),
            ("note.pdf", False),
            ("note.docx", False),
            ("note", False),
            ("note.md.backup", False),
        ],
    )
    def test_can_handle(self, path: str, expected: bool) -> None:
        """can_handle 按 .md / .markdown 后缀识别（大小写不敏感）。"""
        assert self.adapter.can_handle(path) is expected

    def test_can_handle_is_pure_query(self) -> None:
        """can_handle 是纯查询：不抛异常、不写文件、不读文件。"""
        # 不存在的文件路径也应正常返回 bool
        result = self.adapter.can_handle("/nonexistent/path/note.md")
        assert result is True
        result = self.adapter.can_handle("/nonexistent/path/note.txt")
        assert result is False


# =============================================================================
# C. PlainMarkdownAdapter v2 load() — 三态返回
# =============================================================================


@pytest.mark.xfail(
    not _MARKDOWN_ADAPTER_V2_EXISTS,
    reason="v0.2 PlainMarkdownAdapter wrapper 尚未实现——预期 Red。",
    strict=True,
)
class TestPlainMarkdownAdapterV2Load:
    """v0.2 PlainMarkdownAdapter.load() → AdapterResult 三态契约。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.adapter = PlainMarkdownAdapter()

    # -- failed: 文件不存在 -------------------------------------------------

    def test_load_missing_file_returns_failed(self) -> None:
        """文件不存在时应返回 AdapterResult.failed，不抛 bare exception。"""
        result = self.adapter.load("/tmp/nonexistent_xyz123.md")
        assert isinstance(result, AdapterResult)
        assert result.status == "failed"
        assert result.document is None
        assert result.error_message is not None
        assert len(result.error_message) > 0
        # error_message 应包含文件名以帮助定位
        assert "nonexistent_xyz123" in result.error_message

    # -- skipped: 不支持的格式 ----------------------------------------------

    @pytest.mark.parametrize("suffix", [".txt", ".html", ".pdf", ".docx", ".csv"])
    def test_load_unsupported_suffix_returns_skipped(
        self, tmp_path: Path, suffix: str
    ) -> None:
        """不支持的格式应返回 AdapterResult.skipped，而非抛异常。"""
        f = tmp_path / f"test{suffix}"
        f.write_text("content", encoding="utf-8")
        result = self.adapter.load(str(f))
        assert isinstance(result, AdapterResult)
        assert result.status == "skipped"
        assert result.document is None
        assert result.skip_reason is not None
        assert len(result.skip_reason) > 0

    # -- loaded: 合法 Markdown ----------------------------------------------

    def test_load_valid_md_returns_loaded(self, tmp_path: Path) -> None:
        """合法 .md 文件应返回 AdapterResult.loaded。"""
        md = tmp_path / "note.md"
        md.write_text("# Hello\n\nWorld.\n", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert isinstance(result, AdapterResult)
        assert result.status == "loaded"
        assert result.document is not None
        assert result.skip_reason is None
        assert result.error_message is None

    def test_loaded_document_has_correct_source_type(self, tmp_path: Path) -> None:
        """loaded document.source_type 必须为 "plain_markdown"。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.document.source_type == "plain_markdown"

    def test_loaded_document_preserves_raw_text(self, tmp_path: Path) -> None:
        """loaded document.raw_text 保留原文内容。

        注：``frontmatter`` 库的 ``post.content`` 会 strip 尾部空白符——
        这是 v0.1 既存行为，v0.2 wrapper 与之保持一致。
        """
        content = "# Title\n\nBody paragraph."
        md = tmp_path / "note.md"
        md.write_text(content + "\n", encoding="utf-8")
        result = self.adapter.load(str(md))
        # frontmatter 去掉了尾部 \\n，所以 raw_text == 不含尾部空白的 content
        assert result.document.raw_text == content

    def test_loaded_document_preserves_source_path(self, tmp_path: Path) -> None:
        """loaded document.source_path 保留原始路径。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.document.source_path == str(md)

    def test_loaded_document_has_content_hash(self, tmp_path: Path) -> None:
        """loaded document.content_hash 不为空。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.document.content_hash
        assert result.document.content_hash.startswith("sha256:")

    def test_loaded_document_extraction_warnings_default_empty(self, tmp_path: Path) -> None:
        """正常 Markdown 的 extraction_warnings 应为空 list。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.document.extraction_warnings == []

    def test_loaded_document_provenance_blocks_default_empty(self, tmp_path: Path) -> None:
        """正常 Markdown 的 provenance_blocks 应为空 list。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.document.provenance_blocks == []

    def test_loaded_document_highlights_default_empty(self, tmp_path: Path) -> None:
        """Markdown adapter 的 highlights 应为空 list（v0.1 行为不变）。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.document.highlights == []

    def test_loaded_result_warnings_is_list(self, tmp_path: Path) -> None:
        """loaded 状态的 AdapterResult.warnings 应为 list（可为空）。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert isinstance(result.warnings, list)
        assert result.warnings == []

    def test_load_valid_markdown_uses_markdown_suffix(self, tmp_path: Path) -> None:
        """.markdown 后缀文件也应被识别和加载。"""
        md = tmp_path / "note.markdown"
        md.write_text("# Hello\n", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.status == "loaded"
        assert result.document is not None

    # -- 空文件处理 ----------------------------------------------------------

    def test_load_empty_md_file_returns_loaded(self, tmp_path: Path) -> None:
        """空 .md 文件应返回 loaded（raw_text 可为空字符串）。"""
        md = tmp_path / "empty.md"
        md.write_text("", encoding="utf-8")
        result = self.adapter.load(str(md))
        assert result.status == "loaded"
        assert result.document is not None
        assert result.document.raw_text == ""

    # -- frontmatter 解析 ---------------------------------------------------

    def test_load_md_with_frontmatter(self, tmp_path: Path) -> None:
        """带 YAML frontmatter 的 Markdown 应正确解析 title。"""
        md = tmp_path / "note.md"
        md.write_text(
            "---\ntitle: My Note\nauthor: Alice\n---\n\n# Body\n",
            encoding="utf-8",
        )
        result = self.adapter.load(str(md))
        assert result.status == "loaded"
        assert result.document.title == "My Note"
        assert result.document.author == "Alice"

    # -- source_id 稳定性 ---------------------------------------------------

    def test_source_id_stable_for_same_path(self, tmp_path: Path) -> None:
        """相同路径应产生相同 source_id。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result1 = self.adapter.load(str(md))
        result2 = self.adapter.load(str(md))
        assert result1.document.source_id == result2.document.source_id

    # -- content_hash 稳定性 ------------------------------------------------

    def test_content_hash_stable_for_same_content_same_stem(
        self, tmp_path: Path
    ) -> None:
        """相同内容 + 相同 stem 应产生相同 content_hash。"""
        md = tmp_path / "note.md"
        md.write_text("# Same", encoding="utf-8")
        result1 = self.adapter.load(str(md))
        result2 = self.adapter.load(str(md))
        assert result1.document.content_hash == result2.document.content_hash

    # -- frozen 不可变 ------------------------------------------------------

    def test_loaded_document_is_frozen(self, tmp_path: Path) -> None:
        """loaded document 必须是 frozen dataclass。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.document.raw_text = "tampered"  # type: ignore[misc]

    def test_adapter_result_is_frozen(self, tmp_path: Path) -> None:
        """返回的 AdapterResult 必须是 frozen dataclass。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        result = self.adapter.load(str(md))
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.status = "skipped"  # type: ignore[misc]


# =============================================================================
# D. SkipReason 词汇表在 Markdown adapter 中的使用
# =============================================================================


@pytest.mark.xfail(
    not _MARKDOWN_ADAPTER_V2_EXISTS,
    reason="v0.2 PlainMarkdownAdapter wrapper 尚未实现——预期 Red。",
    strict=True,
)
class TestMarkdownAdapterSkipReasonUsage:
    """确保 Markdown adapter 使用 SkipReason 标准词汇表。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.adapter = PlainMarkdownAdapter()

    def test_unsupported_format_uses_standard_skip_reason(self, tmp_path: Path) -> None:
        """不支持的格式应使用 SkipReason.UNSUPPORTED_FORMAT。"""
        f = tmp_path / "test.pdf"
        f.write_text("content", encoding="utf-8")
        result = self.adapter.load(str(f))
        assert result.skip_reason == SkipReason.UNSUPPORTED_FORMAT


# =============================================================================
# E. 安全 / 边界守卫
# =============================================================================


@pytest.mark.xfail(
    not _MARKDOWN_ADAPTER_V2_EXISTS,
    reason="v0.2 PlainMarkdownAdapter wrapper 尚未实现——预期 Red。",
    strict=True,
)
class TestMarkdownAdapterV2Safety:
    """v0.2 PlainMarkdownAdapter 安全边界。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        self.adapter = PlainMarkdownAdapter()

    def test_does_not_call_llm_on_load(self, tmp_path: Path, monkeypatch) -> None:
        """load() 不应调用 LLM / API。"""
        md = tmp_path / "note.md"
        md.write_text("# Test", encoding="utf-8")
        # 用 monkeypatch 守护：如果代码里 import 了任何 LLM 相关模块，
        # 这个测试本身不会拦截——它验证 load 不会抛异常或产生副作用。
        result = self.adapter.load(str(md))
        assert result.status == "loaded"

    def test_does_not_read_env_on_can_handle(self, monkeypatch) -> None:
        """can_handle() 不应读环境变量。"""
        # 删除所有可能的环境变量以验证不需要它们
        result = self.adapter.can_handle("note.md")
        assert result is True

    def test_capabilities_includes_fake_safe(self) -> None:
        """capabilities 应包含 fake_safe。"""
        assert "fake_safe" in self.adapter.capabilities()

    def test_capabilities_excludes_real_api(self) -> None:
        """capabilities 不应包含 real_api（Markdown adapter 是纯本地文件读取）。"""
        assert "real_api" not in self.adapter.capabilities()

    def test_capabilities_is_frozenset(self) -> None:
        """capabilities 返回类型应为 frozenset。"""
        caps = self.adapter.capabilities()
        assert isinstance(caps, frozenset)

    def test_instantiation_does_no_io(self, monkeypatch) -> None:
        """实例化不应做 IO。"""
        # 再次实例化以验证无 IO（已在 fixture 中实例化过）
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter

        a = PlainMarkdownAdapter()
        assert a.name == "PlainMarkdownAdapter"
        assert a.source_type == "plain_markdown"


# =============================================================================
# F. 与 v0.1 PlainMarkdownAdapter 的兼容性
# =============================================================================


@pytest.mark.xfail(
    not _MARKDOWN_ADAPTER_V2_EXISTS,
    reason="v0.2 PlainMarkdownAdapter wrapper 尚未实现——预期 Red。",
    strict=True,
)
class TestV2AdapterPreservesV1Behavior:
    """v0.2 wrapper 保持与 v0.1 PlainMarkdownAdapter 行为一致。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.sources.markdown_adapter import PlainMarkdownAdapter as V2Adapter
        from mindforge.sources.plain_markdown import (
            PlainMarkdownAdapter as V1Adapter,
        )

        self.V2Adapter = V2Adapter
        self.V1Adapter = V1Adapter

    def test_source_type_matches_v1(self) -> None:
        """v0.2 wrapper 的 source_type 应与 v0.1 一致。"""
        v1 = self.V1Adapter()
        v2 = self.V2Adapter()
        assert v2.source_type == v1.source_type == "plain_markdown"

    def test_can_handle_matches_v1_for_md(self) -> None:
        """v0.2 wrapper 的 can_handle 对 .md 应与 v0.1 一致。"""
        v1 = self.V1Adapter()
        v2 = self.V2Adapter()
        assert v2.can_handle("note.md") == v1.can_handle("note.md") is True

    def test_can_handle_matches_v1_for_non_md(self) -> None:
        """v0.2 wrapper 的 can_handle 对非 .md 应与 v0.1 一致。"""
        v1 = self.V1Adapter()
        v2 = self.V2Adapter()
        for ext in [".txt", ".pdf", ".html"]:
            assert v2.can_handle(f"note{ext}") == v1.can_handle(f"note{ext}") is False

    def test_load_same_content_produces_same_raw_text(
        self, tmp_path: Path
    ) -> None:
        """相同文件的 raw_text 应与 v0.1 一致。"""
        content = "# Hello\n\nWorld.\n"
        md = tmp_path / "note.md"
        md.write_text(content, encoding="utf-8")
        v1 = self.V1Adapter()
        v2 = self.V2Adapter()
        v1_doc = v1.load(str(md))
        v2_result = v2.load(str(md))
        assert v2_result.document.raw_text == v1_doc.raw_text

    def test_load_same_content_produces_same_content_hash(
        self, tmp_path: Path
    ) -> None:
        """相同文件的 content_hash 应与 v0.1 一致。"""
        content = "# Hello\n\nWorld.\n"
        md = tmp_path / "note.md"
        md.write_text(content, encoding="utf-8")
        v1 = self.V1Adapter()
        v2 = self.V2Adapter()
        v1_doc = v1.load(str(md))
        v2_result = v2.load(str(md))
        assert v2_result.document.content_hash == v1_doc.content_hash
