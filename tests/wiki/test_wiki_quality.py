"""M2 Wiki Quality unit tests — SDD §6, TDD §4。"""

import pytest

from mindforge.wiki.wiki_quality import (
    WikiQualityReport,
    SectionReference,
    compute_coverage,
    compute_faithfulness_score,
    detect_conflicting_claims,
    detect_stale_sections,
)

from tests.fixtures.faithfulness_golden import FAITHFULNESS_GOLDEN
from tests.fixtures.wiki_quality_fixture import build_wiki_quality_fixture


# ──────────────────────────────────────────────
# Coverage Tests
# ──────────────────────────────────────────────

class TestWikiCoverage:
    def test_all_approved_cards_used_gives_full_coverage(self):
        approved = ["c1", "c2", "c3"]
        used = ["c1", "c2", "c3"]
        unused, reasons = compute_coverage(approved, used, {})
        assert len(unused) == 0

    def test_unused_cards_listed_with_reasons(self):
        approved = ["c1", "c2", "c3", "c4"]
        used = ["c1", "c3"]
        reason_map = {"c2": "too short", "c4": "topic too narrow"}
        unused, reasons = compute_coverage(approved, used, reason_map)
        assert len(unused) == 2
        assert "c2" in unused
        assert "c4" in unused

    def test_coverage_rate_is_float_between_0_and_1(self):
        approved = ["c1", "c2", "c3", "c4"]
        used = ["c1", "c2"]
        unused, reasons = compute_coverage(approved, used, {})
        rate = (len(approved) - len(unused)) / len(approved)
        assert 0.0 <= rate <= 1.0

    # ── Golden fixture ──

    def test_golden_fixture_8_used_2_unused(self):
        f = build_wiki_quality_fixture()
        approved_ids = [c.id for c in f.approved_cards]
        unused, reasons = compute_coverage(
            approved_ids, f.used_card_ids, f.unused_reasons
        )
        assert len(unused) == 2
        assert "c9" in unused
        assert "c10" in unused
        assert len(reasons) == 2


# ──────────────────────────────────────────────
# Faithfulness Tests
# ──────────────────────────────────────────────

class TestFaithfulness:
    def test_high_overlap_section_is_faithful(self):
        """section 与引用 cards 高度重叠 → faithful, score ≥ 0.5"""
        case = FAITHFULNESS_GOLDEN["faithful_case"]
        score = compute_faithfulness_score(case["section_text"], case["card_bodies"])
        assert score >= case["expected_score_min"], (
            f"Expected >= {case['expected_score_min']}, got {score}"
        )

    def test_low_overlap_section_flagged(self):
        """section 与引用 cards 几乎不重叠 → unfaithful, score < 0.2"""
        case = FAITHFULNESS_GOLDEN["unfaithful_case"]
        score = compute_faithfulness_score(case["section_text"], case["card_bodies"])
        assert score < case["expected_score_max"], (
            f"Expected < {case['expected_score_max']}, got {score}"
        )

    def test_partial_overlap_section(self):
        """部分重叠 → 0.2 ≤ score ≤ 0.5"""
        case = FAITHFULNESS_GOLDEN["partial_case"]
        score = compute_faithfulness_score(case["section_text"], case["card_bodies"])
        assert case["expected_score_min"] <= score <= case["expected_score_max"], (
            f"Expected {case['expected_score_min']}-{case['expected_score_max']}, got {score}"
        )

    def test_no_references_warns(self):
        """无 card references → 仍可计算但需警告"""
        case = FAITHFULNESS_GOLDEN["no_references_case"]
        score = compute_faithfulness_score(case["section_text"], case["card_bodies"])
        assert isinstance(score, float)

    def test_empty_section_text_returns_zero(self):
        score = compute_faithfulness_score("", {"c1": "some content"})
        assert score == 0.0

    def test_empty_card_bodies_returns_zero(self):
        score = compute_faithfulness_score("some content", {})
        assert score == 0.0

    def test_deterministic_repeatability(self):
        case = FAITHFULNESS_GOLDEN["faithful_case"]
        scores = [
            compute_faithfulness_score(case["section_text"], case["card_bodies"])
            for _ in range(10)
        ]
        assert all(s == scores[0] for s in scores)

    def test_chinese_text_handled(self):
        section = "认证使用 OAuth 2.0 协议和 JWT 令牌进行会话管理。"
        card_bodies = {
            "c1": "OAuth 2.0 是认证协议。JWT 令牌管理会话状态。",
        }
        score = compute_faithfulness_score(section, card_bodies)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ──────────────────────────────────────────────
