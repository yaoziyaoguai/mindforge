"""M5 Knowledge Health unit tests — SDD §9, TDD §6。"""

import pytest

from mindforge.health.health_service import (
    HealthIssue,
    HealthReport,
    KnowledgeHealthReport,
    Severity,
    build_knowledge_health_report,
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
            assert len(issue.reason) > 0
            assert len(issue.suggested_action) > 0
            assert len(issue.message) > 0

    def test_missing_provenance_detected(self):
        report = compute_health_report(
            cards=[
                {
                    "id": "c_missing",
                    "status": "human_approved",
                    "quality_level": "medium",
                    "title": "Missing provenance",
                    "source_id": None,
                    "source_path": None,
                    "source_type": None,
                    "adapter_name": None,
                }
            ],
            pending_drafts=0,
            wiki_stale_sections=(),
        )
        issue = next(i for i in report.issues if i.code == "missing_provenance")
        assert issue.severity == Severity.WARN
        assert issue.affected_card_ids == ("c_missing",)

    def test_source_warnings_detected(self):
        report = compute_health_report(
            cards=[],
            pending_drafts=0,
            wiki_stale_sections=(),
            source_warnings=("unsupported_legacy_doc: legacy.doc", "scanned_pdf_no_text"),
        )
        issue = next(i for i in report.issues if i.code == "source_warnings")
        assert issue.severity == Severity.INFO
        assert "unsupported_legacy_doc" in issue.reason

    def test_summary_stats_include_maintenance_counts(self):
        report = compute_health_report(
            cards=[
                {"id": "draft", "status": "ai_draft", "title": "Draft"},
                {"id": "approved", "status": "human_approved", "title": "Approved"},
            ],
            pending_drafts=1,
            wiki_stale_sections=(),
            source_warnings=("decode_error",),
        )
        assert report.stats["total_cards"] == 2
        assert report.stats["approved"] == 1
        assert report.stats["pending_drafts"] == 1
        assert report.stats["source_warnings"] == 1
        assert report.maintenance_suggestions

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

    def test_knowledge_health_report_alias_is_available(self):
        report = KnowledgeHealthReport(issues=(), summary="ok")
        assert isinstance(report, HealthReport)

    def test_health_issue_is_immutable(self):
        issue = HealthIssue(
            code="test",
            severity=Severity.INFO,
            message="test message",
            suggested_action="do something",
        )
        with pytest.raises(Exception):
            issue.severity = Severity.CRITICAL  # type: ignore[misc]


def test_build_knowledge_health_report_from_real_config(tmp_path):
    """真实配置入口从 vault/state/wiki 聚合，只读生成 health report。"""
    import yaml
    from mindforge.app_context import load_app_config

    vault = tmp_path / "vault"
    cards_dir = vault / "20-Knowledge-Cards"
    wiki_dir = vault / "30-Wiki"
    cards_dir.mkdir(parents=True)
    wiki_dir.mkdir(parents=True)
    cfg_path = tmp_path / "mindforge.yaml"
    cfg_path.write_text(
        yaml.safe_dump(
            {
                "version": 0.7,
                "vault": {
                    "root": str(vault),
                    "inbox_root": "00-Inbox",
                    "cards_dir": "20-Knowledge-Cards",
                    "archive_dir": "90-Archive/Skipped",
                },
                "llm": {
                    "active": "fake",
                    "providers": {"fake": {"type": "fake", "purpose": "test"}},
                },
                "telemetry": {"enabled": True, "local_only": True},
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (cards_dir / "approved.md").write_text(
        """---
id: approved-1
title: Approved Missing Provenance
status: human_approved
---

tiny
""",
        encoding="utf-8",
    )
    (cards_dir / "draft.md").write_text(
        """---
id: draft-1
title: Draft
status: ai_draft
source_id: src
source_type: txt
source_path: note.txt
source_content_hash: sha256:test
adapter_name: TxtAdapter
---

draft body
""",
        encoding="utf-8",
    )
    (wiki_dir / "Main-Wiki.md").write_text(
        """> Cards included: 0
> Last rebuilt: 2026-01-01T00:00:00+0000
""",
        encoding="utf-8",
    )
    cfg = load_app_config(cfg_path, cwd=tmp_path)

    report = build_knowledge_health_report(cfg)

    codes = {issue.code for issue in report.issues}
    assert "missing_provenance" in codes
    assert "wiki_stale" in codes
    assert report.stats["total_cards"] == 2
    assert report.stats["pending_drafts"] == 1
