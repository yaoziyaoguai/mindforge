"""Card approval metadata contract tests."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from mindforge.cards import iter_cards
from mindforge.library_presenter import render_library_detail
from mindforge.library_service import LibraryCard, LibraryCardDetail


def _write_card(cards: Path, frontmatter: str) -> Path:
    cards.mkdir(parents=True, exist_ok=True)
    card = cards / "card.md"
    card.write_text(f"---\n{frontmatter}---\n\n## Body\n", encoding="utf-8")
    return card


def test_card_summary_reads_real_approved_at(tmp_path: Path) -> None:
    """approved_at 只来自真实 approval metadata。"""

    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    _write_card(
        cards,
        """id: approved-1
title: Approved
status: human_approved
approved_at: 2026-05-10T09:00:00+08:00
reviewed_at: 2026-05-11T09:00:00+08:00
""",
    )

    summary = iter_cards(vault, "20-Knowledge-Cards").cards[0]

    assert summary.approved_at is not None
    assert summary.approved_at.isoformat() == "2026-05-10T09:00:00+08:00"
    assert summary.reviewed_at is not None


def test_legacy_reviewed_at_does_not_populate_approved_at(tmp_path: Path) -> None:
    """reviewed_at 是复习时间，不是 approval timestamp，不能作为 fallback。"""

    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    _write_card(
        cards,
        """id: reviewed-only
title: Reviewed Only
status: human_approved
reviewed_at: 2026-05-11T09:00:00+08:00
""",
    )

    summary = iter_cards(vault, "20-Knowledge-Cards").cards[0]

    assert summary.approved_at is None
    assert summary.reviewed_at is not None
    assert summary.reviewed_at.isoformat() == "2026-05-11T09:00:00+08:00"


def test_library_presenter_does_not_label_reviewed_at_as_approved_at(tmp_path: Path) -> None:
    """CLI Library detail 的 approved_at 行不能使用 reviewed_at 的值。"""

    vault = tmp_path / "vault"
    cards = vault / "20-Knowledge-Cards"
    _write_card(
        cards,
        """id: reviewed-only
title: Reviewed Only
status: human_approved
reviewed_at: 2026-05-11T09:00:00+08:00
""",
    )
    summary = iter_cards(vault, "20-Knowledge-Cards").cards[0]
    detail = LibraryCardDetail(
        card=LibraryCard(
            summary=summary,
            source_missing=False,
            source_lookup_path=None,
            status_explanation="human_approved",
            fallback_provider_note=None,
        ),
        body=None,
    )
    console = Console(record=True, width=120)

    render_library_detail(console, detail)

    output = console.export_text()
    assert "approved_at         : -" in output
    assert "2026-05-11T09:00:00+08:00" not in output
