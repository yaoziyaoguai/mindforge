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


__all__ = ["CardBodyUpdateResult", "CardWorkspaceError", "update_card_body"]
