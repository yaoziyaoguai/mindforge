"""M1 quality warnings tests — SDD §5.3, RFC §7 FR1.3。

验证质量警告检测的确定性规则。
"""
from tests.fixtures.quality_golden import WARNING_FIXTURES, SyntheticCard


def _detect_warnings(card: SyntheticCard, all_titles: list[str] | None = None):
    """调用 warning 检测。"""
    from mindforge.quality.warnings import detect_warnings
    return detect_warnings(
        title=card.title,
        body=card.body,
        source_id=card.source_id,
        source_path=card.source_path,
        all_titles=all_titles or [],
    )


def _codes(warnings) -> set[str]:
    """提取 warning code 集合。"""
    return {w.code for w in warnings}


class TestQualityWarnings:
    """质量警告检测测试（SDD §5.3）。"""

    def test_too_short_warning_on_body_under_100_chars(self):
        """body < 100 chars → too_short warning。"""
        card = WARNING_FIXTURES["too_short"]
        result = _detect_warnings(card)
        assert "too_short" in _codes(result)

    def test_no_too_short_warning_on_sufficient_body(self):
        """body ≥ 100 chars → 无 too_short warning。"""
        card = WARNING_FIXTURES["missing_sections"]
        assert len(card.body) >= 100
        result = _detect_warnings(card)
        assert "too_short" not in _codes(result)

    def test_missing_sections_warning_on_no_h2_markers(self):
        """body 中无 '## ' 标记 → missing_sections warning。"""
        card = WARNING_FIXTURES["missing_sections"]
        assert "## " not in card.body
        result = _detect_warnings(card)
        assert "missing_sections" in _codes(result)

    def test_no_missing_sections_warning_with_h2_markers(self):
        """body 中有 '## ' 标记 → 无 missing_sections warning。"""
        card = WARNING_FIXTURES["no_source"]
        assert "## " in card.body
        result = _detect_warnings(card)
        assert "missing_sections" not in _codes(result)

    def test_no_source_citation_warning(self):
        """card 无 source_id 且无 source_path → no_source_citation warning。"""
        card = WARNING_FIXTURES["no_source"]
        result = _detect_warnings(card)
        assert "no_source_citation" in _codes(result)

    def test_vague_language_warning(self):
        """高 vague term 比例 → vague_language warning。"""
        card = WARNING_FIXTURES["vague_language"]
        result = _detect_warnings(card)
        assert "vague_language" in _codes(result)

    def test_possible_duplicate_warning(self):
        """title 相似度 > 80% → possible_duplicate warning。"""
        card = WARNING_FIXTURES["no_source"]
        similar_titles = [
            "Good Content Without Source Citation",  # 高重叠
            "Something Completely Different About Databases",
        ]
        result = _detect_warnings(card, all_titles=similar_titles)
        assert "possible_duplicate" in _codes(result)

    def test_no_possible_duplicate_warning_when_unique(self):
        """title 相似度均 ≤ 80% → 无 possible_duplicate warning。"""
        card = WARNING_FIXTURES["no_source"]
        unique_titles = [
            "Database Migration Strategy",
            "Frontend Architecture Patterns",
            "Python Type Hints Best Practices",
        ]
        result = _detect_warnings(card, all_titles=unique_titles)
        assert "possible_duplicate" not in _codes(result)

    def test_each_warning_has_required_fields(self):
        """每个 warning 有 code, severity, message。"""
        card = WARNING_FIXTURES["vague_language"]
        result = _detect_warnings(card)
        for w in result:
            assert w.code
            assert w.severity in ("info", "warn", "critical")
            assert w.message
