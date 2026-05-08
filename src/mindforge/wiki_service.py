"""Main Wiki service —— 从 approved cards 确定性地生成派生 Wiki 视图。

中文学习型说明：Wiki 是 approved cards 的只读派生视图，不是 source、不是
审批入口、不是唯一知识源。rebuild 总是从 approved card 集合重新生成，使用
确定性模板（不调 LLM）。provenance 由代码自动追加，不会被 LLM 删除。

Wiki 文件放在 ``30-Wiki/Main-Wiki.md``，与 cards(20-Knowledge-Cards) 分开。
写入使用 atomic write（先写 .tmp 再 replace），失败时旧 Wiki 保持不变。
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

from .cards import CardSummary, extract_section, iter_cards, read_card_body
from .config import MindForgeConfig


@dataclass(frozen=True)
class WikiRebuildResult:
    wiki_path: str
    included_cards: int
    excluded_trashed: int
    last_rebuilt_at: str
    card_count: int


@dataclass(frozen=True)
class WikiStatus:
    wiki_path: str
    exists: bool
    last_rebuilt_at: str | None = None
    approved_card_count: int = 0
    wiki_card_count: int = 0


class WikiError(ValueError):
    """Wiki 操作失败；message 可安全返回给 Web/CLI。"""


def _wiki_root(cfg: MindForgeConfig) -> Path:
    return cfg.vault.root / "30-Wiki"


def _wiki_path(cfg: MindForgeConfig) -> Path:
    return _wiki_root(cfg) / "Main-Wiki.md"


def rebuild_main_wiki(cfg: MindForgeConfig) -> WikiRebuildResult:
    """从 approved cards 重建 Main Wiki（deterministic template，不调 LLM）。

    只包含 human_approved 卡片，排除 ai_draft 和 trashed cards。
    """
    wiki_dir = _wiki_root(cfg)
    wiki_path = _wiki_path(cfg)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # 收集 approved cards（排除 ai_draft）
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved = [c for c in scan.cards if c.status == "human_approved"]

    # 排除 trashed cards（不在 cards_dir 中 = 已被 trash）
    # iter_cards 只扫描 cards_dir，trashed 在 90-Archive/ 不被扫到，
    # 所以 approved card 列表已天然排除 trashed cards。
    # 仅记录 card 数量。
    trashed_excluded = 0  # 本轮不追踪，后续可接入 trash_service

    # 按 track 分组
    by_track: dict[str, list[CardSummary]] = {}
    for c in approved:
        track = c.track or "unrouted"
        by_track.setdefault(track, []).append(c)

    # 生成 Wiki
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    lines: list[str] = []
    lines.append("# MindForge Main Wiki\n")
    lines.append("<!-- Wiki generated from approved knowledge cards. Do not edit directly. -->\n")
    lines.append("> This wiki is generated from human-approved knowledge cards.\n")
    lines.append("> It is a derived view. Source files are not copied into this wiki.\n")
    lines.append(f"> Last rebuilt: {now}\n")
    lines.append(f"> Cards included: {len(approved)}\n\n")

    lines.append("## Overview\n\n")
    lines.append(f"- **Cards included**: {len(approved)}\n")
    lines.append(f"- **Last rebuilt**: {now}\n\n")

    for track, cards in sorted(by_track.items()):
        lines.append(f"## {track}\n\n")
        for card in cards:
            _append_card_section(lines, card)
        lines.append("")

    content = "".join(lines)

    # Atomic write
    tmp = wiki_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(str(tmp), str(wiki_path))

    return WikiRebuildResult(
        wiki_path=str(wiki_path),
        included_cards=len(approved),
        excluded_trashed=trashed_excluded,
        last_rebuilt_at=now,
        card_count=len(approved),
    )


def read_main_wiki(cfg: MindForgeConfig) -> str | None:
    """读 Main Wiki 内容。不存在时返回 None。"""
    path = _wiki_path(cfg)
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def get_wiki_status(cfg: MindForgeConfig) -> WikiStatus:
    """返回 Main Wiki 状态摘要。"""
    path = _wiki_path(cfg)
    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    approved_count = sum(1 for c in scan.cards if c.status == "human_approved")

    if not path.is_file():
        return WikiStatus(
            wiki_path=str(path),
            exists=False,
            approved_card_count=approved_count,
        )

    # 从 Wiki 内容中提取 last_rebuilt_at 和 card_count
    text = path.read_text(encoding="utf-8")
    last_rebuilt = None
    wiki_cards = 0
    for line in text.split("\n"):
        if "Last rebuilt:" in line:
            last_rebuilt = line.split("Last rebuilt:")[-1].strip()
        if "Cards included:" in line:
            try:
                wiki_cards = int(line.split(":")[-1].strip())
            except ValueError:
                pass

    return WikiStatus(
        wiki_path=str(path),
        exists=True,
        last_rebuilt_at=last_rebuilt,
        approved_card_count=approved_count,
        wiki_card_count=wiki_cards,
    )


def _append_card_section(lines: list[str], card: CardSummary) -> None:
    """追加单张 approved card 的 Wiki section。"""
    title = card.title or card.id or "Untitled"
    lines.append(f"<!-- WIKI_SECTION_START card={card.id} -->\n")
    lines.append(f"### {title}\n\n")

    # 读 body 提取摘要
    try:
        body = read_card_body(card.path)
    except Exception:
        body = ""
    summary = extract_section(body, "AI Summary") if body else ""
    principles = extract_section(body, "Principles") if body else ""
    actions = extract_section(body, "Action Items") if body else ""

    if summary:
        lines.append(f"{summary}\n\n")
    if principles:
        lines.append(f"**Principles:**\n{principles}\n\n")
    if actions:
        lines.append(f"**Action Items:**\n{actions}\n\n")

    # Provenance（代码自动追加）
    lines.append("**Provenance:**\n\n")
    lines.append(f"- **Source card**: [{title}](../20-Knowledge-Cards/{card.rel_path.rsplit('/', 1)[-1] if '/' in card.rel_path else card.rel_path})\n")
    lines.append(f"- **Card path**: `{card.rel_path}`\n")
    if card.source_title:
        lines.append(f"- **Original source**: {card.source_title}\n")
    elif card.source_path:
        lines.append(f"- **Original source**: `{card.source_path}`\n")
    if card.strategy_id:
        lines.append(f"- **Strategy**: {card.strategy_id} v{card.strategy_version or '?'}\n")
    if card.tags:
        lines.append(f"- **Tags**: {', '.join(card.tags)}\n")
    if card.value_score is not None:
        lines.append(f"- **Value score**: {card.value_score}\n")

    lines.append("\n<!-- WIKI_SECTION_END -->\n")
    lines.append("---\n\n")


__all__ = [
    "WikiRebuildResult",
    "WikiStatus",
    "WikiError",
    "rebuild_main_wiki",
    "read_main_wiki",
    "get_wiki_status",
]
