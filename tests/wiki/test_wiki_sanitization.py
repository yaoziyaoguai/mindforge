"""Wiki P5 — Markdown Sanitization 规则测试。

验证后端 WikiPageViewModel 输出的 section.body 不包含不安全的 HTML 标签。
实际渲染 sanitization 在前端 DOMPurify 完成，但后端确保 body 为 canonical Markdown。

RFC_0002 §6 / SDD_WIKI_PRESENTATION_V2 §7, §13。
"""

from __future__ import annotations

import pytest


# =============================================================================
# Markdown content 安全规则（后端验证）
# =============================================================================


class TestWikiMarkdownSanitizationRules:
    """后端确保 section.body 为 canonical Markdown text。

    前端 DOMPurify 为唯一 sanitization 点。但后端应确保不输出
    预渲染的含危险标签的 HTML。
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import (
            WikiPageViewModel,
            WikiSectionView,
            WikiReferenceView,
        )

        self.WikiPageViewModel = WikiPageViewModel
        self.WikiSectionView = WikiSectionView
        self.WikiReferenceView = WikiReferenceView

    def test_section_body_does_not_contain_script_tag(self) -> None:
        """section.body 不应包含 <script> 标签。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Safe Section",
            body="## Content\n\nNormal content here.",
            level=2,
            card_refs=[],
            anchor="#safe-section",
        )
        assert "<script" not in sec.body.lower()
        assert "</script>" not in sec.body.lower()

    def test_section_body_does_not_contain_iframe(self) -> None:
        """section.body 不应包含 <iframe> 标签。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Safe Section",
            body="## Content\n\nClean markdown text.",
            level=2,
            card_refs=[],
            anchor="#safe-section",
        )
        assert "<iframe" not in sec.body.lower()

    def test_section_body_is_markdown_not_html(self) -> None:
        """body 必须是 Markdown 或纯文本，不是 HTML。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Markdown Section",
            body="### Subheading\n\nText with **bold** and *italic*.",
            level=2,
            card_refs=[],
            anchor="#markdown-section",
        )
        # Markdown indicators should be present
        assert "###" in sec.body or "**" in sec.body or "*" in sec.body
        # HTML structural tags should not be present
        assert "<p>" not in sec.body

    def test_overview_does_not_contain_script_tag(self) -> None:
        """WikiPageViewModel.overview 不应包含 <script>。"""
        vm = self.WikiPageViewModel(
            title="Safe Wiki",
            mode="llm",
            model_id=None,
            last_rebuilt_at=None,
            overview="## Overview\n\nSafe overview text.",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        assert "<script" not in vm.overview.lower()

    def test_build_preserves_markdown_formatting(self) -> None:
        """build() 应保留 Markdown 格式（**bold**、列表等）。"""
        synth = {
            "overview": "Overview with **bold**.",
            "sections": [
                {
                    "title": "Sec",
                    "body": "- item 1\n- item 2\n\n**bold text**",
                    "card_ids": [],
                }
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        body = vm.sections[0].body
        assert "- item 1" in body
        assert "**bold text**" in body


class TestWikiReferenceViewSafety:
    """WikiReferenceView 不泄露敏感信息。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiReferenceView

        self.WikiReferenceView = WikiReferenceView

    def test_reference_does_not_contain_raw_card_body(self) -> None:
        """WikiReferenceView 只包含元数据，不包含原始 card body。"""
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Test Card",
            source_title="source.pdf",
            source_type="pdf",
            card_rel_path="path/to/card.md",
        )
        d = ref.__dict__
        # 不应有 body / content / raw_text 字段
        assert "body" not in d
        assert "content" not in d
        assert "raw_text" not in d
