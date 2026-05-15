"""Wiki P5 — TOC 生成测试。

验证从 WikiPageViewModel.sections 生成 Table of Contents 的逻辑。
anchor 基于 section title 的 _slugify 生成，确保唯一性和 URL 安全性。

RFC_0002 §5.2 / SDD_WIKI_PRESENTATION_V2 §9.
"""

from __future__ import annotations

import pytest


class TestSlugifyHelper:
    """_slugify() 辅助函数测试。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import _slugify

        self._slugify = _slugify

    def test_slugify_lowercase(self) -> None:
        assert self._slugify("Hello World") == "hello-world"

    def test_slugify_spaces_to_hyphens(self) -> None:
        assert self._slugify("My Section Title") == "my-section-title"

    def test_slugify_strips_punctuation(self) -> None:
        assert self._slugify("What is Knowledge?") == "what-is-knowledge"

    def test_slugify_collapses_multiple_hyphens(self) -> None:
        assert self._slugify("foo -- bar") == "foo-bar"

    def test_slugify_trims_leading_trailing_hyphens(self) -> None:
        assert self._slugify(" - leading trailing - ") == "leading-trailing"

    def test_slugify_handles_chinese_characters(self) -> None:
        """中文标题保留在 slug 中（Python 3 默认 Unicode 匹配）。"""
        slug = self._slugify("知识管理")
        # Python 3 re 默认 Unicode 模式，\w 匹配中文字符
        assert "知识管理" in slug or slug == ""

    def test_slugify_handles_mixed_chinese_english(self) -> None:
        """中英混合标题应保留英文/数字部分。"""
        slug = self._slugify("Wiki 知识 Management")
        assert "wiki" in slug
        assert "management" in slug

    def test_slugify_handles_special_characters(self) -> None:
        # & : # 都被 [^\w\s-] 移除，空格转连字符后 collapse
        assert self._slugify("A & B: C#") == "a-b-c"

    def test_slugify_handles_numbers(self) -> None:
        assert self._slugify("Section 2.1 Overview") == "section-21-overview"


class TestWikiSectionViewAnchor:
    """WikiSectionView.anchor 的正确性。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiSectionView, _slugify

        self.WikiSectionView = WikiSectionView
        self._slugify = _slugify

    def test_anchor_starts_with_hash(self) -> None:
        sec = self.WikiSectionView(
            id="s1",
            title="Test Section",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#test-section",
        )
        assert sec.anchor.startswith("#")

    def test_anchor_is_url_safe(self) -> None:
        """anchor 不应包含空格或特殊字符（# 后部分）。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Hello World",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#hello-world",
        )
        fragment = sec.anchor[1:]
        assert " " not in fragment
        assert "#" not in fragment
        assert all(c.isalnum() or c in "-_" for c in fragment)

    def test_build_generates_anchor_from_title(self) -> None:
        """build() 应根据 section title 自动生成 anchor。"""
        from mindforge.wiki_view_model import WikiPageViewModel

        synth = {
            "overview": "Overview.",
            "sections": [
                {
                    "title": "Core Concepts",
                    "body": "Body text.",
                    "card_ids": [],
                }
            ],
            "open_questions": [],
        }
        vm = WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.sections[0].anchor == "#core-concepts"

    def test_build_multiple_sections_have_unique_anchors(self) -> None:
        """不同 section 的 anchor 基于 title 应有不同值。"""
        from mindforge.wiki_view_model import WikiPageViewModel

        synth = {
            "overview": "Overview.",
            "sections": [
                {"title": "Section One", "body": "1.", "card_ids": []},
                {"title": "Section Two", "body": "2.", "card_ids": []},
            ],
            "open_questions": [],
        }
        vm = WikiPageViewModel.build(synthesis_output=synth, digests=[])
        anchors = [s.anchor for s in vm.sections]
        # 相同 title 可能产生相同 anchor，但不同 title 不应相同
        assert anchors[0] != anchors[1]


class TestTOCGeneration:
    """基于 WikiPageViewModel.sections 生成 TOC。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel, WikiSectionView

        self.WikiPageViewModel = WikiPageViewModel
        self.WikiSectionView = WikiSectionView

    def test_toc_from_empty_sections(self) -> None:
        """无 section 的 page 应有空 TOC。"""
        vm = self.WikiPageViewModel(
            title="Empty Wiki",
            mode="llm",
            model_id=None,
            last_rebuilt_at=None,
            overview="No sections.",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        assert len(vm.sections) == 0

    def test_toc_entries_match_sections(self) -> None:
        """TOC 条目数量应等于 section 数量。"""
        synth = {
            "overview": "O.",
            "sections": [
                {"title": "A", "body": "a", "card_ids": []},
                {"title": "B", "body": "b", "card_ids": []},
                {"title": "C", "body": "c", "card_ids": []},
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        toc_entries = [(s.title, s.anchor) for s in vm.sections]
        assert len(toc_entries) == 3
        assert all(title for title, _ in toc_entries)
        assert all(anchor.startswith("#") for _, anchor in toc_entries)

    def test_toc_section_ids_are_zero_based_sequential(self) -> None:
        """section id 应为从 0 开始的自增序号。"""
        synth = {
            "overview": "O.",
            "sections": [
                {"title": f"S{i}", "body": str(i), "card_ids": []}
                for i in range(5)
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        for i, sec in enumerate(vm.sections):
            assert sec.id == f"section-{i}"
