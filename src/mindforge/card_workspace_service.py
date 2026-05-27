"""Knowledge Card workspace write service.

中文学习型说明：Web 工作台允许用户编辑 Knowledge Card 正文，但这个能力仍属
核心业务边界，而不是前端或 Router 直接写文件。Service 只替换 Markdown body，
保留 YAML frontmatter（status/source/strategy/provenance），并在
``human_approved`` 卡片保存后刷新本地 BM25。它不读取 source raw text、不读
``.env``、不调用 provider，也不自动 approve。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .cards import CardLoadValueError, read_card_frontmatter
from .config import MindForgeConfig
from .lexical_index import rebuild_index_for_config


@dataclass(frozen=True)
class CardBodyUpdateResult:
    card_path: Path
    status: str
    index_updated: bool
    index_path: Path | None = None
    index_error: str | None = None


class CardWorkspaceError(ValueError):
    """卡片工作台写入失败；message 可安全返回给 Web。"""


def update_card_body(
    cfg: MindForgeConfig,
    card_path: Path,
    body: str,
    *,
    expected_status: str | None = None,
    rebuild_recall_for_approved: bool = True,
) -> CardBodyUpdateResult:
    """替换单张 Knowledge Card 的正文，保留 frontmatter 与状态语义。

    中文学习型说明：Web draft edit 和 library edit 的差别只在状态边界：
    draft 保存后仍是 ``ai_draft``，approved 保存后仍是 ``human_approved``。
    这就是为什么这里显式校验 ``expected_status``，而不是让 UI 传什么就写什么。
    """

    resolved = _resolve_within_cards_dir(cfg, card_path)
    frontmatter = _frontmatter_text(resolved)
    try:
        fields = read_card_frontmatter(resolved)
    except (CardLoadValueError, OSError) as exc:
        raise CardWorkspaceError(f"card frontmatter 无法读取：{type(exc).__name__}: {exc}") from exc

    status = fields.get("status")
    if not isinstance(status, str) or not status:
        raise CardWorkspaceError("card frontmatter 缺 status 字段")
    if expected_status is not None and status != expected_status:
        raise CardWorkspaceError(f"card status 是 {status}，不能作为 {expected_status} 保存")

    normalized_body = body if body.endswith("\n") else f"{body}\n"
    _atomic_write(resolved, f"---\n{frontmatter}\n---\n{normalized_body}")

    index_updated = False
    index_path: Path | None = None
    index_error: str | None = None
    if status == "human_approved" and rebuild_recall_for_approved:
        try:
            rebuilt = rebuild_index_for_config(cfg)
            index_updated = True
            index_path = rebuilt.path
        except Exception as exc:  # pragma: no cover - Web 用结构化错误兜底展示
            index_error = f"{type(exc).__name__}: {exc}"
    return CardBodyUpdateResult(
        card_path=resolved,
        status=status,
        index_updated=index_updated,
        index_path=index_path,
        index_error=index_error,
    )


def _resolve_within_cards_dir(cfg: MindForgeConfig, card_path: Path) -> Path:
    root = cfg.vault.cards_path.resolve()
    resolved = card_path.expanduser().resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise CardWorkspaceError("card path 不在当前 vault cards_dir 内") from exc
    if not resolved.exists() or not resolved.is_file():
        raise CardWorkspaceError("card 文件不存在")
    return resolved


def _frontmatter_text(card_path: Path) -> str:
    raw = card_path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise CardWorkspaceError("card 缺少 frontmatter")
    rest = raw[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise CardWorkspaceError("card frontmatter 未闭合")
    return rest[:end]


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def link_cards(
    cfg: MindForgeConfig,
    card1_ref: str,
    card2_ref: str,
    reason: str = "see_also",
) -> tuple[bool, str]:
    """手动关联两张卡片 — 在双方 frontmatter 中写入 manual_links 条目。

    返回 (ok, message)。
    """
    from datetime import datetime, timezone

    from .cards import iter_cards

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards_by_ref: dict[str, Path] = {}
    for card in scan.cards:
        if card.id:
            cards_by_ref[card.id] = card.path
        cards_by_ref[card.rel_path] = card.path
        cards_by_ref[str(card.path)] = card.path

    path1 = cards_by_ref.get(card1_ref)
    path2 = cards_by_ref.get(card2_ref)
    if path1 is None:
        return False, f"card not found: {card1_ref}"
    if path2 is None:
        return False, f"card not found: {card2_ref}"
    if path1 == path2:
        return False, "cannot link a card to itself"

    ts = datetime.now(timezone.utc).isoformat()
    try:
        _add_manual_link_to_frontmatter(path1, target_ref=card2_ref, reason=reason, created_at=ts)
        _add_manual_link_to_frontmatter(path2, target_ref=card1_ref, reason=reason, created_at=ts)
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def _add_manual_link_to_frontmatter(
    card_path: Path,
    *,
    target_ref: str,
    reason: str,
    created_at: str,
) -> None:
    """在卡片 frontmatter 的 manual_links 列表中添加一条关联记录。"""
    import yaml

    raw = card_path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise CardWorkspaceError("card 缺少 frontmatter")
    rest = raw[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise CardWorkspaceError("card frontmatter 未闭合")

    fm_text = rest[:end]
    body = rest[end + 5:]

    try:
        fm = yaml.safe_load(fm_text)
    except Exception as exc:
        raise CardWorkspaceError(f"frontmatter YAML 解析失败: {exc}") from exc

    if not isinstance(fm, dict):
        fm = {}

    existing: list[dict] = fm.get("manual_links", [])
    if not isinstance(existing, list):
        existing = []
    # 去重 — 避免重复写入同一个 link
    for entry in existing:
        if isinstance(entry, dict) and entry.get("target") == target_ref:
            return  # already linked
    existing.append({"target": target_ref, "reason": reason, "created_at": created_at})
    fm["manual_links"] = existing

    new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False).rstrip("\n")
    new_body = body if body.endswith("\n") else f"{body}\n"
    _atomic_write(card_path, f"---\n{new_fm}\n---\n{new_body}")


__all__ = ["CardBodyUpdateResult", "CardWorkspaceError", "bulk_update_cards", "link_cards", "update_card_body"]


def bulk_update_cards(
    cfg: MindForgeConfig,
    card_refs: list[str],
    *,
    set_tags: list[str] | None = None,
    set_track: str | None = None,
) -> tuple[int, list[str]]:
    """批量更新卡片的 frontmatter tags / track 字段，保留 body 不变。

    返回 (updated_count, errors)。
    """
    from .cards import iter_cards

    if set_tags is None and set_track is None:
        return 0, ["no fields to update"]

    scan = iter_cards(cfg.vault.root, cfg.vault.cards_dir)
    cards_by_ref: dict[str, Path] = {}
    for card in scan.cards:
        if card.id:
            cards_by_ref[card.id] = card.path
        cards_by_ref[card.rel_path] = card.path
        cards_by_ref[str(card.path)] = card.path

    updated = 0
    errors: list[str] = []

    for ref in card_refs:
        card_path = cards_by_ref.get(ref)
        if card_path is None:
            errors.append(f"card not found: {ref}")
            continue
        try:
            _update_frontmatter_fields(card_path, set_tags=set_tags, set_track=set_track)
            updated += 1
        except Exception as exc:
            errors.append(f"{ref}: {exc}")

    return updated, errors


def _update_frontmatter_fields(
    card_path: Path,
    *,
    set_tags: list[str] | None = None,
    set_track: str | None = None,
) -> None:
    """修改 frontmatter 中的 tags 和/或 track 字段，保留其余字段和 body 不变。"""
    import yaml

    raw = card_path.read_text(encoding="utf-8")
    if not raw.startswith("---\n"):
        raise CardWorkspaceError("card 缺少 frontmatter")
    rest = raw[4:]
    end = rest.find("\n---\n")
    if end == -1:
        raise CardWorkspaceError("card frontmatter 未闭合")

    fm_text = rest[:end]
    body = rest[end + 5:]  # skip "\n---\n"

    try:
        fm = yaml.safe_load(fm_text)
    except Exception as exc:
        raise CardWorkspaceError(f"frontmatter YAML 解析失败: {exc}") from exc

    if not isinstance(fm, dict):
        fm = {}

    if set_tags is not None:
        fm["tags"] = set_tags
    if set_track is not None:
        fm["track"] = set_track

    new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False).rstrip("\n")
    new_body = body if body.endswith("\n") else f"{body}\n"
    _atomic_write(card_path, f"---\n{new_fm}\n---\n{new_body}")
