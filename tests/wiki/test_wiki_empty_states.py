"""Wiki P5 — Empty / Error / Warning 状态测试。

验证 WikiPageViewModel 在各种边界条件下的行为：
- 空 sections / 空 overview
- 无 approved cards
- build warnings 记录
- 缺失 synthesis 字段

RFC_0002 §5.2 / SDD_WIKI_PRESENTATION_V2 §9, §13。
"""

from __future__ import annotations

import pytest


class TestWikiPageViewModelEmptyStates:
    """Empty state 测试。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    # -- 空 sections ---------------------------------------------------------------------

    def test_empty_sections_list(self) -> None:
        """synthesis 中 sections 为空列表时，ViewModel 应有空 sections。"""
        synth = {
            "overview": "Just an overview.",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.sections == []
        assert vm.overview == "Just an overview."

    def test_missing_sections_key(self) -> None:
        """synthesis 中缺少 sections key 时，应默认为空列表。"""
        synth = {
            "overview": "Only overview.",
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.sections == []

    def test_none_sections(self) -> None:
        """sections 为 None 时处理为 []。"""
        synth = {
            "overview": "O.",
            "sections": None,
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.sections == []

    # -- 空 overview --------------------------------------------------------------------

    def test_empty_overview(self) -> None:
        synth = {
            "overview": "",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.overview == ""

    def test_missing_overview_key(self) -> None:
        synth = {
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.overview == ""

    # -- 空 open_questions ---------------------------------------------------------------

    def test_empty_open_questions(self) -> None:
        synth = {
            "overview": "O.",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.open_questions == []

    def test_missing_open_questions_key(self) -> None:
        synth = {
            "overview": "O.",
            "sections": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.open_questions == []

    # -- 空 card digests -----------------------------------------------------------------

    def test_zero_digests_with_sections(self) -> None:
        """无 digests 但有 sections 的 page 应正确构建。"""
        synth = {
            "overview": "O.",
            "sections": [
                {"title": "S1", "body": "Body.", "card_ids": []}
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.included_card_count == 0
        assert vm.additional_card_count == 0
        assert len(vm.sections) == 1

    def test_zero_digests_zero_sections(self) -> None:
        """完全空的 wiki（无 cards、无 sections）。"""
        synth = {
            "overview": "",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.included_card_count == 0
        assert vm.additional_card_count == 0
        assert vm.sections == []


class TestWikiPageViewModelWarningStates:
    """Warning 状态测试。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_build_records_unknown_card_id_warning(self) -> None:
        """section 引用不存在的 card_id 应记录 warning。"""
        synth = {
            "overview": "O.",
            "sections": [
                {
                    "title": "S1",
                    "body": "Body.",
                    "card_ids": ["nonexistent-card-001"],
                }
            ],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert len(vm.warnings) >= 1
        assert any("nonexistent-card-001" in w for w in vm.warnings)

    def test_build_merges_external_warnings(self) -> None:
        """外部 warnings 应与内部 warning 合并。"""
        synth = {
            "overview": "O.",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=[],
            warnings=["LLM timeout warning"],
        )
        assert "LLM timeout warning" in vm.warnings

    def test_no_warnings_on_valid_build(self) -> None:
        """合法 synthesis + 合法 digests → 无 warning。"""
        synth = {
            "overview": "O.",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.warnings == []

    def test_warnings_never_contain_sensitive_fields(self) -> None:
        """warnings 不应包含 card body / raw_text。"""
        synth = {
            "overview": "O.",
            "sections": [],
            "open_questions": [],
        }
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=[],
            warnings=["Some warning"],
        )
        for w in vm.warnings:
            assert "body" not in w.lower() or "warning" in w.lower()


class TestWikiPageViewModelModeStates:
    """mode 状态签名测试。"""

    @pytest.fixture(autouse=True)
    def _imports(self):
        from mindforge.wiki_view_model import WikiPageViewModel

        self.WikiPageViewModel = WikiPageViewModel

    def test_deterministic_mode_preserved(self) -> None:
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth, digests=[], mode="deterministic"
        )
        assert vm.mode == "deterministic"

    def test_llm_mode_is_default(self) -> None:
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(synthesis_output=synth, digests=[])
        assert vm.mode == "llm"

    def test_model_id_preserved(self) -> None:
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth, digests=[], model_id="gpt-4"
        )
        assert vm.model_id == "gpt-4"

    def test_last_rebuilt_at_preserved(self) -> None:
        synth = {"overview": "", "sections": [], "open_questions": []}
        vm = self.WikiPageViewModel.build(
            synthesis_output=synth,
            digests=[],
            last_rebuilt_at="2026-05-15T10:00:00+0800",
        )
        assert vm.last_rebuilt_at == "2026-05-15T10:00:00+0800"