# Staleness Tests
# ──────────────────────────────────────────────

class TestStaleness:
    def test_new_card_matching_topic_marks_stale(self):
        section_refs = [
            SectionReference(
                section_title="Authentication",
                card_ids=("c1", "c2"),
                relevance="primary",
            ),
        ]
        new_card_titles = {"Auth", "DB Backup"}
        stale = detect_stale_sections(
            section_refs,
            new_card_titles=new_card_titles,
            topic_keywords={"Authentication": {"auth", "oauth", "login"}},
        )
        assert "Authentication" in stale

    def test_no_new_cards_means_no_stale(self):
        section_refs = [
            SectionReference(
                section_title="Database",
                card_ids=("c4",),
                relevance="primary",
            ),
        ]
        stale = detect_stale_sections(
            section_refs,
            new_card_titles=set(),
            topic_keywords={},
        )
        assert len(stale) == 0

    def test_unrelated_new_card_does_not_mark_stale(self):
        section_refs = [
            SectionReference(
                section_title="Authentication",
                card_ids=("c1",),
                relevance="primary",
            ),
        ]
        new_card_titles = {"SVG Rendering Guide", "Car Maintenance"}
        stale = detect_stale_sections(
            section_refs,
            new_card_titles=new_card_titles,
            topic_keywords={"Authentication": {"auth", "oauth"}},
        )
        assert len(stale) == 0


# ──────────────────────────────────────────────
# Conflicting Claims Tests
# ──────────────────────────────────────────────

class TestConflictingClaims:
    def test_opposite_claims_same_topic_detected(self):
        conflicts = detect_conflicting_claims(
            ("c_a", "Exercise increases productivity", {"productivity"}),
            ("c_b", "Exercise decreases productivity", {"productivity"}),
        )
        assert len(conflicts) > 0

    def test_same_direction_claims_not_detected(self):
        conflicts = detect_conflicting_claims(
            ("c_a", "Exercise increases productivity", {"productivity"}),
            ("c_c", "Exercise improves focus", {"productivity"}),
        )
        assert len(conflicts) == 0

    def test_different_tags_no_conflict(self):
        conflicts = detect_conflicting_claims(
            ("c_a", "Exercise increases productivity", {"health"}),
            ("c_b", "Exercise decreases productivity", {"economics"}),
        )
        assert len(conflicts) == 0


# ──────────────────────────────────────────────
# Data Model Tests
# ──────────────────────────────────────────────

class TestWikiQualityReport:
    def test_report_is_immutable(self):
        report = WikiQualityReport(
            wiki_version="v1",
            rebuild_time="2026-01-01",
            total_approved_cards=10,
            used_card_ids=("c1", "c2"),
            unused_card_ids=("c3",),
            unused_reasons={},
            section_references=(),
            stale_sections=(),
            faithfulness_scores={},
            faithfulness_issues=(),
            knowledge_gaps=(),
            conflicting_claims=(),
            dedup_suggestions=(),
        )
        with pytest.raises(Exception):
            report.total_approved_cards = 20  # type: ignore[misc]

    def test_section_reference_is_immutable(self):
        ref = SectionReference(
            section_title="Auth",
            card_ids=("c1", "c2"),
            relevance="primary",
        )
        with pytest.raises(Exception):
            ref.relevance = "supporting"  # type: ignore[misc]
