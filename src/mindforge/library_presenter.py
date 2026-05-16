"""Presenter for ``mindforge library``.

展示层只消费 library_service 的结构化结果，不重新读取卡片或 source。这样 CLI
文案调整不会触碰 inventory 业务规则。
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from .library_service import LibraryCardDetail, LibraryInventory, LibraryStats


def render_library_stats(console: Console, stats: LibraryStats) -> None:
    console.print("[bold]MindForge Library Stats[/bold]")
    console.print(f"vault.root: {stats.vault_root}", markup=False, soft_wrap=True)
    console.print(f"cards_dir : {stats.cards_dir}", markup=False, soft_wrap=True)
    console.print(f"total cards: {stats.total_cards}", markup=False)
    console.print(f"by status : {_counts(stats.by_status)}", markup=False)
    console.print(f"by track  : {_counts(stats.by_track)}", markup=False)
    console.print(f"by model: {_counts(stats.by_provider)}", markup=False)
    console.print(
        f"index     : path={stats.index_path} exists={'yes' if stats.index_exists else 'no'}",
        markup=False,
        soft_wrap=True,
    )
    console.print(f"recent card count: {stats.recent_count}", markup=False)
    console.print(f"next recommended action: {stats.next_action}", markup=False)
    if stats.scan_errors:
        console.print(f"[yellow]scan errors: {len(stats.scan_errors)} unreadable cards[/yellow]")


def render_library_list(console: Console, inventory: LibraryInventory) -> None:
    if not inventory.cards:
        console.print("[yellow]知识库暂无 Knowledge Cards。[/yellow]")
        console.print("下一步：mindforge watch add <file-or-folder>", markup=False)
        return
    table = Table(title=f"Knowledge Library · {inventory.stats.total_cards} cards")
    for col in (
        "title",
        "status",
        "track",
        "source",
        "model",
        "updated",
        "path",
    ):
        table.add_column(col, overflow="fold")
    for item in inventory.cards:
        card = item.summary
        table.add_row(
            card.title or "?",
            card.status,
            card.track or "-",
            (
                f"{card.source_type or '-'} / {card.adapter_name or '-'} / "
                f"{card.source_title or '-'} / source_missing={'yes' if item.source_missing else 'no'}"
            ),
            card.profile or card.provider or "-",
            card.updated_at.isoformat(timespec="minutes") if card.updated_at else "-",
            card.rel_path,
        )
    console.print(table)
    console.print("[bold]Cards[/bold]")
    for item in inventory.cards:
        card = item.summary
        console.print(
            f"- {card.title or '?'} · status={card.status} · track={card.track or '-'} · "
            f"source_type={card.source_type or '-'} · adapter_name={card.adapter_name or '-'} · "
            f"source_title={card.source_title or '-'} · source_missing={'yes' if item.source_missing else 'no'} · "
            f"model={card.profile or card.provider or '-'} · path={card.rel_path}",
            markup=False,
            soft_wrap=True,
        )
    console.print("[dim]默认只展示 metadata，不读取 source 正文，也不展示 card body。[/dim]")


def render_library_detail(console: Console, detail: LibraryCardDetail) -> None:
    card = detail.card.summary
    console.print("[bold]Knowledge Card[/bold]")
    rows = {
        "title": card.title or "-",
        "status": card.status,
        "status_note": detail.card.status_explanation,
        "track": card.track or "-",
        "source_type": card.source_type or "-",
        "adapter_name": card.adapter_name or "-",
        "source_title": card.source_title or "-",
        "source_path": card.source_path or "-",
        "source_archive_path": card.source_archive_path or "-",
        "source_missing": "yes" if detail.card.source_missing else "no",
        "model": card.profile or card.provider or "-",
        "approved_at": card.reviewed_at.isoformat() if card.reviewed_at else "-",
        "path": card.rel_path,
    }
    for key, value in rows.items():
        console.print(f"{key:<20}: {value}", markup=False, soft_wrap=True)
    console.print(f"source_missing={'yes' if detail.card.source_missing else 'no'}", markup=False)
    if detail.card.fallback_provider_note:
        console.print(detail.card.fallback_provider_note, markup=False)
    if detail.body is not None:
        console.print("\n[bold]Card body[/bold]")
        console.print(detail.body, markup=False)
    else:
        console.print(
            "\nBoundary: metadata only. Use --show-content to display card body; source body is never shown.",
            markup=False,
        )


def _counts(counts: dict[str, int]) -> str:
    if not counts:
        return "-"
    return " ".join(f"{key}={value}" for key, value in sorted(counts.items()))


__all__ = ["render_library_detail", "render_library_list", "render_library_stats"]
