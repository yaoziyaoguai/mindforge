"""Knowledge library inventory service.

中文学习型说明：Library 是"我已经有哪些知识卡"的只读查询面。它复用
``cards.iter_cards`` 的白名单摘要，不读取 source 正文，不调用 LLM，也不做
approve。CLI / Web 都应通过这里拿 inventory，避免各自重新扫描和拼字段。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .approval_service import resolve_user_card_path
from .cards import CardLoadError, CardSummary, iter_cards, read_card_body
from .config import MindForgeConfig
from .lexical_index import default_index_path


@dataclass(frozen=True)
class LibraryCard:
    summary: CardSummary
    source_missing: bool
    source_lookup_path: Path | None
    status_explanation: str
    fake_provider_note: str | None


@dataclass(frozen=True)
class LibraryStats:
    vault_root: Path
    cards_dir: str
    total_cards: int
    by_status: dict[str, int]
    by_track: dict[str, int]
    by_provider: dict[str, int]
    recent_count: int
    index_path: Path
    index_exists: bool
    next_action: str
    scan_errors: tuple[CardLoadError, ...]


@dataclass(frozen=True)
class LibraryInventory:
    stats: LibraryStats
    cards: tuple[LibraryCard, ...]


@dataclass(frozen=True)
class LibraryCardDetail:
    card: LibraryCard
    body: str | None = None


@dataclass(frozen=True)
class LibraryLookupError:
    message: str
    exit_code: int = 2


def build_library_inventory(cfg: MindForgeConfig, *, limit: int = 200) -> LibraryInventory:
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards = tuple(_library_card(cfg, card) for card in scan.cards[:limit])
    return LibraryInventory(
        stats=_stats(cfg, tuple(scan.cards), scan_errors=scan.errors),
        cards=cards,
    )


def show_library_card(
    cfg: MindForgeConfig,
    card_ref: str,
    *,
    show_content: bool = False,
) -> LibraryCardDetail | LibraryLookupError:
    path = _resolve_card_ref(cfg, card_ref)
    if path is None:
        return LibraryLookupError(
            "未找到 card。可传 card id、绝对路径、当前目录相对路径，或 vault-relative path。"
        )
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    for card in scan.cards:
        if card.path == path.resolve():
            body = read_card_body(card.path) if show_content else None
            return LibraryCardDetail(card=_library_card(cfg, card), body=body)
    return LibraryLookupError(f"card frontmatter 无法作为安全摘要读取：{path}")


def _stats(
    cfg: MindForgeConfig,
    cards: tuple[CardSummary, ...],
    *,
    scan_errors: tuple[CardLoadError, ...],
) -> LibraryStats:
    by_status = Counter(card.status for card in cards)
    by_track = Counter(card.track or "unrouted" for card in cards)
    by_provider = Counter(_provider_label(card) for card in cards)
    recent = sorted(
        (card for card in cards if card.updated_at is not None),
        key=lambda card: card.updated_at,
        reverse=True,
    )[:10]
    index_path = default_index_path(cfg.state.workdir)
    next_action = "mindforge approve list"
    if by_status.get("ai_draft", 0) == 0 and by_status.get("human_approved", 0) > 0:
        next_action = "mindforge index rebuild"
    if not cards:
        next_action = "mindforge watch add <file-or-folder>"
    return LibraryStats(
        vault_root=cfg.vault.root,
        cards_dir=cfg.vault.cards_dir,
        total_cards=len(cards),
        by_status=dict(by_status),
        by_track=dict(by_track),
        by_provider=dict(by_provider),
        recent_count=len(recent),
        index_path=index_path,
        index_exists=index_path.exists(),
        next_action=next_action,
        scan_errors=scan_errors,
    )


def _library_card(cfg: MindForgeConfig, card: CardSummary) -> LibraryCard:
    lookup = _source_lookup_path(cfg, card)
    source_missing = card.source_missing
    if lookup is not None and not lookup.exists():
        source_missing = True
    return LibraryCard(
        summary=card,
        source_missing=source_missing,
        source_lookup_path=lookup,
        status_explanation=_status_explanation(card.status),
        fake_provider_note=_fake_note(card),
    )


def _source_lookup_path(cfg: MindForgeConfig, card: CardSummary) -> Path | None:
    raw = card.source_archive_path or card.source_path
    if not raw:
        return None
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path
    return cfg.vault.root / path


def _resolve_card_ref(cfg: MindForgeConfig, card_ref: str) -> Path | None:
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    matches = [
        card.path
        for card in scan.cards
        if card.id == card_ref
        or card.rel_path == card_ref
        or Path(card.rel_path).name == card_ref
        or Path(card.rel_path).stem == card_ref
    ]
    if len(matches) == 1:
        return matches[0]
    resolved = resolve_user_card_path(cfg, Path(card_ref))
    return resolved.path.resolve() if resolved.ok and resolved.path is not None else None


def _status_explanation(status: str) -> str:
    if status == "ai_draft":
        return "ai_draft：AI 草稿，不是正式知识"
    if status == "human_approved":
        return "human_approved：显式 approve 后进入正式知识库"
    return f"{status}：非标准或历史状态"


def _provider_label(card: CardSummary) -> str:
    if card.profile:
        return card.profile
    if card.provider:
        return card.provider
    return "unknown"


def _fake_note(card: CardSummary) -> str | None:
    label = f"{card.profile or ''} {card.provider or ''}".lower()
    if "fake" in label:
        return "fake provider：用于安全跑通流程，不代表真实卡片质量。"
    return None


__all__ = [
    "LibraryCard",
    "LibraryCardDetail",
    "LibraryInventory",
    "LibraryLookupError",
    "LibraryStats",
    "build_library_inventory",
    "show_library_card",
]
