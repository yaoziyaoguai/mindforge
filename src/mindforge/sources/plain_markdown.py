"""PlainMarkdownAdapter — 普通 Markdown 笔记的 adapter。

适用场景
--------
- 你自己在 Obsidian 里手写的笔记；
- 任何不是 Cubox / WebClip 工具生成的、只有正文 + 可选 frontmatter 的 .md。

边界
----
- frontmatter（YAML）若存在则解析；不存在也允许，整文件视为正文。
- highlights 留空（v0.1 不解析 ``==高亮==`` 语法）。
- metadata 仅放 ``frontmatter`` 原始字典，不做字段映射。

后续 ``CuboxMarkdownAdapter`` 与本类的差异主要是：Cubox 有自己的
frontmatter 字段约定（标题、URL、捕获时间、tags 等），需要做一次字段映射
并解析 ``## Highlights`` 段。
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import frontmatter

from .base import SourceAdapter, SourceDocument, compute_content_hash


class PlainMarkdownAdapter(SourceAdapter):
    """把 ``00-Inbox/ManualNotes/*.md`` 解析为统一的 SourceDocument。"""

    name = "PlainMarkdownAdapter"
    source_type = "plain_markdown"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        # 仅按后缀判断，子目录派发由 Scanner / registry 负责
        return path.lower().endswith(".md")

    def load(self, path: str) -> SourceDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"PlainMarkdownAdapter: 文件不存在 {p}")

        post = frontmatter.load(str(p))
        meta: dict = dict(post.metadata or {})
        body = post.content or ""

        title = _coerce_str(meta.get("title")) or p.stem
        author = _coerce_str(meta.get("author"))
        source_url = _coerce_str(meta.get("source_url") or meta.get("url"))
        tags = _coerce_tags(meta.get("tags"))
        created_at = _coerce_dt(meta.get("created_at") or meta.get("created"))
        captured_at = _coerce_dt(meta.get("captured_at"))

        # source_id 用 sha1(source_path) 保证稳定且短
        source_id = "sha1:" + hashlib.sha1(path.encode("utf-8")).hexdigest()

        # 仅把会影响加工结果的元信息纳入 hash，避免每次时间戳变都失效
        key_meta = {
            "title": title,
            "source_url": source_url,
            "author": author,
        }
        content_hash = compute_content_hash(body, key_meta)

        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=path,
            title=title,
            author=author,
            source_url=source_url,
            created_at=created_at,
            captured_at=captured_at,
            tags=tags,
            highlights=[],
            raw_text=body,
            metadata={"frontmatter": meta},
            content_hash=content_hash,
        )


def _coerce_str(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _coerce_tags(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        # 支持 "a, b, c" 这种字符串形式
        return [t.strip() for t in v.split(",") if t.strip()]
    if isinstance(v, list):
        return [str(t).strip() for t in v if str(t).strip()]
    return []


def _coerce_dt(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            return None
    return None


__all__ = ["PlainMarkdownAdapter"]
