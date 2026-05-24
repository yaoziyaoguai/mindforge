"""v1.2 U5 Provenance Trail Related Sources — unit tests。

中文学习型说明：测试 _compute_related_sources 的确定性行为，
包括共享 tags/sections 的正确识别和排序。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _FakeCard:
    """模拟 CardSummary 的相关字段。"""
    id: str
    rel_path: str = ""
    source_id: str | None = None
    source_title: str | None = None
    tags: list[str] | None = None
    wiki_sections: list[str] | None = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.wiki_sections is None:
            self.wiki_sections = []
        if not self.rel_path:
            self.rel_path = f"{self.id}.md"


def _compute_related_sources(source_id, approved):
    """从 web_facade 导入或就地定义（避免循环导入）。"""
    from mindforge_web.services.web_facade import _compute_related_sources as fn
    return fn(source_id, approved)


class TestComputeRelatedSources:
    """测试 _compute_related_sources 的确定性分组逻辑。"""

    def test_no_related_sources_for_isolated_source(self):
        """孤立的 source（如只有自己的卡片，无其他 source 共享）返回空。"""
        cards = [
            _FakeCard("c1", source_id="src_a", tags=["ai"], wiki_sections=["Intro"]),
            _FakeCard("c2", source_id="src_a", tags=["ai"]),
        ]
        result = _compute_related_sources("src_a", cards)
        assert len(result) == 0

    def test_related_source_via_shared_tag(self):
        """两个 source 共享 tag 时，related source 应被检出。"""
        cards = [
            _FakeCard("c1", source_id="src_a", tags=["ai", "ml"]),
            _FakeCard("c2", source_id="src_b", tags=["ai"], source_title="Source B"),
        ]
        result = _compute_related_sources("src_a", cards)
        assert len(result) == 1
        assert result[0].source_id == "src_b"
        assert "ai" in result[0].shared_tags

    def test_related_source_via_shared_wiki_section(self):
        """两个 source 共享 wiki_section 时，related source 应被检出。"""
        cards = [
            _FakeCard("c1", source_id="src_a", wiki_sections=["Intro"]),
            _FakeCard("c2", source_id="src_b", wiki_sections=["Intro"], source_title="Source B"),
        ]
        result = _compute_related_sources("src_a", cards)
        assert len(result) == 1
        assert result[0].source_id == "src_b"
        assert "Intro" in result[0].shared_wiki_sections

    def test_related_source_via_both_tag_and_section(self):
        """同时共享 tag 和 section 的 source 排在前面（共享更多）。"""
        cards = [
            _FakeCard("c1", source_id="src_a", tags=["ai"], wiki_sections=["Intro"]),
            _FakeCard("c2", source_id="src_b", tags=["ai"], source_title="B"),
            _FakeCard("c3", source_id="src_c", tags=["ai"], wiki_sections=["Intro"], source_title="C"),
        ]
        result = _compute_related_sources("src_a", cards)
        # src_c 共享了 tag + section，应排在 src_b 前面
        assert result[0].source_id == "src_c"

    def test_related_sources_sorted_by_shared_count_desc(self):
        """验证 related sources 按共享实体数降序排列。"""
        cards = [
            _FakeCard("c1", source_id="src_a", tags=["ai", "ml", "db"], wiki_sections=["A", "B"]),
            _FakeCard("c2", source_id="src_b", tags=["ai"], source_title="B"),
            _FakeCard("c3", source_id="src_c", tags=["ai", "ml"], source_title="C"),
            _FakeCard("c4", source_id="src_d", tags=["ai", "ml", "db"], wiki_sections=["A"], source_title="D"),
        ]
        result = _compute_related_sources("src_a", cards)
        # src_d: 3 tags + 1 section = 4 shared
        # src_c: 2 tags = 2 shared
        # src_b: 1 tag = 1 shared
        assert result[0].source_id == "src_d"
        assert result[1].source_id == "src_c"
        assert result[2].source_id == "src_b"

    def test_related_sources_limited_to_five(self):
        """最多返回 5 个 related sources。"""
        cards = [_FakeCard("c0", source_id="src_a", tags=["ai"])]
        for i in range(1, 8):
            cards.append(_FakeCard(f"c{i}", source_id=f"src_{i}", tags=["ai"], source_title=f"S{i}"))
        result = _compute_related_sources("src_a", cards)
        assert len(result) <= 5

    def test_none_source_id_returns_empty(self):
        """source_id 为 None 时返回空列表。"""
        result = _compute_related_sources(None, [])
        assert result == []

    def test_card_count_reflects_total_cards_in_related_source(self):
        """验证 card_count 是 related source 中的总卡片数。"""
        cards = [
            _FakeCard("c1", source_id="src_a", tags=["ai"]),
            _FakeCard("c2", source_id="src_b", tags=["ai"], source_title="B"),
            _FakeCard("c3", source_id="src_b", tags=["something_else"], source_title="B"),
        ]
        result = _compute_related_sources("src_a", cards)
        assert len(result) == 1
        assert result[0].card_count == 2  # both c2 and c3 are from src_b

    def test_deterministic_same_input_same_output(self):
        """验证确定性：相同输入 → 相同输出。"""
        cards = [
            _FakeCard("c1", source_id="src_a", tags=["ai", "ml"], wiki_sections=["Intro"]),
            _FakeCard("c2", source_id="src_b", tags=["ai"], source_title="B"),
        ]
        r1 = _compute_related_sources("src_a", cards)
        r2 = _compute_related_sources("src_a", cards)
        assert len(r1) == len(r2)
        for a, b in zip(r1, r2):
            assert a.source_id == b.source_id
            assert a.shared_tags == b.shared_tags
            assert a.shared_wiki_sections == b.shared_wiki_sections
