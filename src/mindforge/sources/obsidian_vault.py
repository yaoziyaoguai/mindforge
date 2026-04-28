"""ObsidianVaultSourceAdapter — 只读接入 Obsidian vault Markdown。

学习要点：
- Obsidian 在 v0.5 是个人知识语境 Source，因此它必须进入 SourceAdapter 体系；
- binding 默认只读，因为真实 vault 是用户维护的长期知识资产，不是临时工作目录；
- staging/review 与正式 notes 必须隔离，避免 AI 草稿直接污染人的知识库；
- runtime state、cache、index、log 不能进入 Obsidian notes，它们是可重建的机器派生层；
- 这不是 Obsidian plugin，也不是 RAG：本 adapter 只做本地 Markdown 解析。
"""

from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import frontmatter

from .base import SourceAdapter, SourceDocument, compute_content_hash

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|[^\]]+)?\]\]")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_INLINE_TAG_RE = re.compile(r"(?<!\w)#([A-Za-z0-9_/-]+)")


class ObsidianVaultSourceAdapter(SourceAdapter):
    """把 Obsidian Markdown note 解析为统一的 SourceDocument。

    adapter 不写文件、不读 `.env`、不联网、不调用 LLM。调用方负责决定扫描范围；
    本类只把单个 Markdown note 翻译成 SourceDocument。
    """

    name = "obsidian_vault"
    source_type = "obsidian_note"  # type: ignore[assignment]

    def __init__(self, vault_root: str | Path | None = None) -> None:
        self.vault_root = Path(vault_root).expanduser().resolve() if vault_root else None

    def can_handle(self, path: str) -> bool:
        return path.lower().endswith(".md")

    def load(self, path: str) -> SourceDocument:
        p = Path(path).expanduser()
        if not p.exists():
            raise FileNotFoundError(f"Obsidian note 不存在：{p}。请检查 vault 路径。")
        if not p.is_file() or p.suffix.lower() != ".md":
            raise ValueError(f"Obsidian adapter 只读取 Markdown 文件：{p}")

        post = frontmatter.load(str(p))
        meta: dict[str, Any] = dict(post.metadata or {})
        body = post.content or ""
        rel_path = _relative_path(p, self.vault_root)

        title = _pick_title(meta, body, p)
        tags = sorted(set(_coerce_tags(meta.get("tags")) + _inline_tags(body)))
        aliases = _coerce_list(meta.get("aliases") or meta.get("alias"))
        created_at = _coerce_dt(meta.get("created") or meta.get("created_at"))
        updated_at = _coerce_dt(meta.get("updated") or meta.get("updated_at") or meta.get("modified"))
        wikilinks = _wikilinks(body)
        headings = _headings(body)

        key_meta = {
            "title": title,
            "relative_path": rel_path,
            "tags": tags,
            "aliases": aliases,
            "wikilinks": wikilinks,
            "headings": [h["text"] for h in headings],
        }
        content_hash = compute_content_hash(body, key_meta)
        source_id = "sha1:" + hashlib.sha1(rel_path.encode("utf-8")).hexdigest()

        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=rel_path,
            title=title,
            created_at=created_at,
            tags=tags,
            highlights=[],
            raw_text=body,
            metadata={
                "frontmatter": meta,
                "aliases": aliases,
                "updated_at": updated_at.isoformat() if updated_at else None,
                "wikilinks": wikilinks,
                "headings": headings,
                "relative_path": rel_path,
            },
            content_hash=content_hash,
            adapter_name=self.name,
        )


def _relative_path(path: Path, vault_root: Path | None) -> str:
    resolved = path.expanduser().resolve()
    if vault_root is None:
        return str(resolved)
    try:
        return resolved.relative_to(vault_root).as_posix()
    except ValueError:
        return str(resolved)


def _pick_title(meta: dict[str, Any], body: str, path: Path) -> str:
    for key in ("title", "name", "aliases"):
        value = meta.get(key)
        if isinstance(value, list) and value:
            text = str(value[0]).strip()
        else:
            text = str(value).strip() if value is not None else ""
        if text:
            return text
    match = _HEADING_RE.search(body)
    if match:
        return match.group(2).strip()
    return path.stem


def _coerce_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,\s]+", value)
        return [p.strip().lstrip("#") for p in parts if p.strip()]
    if isinstance(value, list):
        return [str(item).strip().lstrip("#") for item in value if str(item).strip()]
    return []


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _coerce_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _inline_tags(body: str) -> list[str]:
    tags: list[str] = []
    for line in body.splitlines():
        if line.lstrip().startswith("# "):
            continue
        tags.extend(m.group(1).strip("/") for m in _INLINE_TAG_RE.finditer(line))
    return [t for t in tags if t]


def _wikilinks(body: str) -> list[str]:
    return sorted({m.group(1).strip() for m in _WIKILINK_RE.finditer(body) if m.group(1).strip()})


def _headings(body: str) -> list[dict[str, Any]]:
    return [
        {"level": len(match.group(1)), "text": match.group(2).strip()}
        for match in _HEADING_RE.finditer(body)
    ]


__all__ = ["ObsidianVaultSourceAdapter"]
