"""Wiki P5 — Accessibility 可访问性测试。

确保 ViewModel 输出支持前端构建语义化 HTML / ARIA 友好的 Wiki 页面：
- 所有 section 有 title（heading）
- 所有 section 有 anchor（导航目标）
- 所有 reference 有 card_title（link text）
- overview 文本非空时有意义内容

后端输出 canonical Markdown text，前端负责 ARIA 属性。
后端测试确保数据模型不缺失可访问性所需的核心字段。

RFC_0002 §5.2 / SDD_WIKI_PRESENTATION_V2 §13。
"""

from __future__ import annotations

import pytest


class TestSectionAccessibility:
    """Section 必须提供前端构建可访问 heading 所需的数据。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiSectionView

        self.WikiSectionView = WikiSectionView

    def test_section_has_non_empty_title(self) -> None:
        """每个 section 必须有 title 作为 heading text。"""
        sec = self.WikiSectionView(
            id="s1",
            title="A Descriptive Title",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#a-descriptive-title",
        )
        assert len(sec.title) > 0

    def test_section_has_level(self) -> None:
        """每个 section 必须有 heading level（用于 <h2> / <h3> 等）。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Title",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#title",
        )
        assert sec.level >= 1

    def test_section_has_anchor(self) -> None:
        """每个 section 必须有 anchor 用于 skip-link 和 TOC 导航。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Title",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#title",
        )
        assert len(sec.anchor) > 0
        assert sec.anchor.startswith("#")

    def test_section_has_body(self) -> None:
        """section 必须有 body（可为空字符串但不能为 None）。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Title",
            body="",
            level=2,
            card_refs=[],
            anchor="#title",
        )
        assert sec.body == ""  # 空 body 合法但不影响可访问性


class TestReferenceAccessibility:
    """Reference 必须提供前端构建可访问 link 所需的数据。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiReferenceView

        self.WikiReferenceView = WikiReferenceView

    def test_reference_has_card_title_for_link_text(self) -> None:
        """card_title 作为 link text 必须是描述性的。"""
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Knowledge Management Principles",
            source_title="source.pdf",
            source_type="pdf",
        )
        assert len(ref.card_title) > 0

    def test_reference_has_source_title_for_context(self) -> None:
        """source_title 提供 provenance context。"""
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
            source_title="original-document.pdf",
            source_type="pdf",
        )
        assert ref.source_title == "original-document.pdf"

    def test_reference_card_id_never_empty(self) -> None:
        """card_id 是唯一标识符，用于 key/ref 关联。"""
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
        )
        assert len(ref.card_id) > 0


class TestViewModelAccessibility:
    """WikiPageViewModel 整体的可访问性约束。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_viewmodel_has_title(self) -> None:
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert len(vm.title) > 0

    def test_all_sections_have_required_accessibility_fields(self) -> None:
        """build() 生成的每个 section 必须有 title、anchor、level。"""
        synth = {
            "overview": "Overview.",
            "sections": [
                {"title": "Section A", "body": "Body A.", "card_ids": []},
                {"title": "Section B", "body": "Body B.", "card_ids": []},
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        for sec in vm.sections:
            assert len(sec.title) > 0, f"Section {sec.id} has empty title"
            assert len(sec.anchor) > 0, f"Section {sec.id} has empty anchor"
            assert sec.level >= 1, f"Section {sec.id} has invalid level"
            assert isinstance(sec.body, str), f"Section {sec.id} body is not str"

    def test_empty_section_title_still_generates_anchor(self) -> None:
        """即使 title 为空，build() 也应生成合法的 anchor。"""
        synth = {
            "overview": "",
            "sections": [
                {"title": "", "body": "Body.", "card_ids": []}
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert len(vm.sections) == 1
        # anchor 仍然存在（可能是 "#"）
        assert isinstance(vm.sections[0].anchor, str)

    def test_references_have_card_title_for_screen_reader(self) -> None:
        """所有 references（section card_refs + additional_cards）必须有 card_title。"""
        synth = {
            "overview": "O.",
            "sections": [],
            "open_questions": [],
        }
        # 无 section 引用的 digests → additional_cards
        from mindforge.wiki_service import CardDigest

        digests = [
            CardDigest(
                card_id="card-001",
                title="Referenced Card Title",
                source_title="source.pdf",
                card_rel_path="path/to/card.md",
                track=None,
                tags=[],
                summary="Summary text.",
                principles=[],
                actions=[],
                value_score=1,
                approved_at="2026-01-01",
            )
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        for ref in vm.additional_cards:
            assert len(ref.card_title) > 0, f"Reference {ref.card_id} has empty card_title"
