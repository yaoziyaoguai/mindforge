"""M5 Knowledge Health unit tests — SDD §9, TDD §6。"""

import pytest

from mindforge.health.health_service import (
    HealthIssue,
    HealthReport,
    Severity,
    compute_health_report,
)

from tests.fixtures.health_golden import (
    SyntheticHealthCard,
    build_health_golden_vault,
)


def _card_dict(card: SyntheticHealthCard) -> dict[str, object]:
    return {
        "id": card.id,
        "status": card.status,
        "quality_level": card.quality_level,
        "source_id": card.source_id,
        "tags": list(card.tags),
        "title": card.title,
    }


# ──────────────────────────────────────────────
# Unit tests
# ──────────────────────────────────────────────

class TestHealthReport:
    def test_review_backlog_detected(self):
        report = compute_health_report(
            cards=[],
            pending_drafts=5,
            wiki_stale_sections=(),
        )
        codes = {i.code for i in report.issues}
        assert "review_backlog" in codes

    def test_no_backlog_when_below_threshold(self):
        report = compute_health_report(
            cards=[],
            pending_drafts=1,
            wiki_stale_sections=(),
        )
        codes = {i.code for i in report.issues}
        assert "review_backlog" not in codes

    def test_orphan_cards_detected(self):
        cards = [
            SyntheticHealthCard(id="c1", source_id="src_1"),
        ]
        report = compute_health_report(
            cards=[_card_dict(c) for c in cards],
            pending_drafts=0,
            wiki_stale_sections=(),
            # c1 has no related cards and no wiki references
            card_wiki_refs={"c1": ()},
            card_related_count={"c1": 0},
        )
        codes = {i.code for i in report.issues}
        assert "orphans" in codes

    def test_low_quality_cards_detected(self):
        cards = [
            SyntheticHealthCard(id="c_low", quality_level="low"),
        ]
        report = compute_health_report(
            cards=[_card_dict(c) for c in cards],
            pending_drafts=0,
            wiki_stale_sections=(),
        )
        codes = {i.code for i in report.issues}
        assert "low_quality" in codes

    def test_duplicates_detected(self):
        cards = [
            SyntheticHealthCard(id="c_a", title="Auth Pattern Guide", tags=("auth",)),
            SyntheticHealthCard(id="c_b", title="Auth Pattern Guidelines", tags=("auth",)),
        ]
        report = compute_health_report(
            cards=[_card_dict(c) for c in cards],
            pending_drafts=0,
            wiki_stale_sections=(),
        )
        codes = {i.code for i in report.issues}
        assert "duplicates" in codes

    def test_wiki_stale_sections_detected(self):
        report = compute_health_report(
            cards=[],
            pending_drafts=0,
            wiki_stale_sections=("Authentication",),
        )
        codes = {i.code for i in report.issues}
        assert "wiki_stale" in codes

    def test_each_issue_has_severity_and_suggested_action(self):
        cards = [
            SyntheticHealthCard(id="c_low", quality_level="low"),
        ]
        report = compute_health_report(
            cards=[_card_dict(c) for c in cards],
            pending_drafts=0,
            wiki_stale_sections=(),
        )
        for issue in report.issues:
            assert issue.severity in (Severity.CRITICAL, Severity.WARN, Severity.INFO)
            assert len(issue.suggested_action) > 0
            assert len(issue.message) > 0

    def test_no_auto_mutation(self):
        cards = [
            SyntheticHealthCard(id="c1", quality_level="low"),
        ]
        original = [dict(c.__dict__) for c in cards]
        compute_health_report(
            cards=[_card_dict(c) for c in cards],
            pending_drafts=0,
            wiki_stale_sections=(),
        )
        restored = [dict(c.__dict__) for c in cards]
        assert restored == original, "Health report must not mutate cards"

    # ── Golden fixture ──

    def test_golden_vault_all_expected_issues_detected(self):
        vault = build_health_golden_vault()
        report = compute_health_report(
            cards=[_card_dict(c) for c in vault.cards],
            pending_drafts=vault.pending_drafts,
            wiki_stale_sections=vault.wiki_stale_sections,
            card_wiki_refs={"c_orphan": ()},
            card_related_count={"c_orphan": 0, "c_low_1": 0, "c_dup_a": 0, "c_dup_b": 0, "c_normal": 0},
        )
        detected = {i.code for i in report.issues}
        for code in vault.expected_issue_codes:
            assert code in detected, f"Expected issue '{code}' not found"


# ──────────────────────────────────────────────
# Data model tests
# ──────────────────────────────────────────────

class TestHealthReportModel:
    def test_report_is_immutable(self):
        report = HealthReport(issues=(), summary="ok")
        with pytest.raises(Exception):
            report.issues = ()  # type: ignore[misc]

    def test_health_issue_is_immutable(self):
        issue = HealthIssue(
            code="test",
            severity=Severity.INFO,
            message="test message",
            suggested_action="do something",
        )
        with pytest.raises(Exception):
            issue.severity = Severity.CRITICAL  # type: ignore[misc]
