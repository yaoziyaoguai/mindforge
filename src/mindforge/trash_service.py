"""Knowledge Card Trash service。

中文学习型说明：Trash 语义是"安全移动卡片到回收站"，不是"永久删除"。
Move to Trash 只移动卡片文件，不删除 source 原文、不删除其他卡片、
不修改 processing history。Trash 目录在 ``90-Archive/Trash/Knowledge-Cards/``，
位于 cards_dir 之外，``iter_cards`` 不会扫描到。

Restore 将卡片移回原路径（或冲突安全路径），并根据 previous_status 恢复可见性。
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .cards import CardSummary, iter_cards
from .config import MindForgeConfig


@dataclass(frozen=True)
class TrashResult:
    card_id: str
    title: str
    previous_status: str
    original_path: str
    trashed_at: str
    trash_rel_path: str


@dataclass(frozen=True)
class TrashCardSummary:
    """Trash 列表中的卡片摘要 —— 不含 body，安全展示。"""
    trash_rel_path: str
    title: str
    previous_status: str
    original_path: str
    trashed_at: str
    track: str | None = None
    tags: list[str] = field(default_factory=list)
    source_title: str | None = None


@dataclass(frozen=True)
class RestoreResult:
    card_id: str
    title: str
    restored_path: str
    previous_status: str
    conflict_resolved: bool = False


class TrashError(ValueError):
    """Trash 操作失败；message 可安全返回给 Web/CLI。"""


def _trash_root(cfg: MindForgeConfig) -> Path:
    """Trash 目录路径：``vault_root/90-Archive/Trash/Knowledge-Cards/``。

    位于 cards_dir 之外，确保 iter_cards 不会扫描到 trashed cards。
    """
    return cfg.vault.root / "90-Archive" / "Trash" / "Knowledge-Cards"


def move_card_to_trash(
    cfg: MindForgeConfig,
    card_path: Path,
    *,
    reason: str | None = None,
) -> TrashResult:
    """将单张 Knowledge Card 移动到 Trash。

    只移动卡片文件；不删除 source 原文、不删除其他卡片。
    在 frontmatter 中追加 trashed_at / original_path / previous_status。
    """
    resolved = _validate_card_in_vault(cfg, card_path)

    # 读 frontmatter
    text = resolved.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise TrashError("card 缺少 frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise TrashError("card frontmatter 未闭合")
    fm_text = rest[:end]
    body = rest[end + 5:]

    # 解析已有字段
    title = _extract_fm_field(fm_text, "title", "")
    status = _extract_fm_field(fm_text, "status", "unknown")
    card_id = _extract_fm_field(fm_text, "id", str(resolved.stem))

    # 追加 trash metadata（不破坏已有 provenance）
    now = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    original_rel = _rel_path(cfg.vault.root, resolved)
    fm_lines = fm_text.split("\n")
    fm_lines.append(f"trashed_at: {now}")
    fm_lines.append(f"original_path: \"{original_rel}\"")
    fm_lines.append(f"previous_status: {status}")
    if reason:
        fm_lines.append(f"trash_reason: \"{reason}\"")

    # 生成 trash 文件名
    trash_dir = _trash_root(cfg)
    trash_dir.mkdir(parents=True, exist_ok=True)
    trash_name = resolved.name
    trash_path = trash_dir / trash_name
    if trash_path.exists():
        # 冲突安全：加时间戳后缀
        stem = resolved.stem
        trash_name = f"{stem}--trashed-{int(time.time())}.md"
        trash_path = trash_dir / trash_name

    # 原子写入 trash 文件，再删除原文件
    new_fm = "\n".join(fm_lines)
    new_text = f"---\n{new_fm}\n---\n{body}"
    tmp = trash_path.with_suffix(".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(str(tmp), str(trash_path))
    resolved.unlink()

    return TrashResult(
        card_id=card_id,
        title=title,
        previous_status=status,
        original_path=original_rel,
        trashed_at=now,
        trash_rel_path=_rel_path(cfg.vault.root, trash_path),
    )


def list_trashed_cards(cfg: MindForgeConfig) -> list[TrashCardSummary]:
    """列出 Trash 中所有卡片。"""
    trash_dir = _trash_root(cfg)
    if not trash_dir.exists():
        return []
    cards: list[TrashCardSummary] = []
    for md in sorted(trash_dir.rglob("*.md"), reverse=True):
        if md.name.startswith("."):
            continue
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---\n"):
            continue
        rest = text[4:]
        end = rest.find("\n---\n")
        if end == -1:
            continue
        fm_text = rest[:end]
        cards.append(TrashCardSummary(
            trash_rel_path=_rel_path(cfg.vault.root, md),
            title=_extract_fm_field(fm_text, "title", md.stem),
            previous_status=_extract_fm_field(fm_text, "previous_status", "unknown"),
            original_path=_extract_fm_field(fm_text, "original_path", str(md)),
            trashed_at=_extract_fm_field(fm_text, "trashed_at", ""),
            track=_extract_fm_field(fm_text, "track", None),
            tags=_extract_fm_list(fm_text, "tags"),
            source_title=_extract_fm_field(fm_text, "source_title", None),
        ))
    return cards


def read_trashed_card(cfg: MindForgeConfig, trash_rel_path: str) -> tuple[dict, str] | None:
    """读 Trash 中单张卡片的 (frontmatter_fields, body)。

    trash_rel_path 是相对于 vault root 的路径。
    """
    resolved = (cfg.vault.root / trash_rel_path).resolve()
    trash_root = _trash_root(cfg).resolve()
    if not resolved.is_relative_to(trash_root):
        raise TrashError("trash path 不在 Trash 目录内")
    if not resolved.exists() or not resolved.is_file():
        return None
    text = resolved.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        return None
    from .cards import read_card_frontmatter
    try:
        fm = read_card_frontmatter(resolved)
    except Exception:
        return None
    return fm, rest[end + 5:]


def restore_trashed_card(
    cfg: MindForgeConfig,
    trash_rel_path: str,
) -> RestoreResult:
    """从 Trash 恢复卡片到原路径。

    如果原路径已被占用，生成冲突安全文件名。
    """
    # trash_rel_path 是相对 vault root 的路径
    trash_path = (cfg.vault.root / trash_rel_path).resolve()
    trash_root = _trash_root(cfg).resolve()
    if not trash_path.is_relative_to(trash_root):
        raise TrashError("trash path 不在 Trash 目录内")
    if not trash_path.exists() or not trash_path.is_file():
        raise TrashError("trash 文件不存在")

    # 读 frontmatter
    text = trash_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise TrashError("trash card 缺少 frontmatter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise TrashError("trash card frontmatter 未闭合")
    fm_text = rest[:end]
    body = rest[end + 5:]

    title = _extract_fm_field(fm_text, "title", trash_path.stem)
    card_id = _extract_fm_field(fm_text, "id", str(trash_path.stem))
    previous_status = _extract_fm_field(fm_text, "previous_status", "ai_draft")
    original_rel = _extract_fm_field(fm_text, "original_path", str(trash_path))
    original_path = cfg.vault.root / original_rel

    # 清理 trash metadata
    fm_lines = [l for l in fm_text.split("\n")
                if not l.startswith("trashed_at:")
                and not l.startswith("original_path:")
                and not l.startswith("previous_status:")
                and not l.startswith("trash_reason:")]
    # 恢复 status 为 previous_status
    new_fm_lines: list[str] = []
    for line in fm_lines:
        if line.startswith("status:"):
            new_fm_lines.append(f"status: {previous_status}")
        else:
            new_fm_lines.append(line)
    fm_text_clean = "\n".join(new_fm_lines)

    # 确保目标目录存在
    original_path.parent.mkdir(parents=True, exist_ok=True)

    conflict_resolved = False
    restore_path = original_path
    if restore_path.exists():
        # 冲突安全：加时间戳后缀
        stem = original_path.stem
        restore_path = original_path.parent / f"{stem}--restored-{int(time.time())}.md"
        conflict_resolved = True

    new_text = f"---\n{fm_text_clean}\n---\n{body}"
    tmp = restore_path.with_suffix(".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(str(tmp), str(restore_path))
    trash_path.unlink()

    # 清理空目录
    _cleanup_empty_dirs(trash_root, trash_path)

    return RestoreResult(
        card_id=card_id,
        title=title,
        restored_path=_rel_path(cfg.vault.root, restore_path),
        previous_status=previous_status,
        conflict_resolved=conflict_resolved,
    )


# ------------------------------------------------------------------
# 内部 helpers
# ------------------------------------------------------------------


def _validate_card_in_vault(cfg: MindForgeConfig, card_path: Path) -> Path:
    """验证 card 在 vault cards_dir 内，防 path traversal 和重复 trash。"""
    cards_root = cfg.vault.cards_path.resolve()
    trash_root = _trash_root(cfg).resolve()
    resolved = card_path.expanduser().resolve()
    # 先检查是否在 trash 中（已 moved 文件不能重复 move）
    if resolved.is_relative_to(trash_root):
        raise TrashError("该文件已在 Trash 中，无需重复操作")
    # 再检查是否在 cards_dir 内
    if not resolved.is_relative_to(cards_root):
        raise TrashError("card path 不在当前 vault cards_dir 内，拒绝操作")
    if not resolved.exists() or not resolved.is_file():
        raise TrashError("card 文件不存在")
    return resolved


def _rel_path(root: Path, path: Path) -> str:
    """返回相对 root 的 posix 路径字符串。"""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _extract_fm_field(fm_text: str, key: str, default: str | None) -> str | None:
    """从 YAML frontmatter 文本中提取单值字段。"""
    # 简单正则，不解析完整 YAML（避免引入依赖）
    m = re.search(rf"^{key}:\s*(.+)", fm_text, re.MULTILINE)
    if m:
        val = m.group(1).strip().strip('"').strip("'")
        return val or default
    return default


def _extract_fm_list(fm_text: str, key: str) -> list[str]:
    """从 YAML frontmatter 中提取列表字段。"""
    m = re.search(rf"^{key}:\s*\[(.*?)\]", fm_text, re.MULTILINE)
    if m:
        items = m.group(1)
        return [i.strip().strip('"').strip("'") for i in items.split(",") if i.strip()]
    return []


def _cleanup_empty_dirs(root: Path, removed_path: Path) -> None:
    """清理删除文件后留下的空目录链。"""
    cur = removed_path.parent
    while cur != root and cur.exists():
        try:
            next(cur.iterdir())
            break  # 非空
        except StopIteration:
            cur.rmdir()
        cur = cur.parent


__all__ = [
    "TrashResult",
    "TrashCardSummary",
    "RestoreResult",
    "TrashError",
    "move_card_to_trash",
    "list_trashed_cards",
    "read_trashed_card",
    "restore_trashed_card",
]
