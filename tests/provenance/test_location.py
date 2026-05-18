"""M4 Source Location unit tests — SDD §8.1, TDD §3。"""

import pytest

from mindforge.provenance.location import SourceLocation

from tests.fixtures.location_golden import LOCATION_FIXTURES


class TestSourceLocationDisplay:
    """各 source_type 的 location display 格式测试"""

    def test_markdown_location_display(self):
        fixture = LOCATION_FIXTURES["markdown"]
        loc = SourceLocation(**fixture[0])  # type: ignore[arg-type]
        assert fixture[1] in loc.to_display()

    def test_txt_location_display(self):
        fixture = LOCATION_FIXTURES["txt"]
        loc = SourceLocation(**fixture[0])  # type: ignore[arg-type]
        assert fixture[1] in loc.to_display()

    def test_pdf_location_display(self):
        fixture = LOCATION_FIXTURES["pdf"]
        loc = SourceLocation(**fixture[0])  # type: ignore[arg-type]
        assert fixture[1] in loc.to_display()

    def test_docx_location_display(self):
        fixture = LOCATION_FIXTURES["docx"]
        loc = SourceLocation(**fixture[0])  # type: ignore[arg-type]
        assert fixture[1] in loc.to_display()

    def test_html_location_display(self):
        fixture = LOCATION_FIXTURES["html"]
        loc = SourceLocation(**fixture[0])  # type: ignore[arg-type]
        display = loc.to_display()
        assert "Overview" in display


class TestSourceLocationDefaults:
    """未设置字段的降级行为"""

    def test_location_none_fields_safe_display(self):
        loc = SourceLocation(source_type="pdf")
        result = loc.to_display()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_location_with_only_source_type(self):
        loc = SourceLocation(source_type="plain_markdown")
        display = loc.to_display()
        assert isinstance(display, str)

    def test_location_all_none_fields(self):
        loc = SourceLocation(source_type="txt", line_start=None, line_end=None)
        display = loc.to_display()
        assert isinstance(display, str)


class TestSourceLocationImmutability:
    """frozen dataclass 不可变性"""

    def test_source_location_is_frozen(self):
        loc = SourceLocation(source_type="pdf", page_number=1)
        with pytest.raises(Exception):
            loc.page_number = 5  # type: ignore[misc]


class TestSourceLocationEquality:
    """确定性相等性"""

    def test_same_fields_equal(self):
        a = SourceLocation(source_type="txt", line_start=1, line_end=10)
        b = SourceLocation(source_type="txt", line_start=1, line_end=10)
        assert a == b

    def test_different_fields_not_equal(self):
        a = SourceLocation(source_type="txt", line_start=1, line_end=10)
        b = SourceLocation(source_type="txt", line_start=5, line_end=10)
        assert a != b
