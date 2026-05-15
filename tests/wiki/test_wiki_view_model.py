"""Wiki P1 — WikiPageViewModel / WikiSectionView / WikiReferenceView 契约测试。

TDD RED 阶段：测试先行，所有 test 预期失败（模块尚未实现）。
实现 wiki_view_model.py 后应全部 Green。

RFC_0002 §5.1 / SDD_WIKI_PRESENTATION_V2 §4.1, §5, §13。
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError, asdict
from unittest.mock import MagicMock

import pytest


# =============================================================================
# A. ViewModel 基本 dataclass 契约
# =============================================================================


class TestWikiPageViewModelContract:
    """WikiPageViewModel frozen dataclass 结构契约（RFC_0002 §5.1）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_is_frozen_dataclass(self) -> None:
        """WikiPageViewModel 必须是 frozen=True dataclass。"""
        from dataclasses import is_dataclass

        assert is_dataclass(self.WikiPageViewModel)
        assert self.WikiPageViewModel.__dataclass_params__.frozen

    def test_has_required_fields(self) -> None:
        """必须包含 RFC 定义的字段。"""
        vm = self.WikiPageViewModel(
            title="Test Wiki",
            mode="llm",
            model_id="test-model",
            last_rebuilt_at="2026-05-15T10:00:00",
            overview="## Overview\n\nTest overview.",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        assert vm.title == "Test Wiki"
        assert vm.mode == "llm"
        assert vm.model_id == "test-model"
        assert vm.overview == "## Overview\n\nTest overview."
        assert vm.sections == []
        assert vm.additional_cards == []
        assert vm.open_questions == []
        assert vm.included_card_count == 0
        assert vm.additional_card_count == 0
        assert vm.warnings == []

    def test_cannot_mutate_after_construction(self) -> None:
        """Frozen dataclass 拒绝 mutation（RFC_0002: Wiki 只读不写）。"""
        vm = self.WikiPageViewModel(
            title="Immutable Wiki",
            mode="llm",
            model_id=None,
            last_rebuilt_at=None,
            overview="",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        with pytest.raises(FrozenInstanceError):
            vm.title = "Changed Title"  # type: ignore[misc]

    def test_overview_body_is_markdown_not_html(self) -> None:
        """overview 字段必须是 canonical Markdown text，非 HTML。"""
        vm = self.WikiPageViewModel(
            title="Markdown Wiki",
            mode="llm",
            model_id=None,
            last_rebuilt_at=None,
            overview="## Overview\n\nThis is **Markdown**.",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        assert "#" in vm.overview or "**" in vm.overview
        assert "<div" not in vm.overview
        assert "<p>" not in vm.overview

    def test_serializable_to_json_dict(self) -> None:
        """asdict() 应返回 JSON-friendly dict（无不可序列化对象）。"""
        vm = self.WikiPageViewModel(
            title="Serializable Wiki",
            mode="llm",
            model_id=None,
            last_rebuilt_at=None,
            overview="Overview.",
            sections=[],
            additional_cards=[],
            open_questions=[],
            included_card_count=0,
            additional_card_count=0,
            warnings=[],
        )
        d = asdict(vm)
        assert isinstance(d, dict)
        assert d["title"] == "Serializable Wiki"
        assert d["mode"] == "llm"
        assert isinstance(d["sections"], list)


class TestWikiSectionViewContract:
    """WikiSectionView frozen dataclass 结构契约（RFC_0002 §5.1）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiSectionView

        self.WikiSectionView = WikiSectionView

    def test_is_frozen(self) -> None:
        from dataclasses import is_dataclass

        assert is_dataclass(self.WikiSectionView)
        assert self.WikiSectionView.__dataclass_params__.frozen

    def test_has_required_fields(self) -> None:
        sec = self.WikiSectionView(
            id="section-1",
            title="Section Title",
            body="## Section\n\nBody in **Markdown**.",
            level=2,
            card_refs=[],
            anchor="#section-title",
        )
        assert sec.id == "section-1"
        assert sec.title == "Section Title"
        assert sec.body == "## Section\n\nBody in **Markdown**."
        assert sec.level == 2
        assert sec.card_refs == []
        assert sec.anchor == "#section-title"

    def test_cannot_mutate(self) -> None:
        sec = self.WikiSectionView(
            id="section-1",
            title="Immutable Section",
            body="Body.",
            level=2,
            card_refs=[],
            anchor="#immutable-section",
        )
        with pytest.raises(FrozenInstanceError):
            sec.title = "Changed"  # type: ignore[misc]

    def test_body_is_markdown_not_html(self) -> None:
        """section body 必须是 canonical Markdown text，非 HTML（RFC_0002 §5.2）。"""
        sec = self.WikiSectionView(
            id="s1",
            title="Markdown Section",
            body="### Subheading\n\nContent with **bold** and `code`.",
            level=2,
            card_refs=[],
            anchor="#markdown-section",
        )
        assert "###" in sec.body
        assert "**" in sec.body
        assert "<div" not in sec.body

    def test_anchor_is_url_safe(self) -> None:
        """anchor 必须是 URL-safe slug（RFC_0002 §5.1）。"""
        sec = self.WikiSectionView(
            id="section-1",
            title="My Section Title",
            body="Content.",
            level=2,
            card_refs=[],
            anchor="#my-section-title",
        )
        assert sec.anchor.startswith("#")
        assert " " not in sec.anchor
        assert sec.anchor.isascii() or "-" in sec.anchor


class TestWikiReferenceViewContract:
    """WikiReferenceView frozen dataclass 结构契约（RFC_0002 §5.1）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiReferenceView

        self.WikiReferenceView = WikiReferenceView

    def test_is_frozen(self) -> None:
        from dataclasses import is_dataclass

        assert is_dataclass(self.WikiReferenceView)
        assert self.WikiReferenceView.__dataclass_params__.frozen

    def test_has_required_fields(self) -> None:
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="My Knowledge Card",
            source_title="source-doc.pdf",
            source_type="pdf",
            source_path="/data/source-doc.pdf",
            track="work",
            tags=["python", "testing"],
            value_score=7,
            approved_at="2026-05-10T09:00:00",
            card_rel_path="20-Knowledge-Cards/card-001.md",
        )
        assert ref.card_id == "card-001"
        assert ref.card_title == "My Knowledge Card"
        assert ref.source_title == "source-doc.pdf"
        assert ref.source_type == "pdf"
        assert ref.source_path == "/data/source-doc.pdf"
        assert ref.track == "work"
        assert ref.tags == ["python", "testing"]
        assert ref.value_score == 7
        assert ref.approved_at == "2026-05-10T09:00:00"
        assert ref.card_rel_path == "20-Knowledge-Cards/card-001.md"

    def test_optional_provenance_fields_can_be_none(self) -> None:
        """source_type / source_path / source_title 可为 None（provenance 不可用时）。"""
        ref = self.WikiReferenceView(
            card_id="card-002",
            card_title="Minimal Card",
            source_title=None,
            source_type=None,
            source_path=None,
            track=None,
            tags=[],
            value_score=None,
            approved_at=None,
            card_rel_path="20-Knowledge-Cards/card-002.md",
        )
        assert ref.source_type is None
        assert ref.source_path is None
        assert ref.source_title is None

    def test_cannot_mutate(self) -> None:
        ref = self.WikiReferenceView(
            card_id="card-001",
            card_title="Immutable",
            source_title=None,
            source_type=None,
            source_path=None,
            track=None,
            tags=[],
            value_score=None,
            approved_at=None,
            card_rel_path="path",
        )
        with pytest.raises(FrozenInstanceError):
            ref.card_title = "Changed"  # type: ignore[misc]

    def test_tags_is_default_factory_list(self) -> None:
        """tags 默认应为空 list（SDD §4.1 field(default_factory=list)）。"""
        ref = self.WikiReferenceView(
            card_id="card-003",
            card_title="Tagless Card",
            source_title=None,
            source_type=None,
            source_path=None,
            track=None,
            value_score=None,
            approved_at=None,
            card_rel_path="path",
        )
        assert ref.tags == []


class TestWikiQuestionViewContract:
    """WikiQuestionView frozen dataclass 结构契约（RFC_0002 §5.1）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiQuestionView

        self.WikiQuestionView = WikiQuestionView

    def test_is_frozen(self) -> None:
        from dataclasses import is_dataclass

        assert is_dataclass(self.WikiQuestionView)
        assert self.WikiQuestionView.__dataclass_params__.frozen

    def test_has_question_field(self) -> None:
        q = self.WikiQuestionView(question="What is the meaning of life?")
        assert q.question == "What is the meaning of life?"


class TestWikiRenderOptionsContract:
    """WikiRenderOptions 配置 dataclass（RFC_0002 §5.1）。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiRenderOptions

        self.WikiRenderOptions = WikiRenderOptions

    def test_default_values(self) -> None:
        opts = self.WikiRenderOptions()
        assert opts.show_provenance_panel is True
        assert opts.show_toc is True
        assert opts.toc_position == "sidebar"
        assert opts.sanitize_html is True
        assert opts.enable_mermaid is False
        assert opts.enable_code_highlight is True

    def test_custom_values(self) -> None:
        opts = self.WikiRenderOptions(
            show_provenance_panel=False,
            toc_position="top",
            enable_mermaid=True,
        )
        assert opts.show_provenance_panel is False
        assert opts.toc_position == "top"
        assert opts.enable_mermaid is True

    def test_mutable_by_design(self) -> None:
        """WikiRenderOptions 是 mutable dataclass（用户可配置）。"""
        opts = self.WikiRenderOptions()
        opts.toc_position = "top"
        assert opts.toc_position == "top"


# =============================================================================
# B. WikiPageViewModel.build() 构建逻辑
# =============================================================================


class TestWikiPageViewModelBuild:
    """WikiPageViewModel.build() 从 synthesis JSON + CardDigest 构建。

    SDD_WIKI_PRESENTATION_V2 §4.1 构建逻辑:
    1. 从 synthesis JSON 解析 overview, sections[], open_questions[]
    2. 每个 section 的 card_ids[] 在 CardDigest index 中查找
    3. 构建 WikiReferenceView 包含 provenance
    4. 未被任何 section 引用的 card → additional_cards
    5. 记录 synthesis warnings
    """

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel
        from mindforge.wiki_service import CardDigest

        self.CardDigest = CardDigest

    def _make_digest(self, card_id: str, title: str = "Card Title", **kw) -> "CardDigest":
        """构造最小 CardDigest 用于测试。"""
        from mindforge.wiki_service import CardDigest

        defaults = {
            "card_id": card_id,
            "title": title,
            "track": None,
            "tags": [],
            "summary": f"Summary for {title}",
            "principles": "",
            "actions": "",
            "value_score": 5,
            "approved_at": "2026-05-10T09:00:00",
            "card_rel_path": f"20-Knowledge-Cards/{card_id}.md",
            "source_title": "source-doc.pdf",
        }
        defaults.update(kw)
        return CardDigest(**defaults)

    def _synth_json(self, **overrides) -> dict:
        """构造标准 synthesis JSON 输出。"""
        base = {
            "overview": "## Overview\n\nThis is an overview.",
            "sections": [
                {
                    "title": "Section One",
                    "body": "Content for section one.",
                    "card_ids": ["card-1"],
                },
                {
                    "title": "Section Two",
                    "body": "Content for section two with **markdown**.",
                    "card_ids": ["card-2", "card-3"],
                },
            ],
            "open_questions": ["How do we scale?", "What about testing?"],
        }
        base.update(overrides)
        return base

    # -- 正常构建 ---------------------------------------------------------

    def test_build_from_valid_synthesis_json(self) -> None:
        """正常 synthesis JSON → 完整 WikiPageViewModel。"""
        synth = self._synth_json()
        digests = [
            self._make_digest("card-1", "Card One"),
            self._make_digest("card-2", "Card Two"),
            self._make_digest("card-3", "Card Three"),
        ]
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=digests,
            mode="llm",
            model_id="test-model",
            last_rebuilt_at="2026-05-15T10:00:00",
        )
        assert vm.title == "MindForge Main Wiki"
        assert vm.mode == "llm"
        assert vm.model_id == "test-model"
        assert vm.last_rebuilt_at == "2026-05-15T10:00:00"
        assert vm.overview == "## Overview\n\nThis is an overview."
        assert len(vm.sections) == 2
        assert len(vm.open_questions) == 2
        assert vm.included_card_count == 3
        assert vm.additional_card_count == 0

    def test_build_section_card_refs_populated(self) -> None:
        """section 的 card_refs 从 CardDigest 正确构建。"""
        synth = self._synth_json()
        digests = [
            self._make_digest("card-1", "Card One", track="work", tags=["python"], value_score=7),
            self._make_digest("card-2", "Card Two"),
            self._make_digest("card-3", "Card Three", track="personal"),
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        sec1 = vm.sections[0]
        assert len(sec1.card_refs) == 1
        ref = sec1.card_refs[0]
        assert ref.card_id == "card-1"
        assert ref.card_title == "Card One"
        assert ref.track == "work"
        assert ref.tags == ["python"]
        assert ref.value_score == 7
        assert ref.source_title == "source-doc.pdf"

        sec2 = vm.sections[1]
        assert len(sec2.card_refs) == 2
        assert {r.card_id for r in sec2.card_refs} == {"card-2", "card-3"}

    def test_build_sections_have_anchors(self) -> None:
        """每个 section 自动生成 anchor slug。"""
        synth = self._synth_json()
        digests = [
            self._make_digest("card-1", "Card One"),
            self._make_digest("card-2", "Card Two"),
            self._make_digest("card-3", "Card Three"),
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        assert vm.sections[0].anchor.startswith("#")
        assert " " not in vm.sections[0].anchor
        assert vm.sections[1].anchor.startswith("#")

    def test_build_section_has_generated_id(self) -> None:
        """section id 自动生成（如 section-0, section-1...）。"""
        synth = self._synth_json()
        digests = [
            self._make_digest("card-1", "Card One"),
            self._make_digest("card-2", "Card Two"),
            self._make_digest("card-3", "Card Three"),
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        assert vm.sections[0].id == "section-0"
        assert vm.sections[1].id == "section-1"

    def test_build_section_body_is_markdown(self) -> None:
        """section.body 必须是 canonical Markdown text，不是 HTML。"""
        synth = self._synth_json()
        digests = [
            self._make_digest("card-1", "Card One"),
            self._make_digest("card-2", "Card Two"),
            self._make_digest("card-3", "Card Three"),
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        # body 内容来自 synthesis JSON 的原始 Markdown
        assert "**" in vm.sections[1].body
        assert "<p>" not in vm.sections[0].body

    # -- 未引用 card → additional_cards -----------------------------------

    def test_uncited_cards_become_additional(self) -> None:
        """未被任何 section 引用的 card → additional_cards。"""
        synth = self._synth_json()  # only references card-1, card-2, card-3
        digests = [
            self._make_digest("card-1", "Card One"),
            self._make_digest("card-2", "Card Two"),
            self._make_digest("card-3", "Card Three"),
            self._make_digest("card-4", "Uncited Card"),
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        assert vm.additional_card_count == 1
        assert len(vm.additional_cards) == 1
        assert vm.additional_cards[0].card_id == "card-4"

    # -- 缺失字段 → 安全 fallback ----------------------------------------

    def test_missing_overview_empty_string(self) -> None:
        synth = {"sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.overview == ""

    def test_missing_sections_empty_list(self) -> None:
        synth = {"overview": "Overview", "open_questions": []}
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.sections == []

    def test_missing_open_questions_empty_list(self) -> None:
        synth = {"overview": "Overview", "sections": []}
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.open_questions == []

    def test_unknown_card_ids_produce_warnings(self) -> None:
        """section 引用不存在的 card_id → warnings。"""
        synth = self._synth_json()
        digests = [self._make_digest("card-1", "Card One")]
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=digests,
            warnings=["unknown card_id: card-2", "unknown card_id: card-3"],
        )
        assert len(vm.warnings) >= 2
        assert any("card-2" in w or "card-3" in w for w in vm.warnings)

    def test_empty_section_body_not_excluded(self) -> None:
        """body 为空的 section 仍保留（不丢弃）。"""
        synth = {
            "overview": "Overview",
            "sections": [
                {"title": "Empty Section", "body": "", "card_ids": []},
                {"title": "Non-empty Section", "body": "Has content.", "card_ids": []},
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert len(vm.sections) == 2

    # -- 外部 warnings 合并 -----------------------------------------------

    def test_external_warnings_merged(self) -> None:
        synth = self._synth_json()
        digests = [self._make_digest("card-1"), self._make_digest("card-2"), self._make_digest("card-3")]
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=digests,
            warnings=["LLM timeout warning", "Rate limit hit"],
        )
        assert "LLM timeout warning" in vm.warnings
        assert "Rate limit hit" in vm.warnings

    # -- mode 默认值 ------------------------------------------------------

    def test_default_mode_is_llm(self) -> None:
        synth = self._synth_json()
        digests = [
            self._make_digest("card-1"), self._make_digest("card-2"), self._make_digest("card-3")
        ]
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=digests)
        assert vm.mode == "llm"

    # -- deterministic mode ------------------------------------------------

    def test_deterministic_mode(self) -> None:
        synth = {"overview": "Deterministic overview.", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth, digests=[], mode="deterministic"
        )
        assert vm.mode == "deterministic"
        assert vm.model_id is None
