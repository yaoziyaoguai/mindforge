"""WebClipMarkdownAdapter — 解析 Web Clipper / MarkDownload 风格的网页 Markdown。

为什么是 SourceAdapter，而不是写死在 processor？
================================================
MindForge 的核心抽象是"adapter 把异构输入翻译成统一 SourceDocument"。
WebClip 工具（Obsidian Web Clipper / MarkDownload / SingleFile to Markdown）
的格式跟 Cubox 略有差异：

- frontmatter 字段名常见：``title`` / ``source`` / ``url`` / ``author``
  / ``created`` / ``tags``；
- 正文可能以一级 H1 标题开头；
- 没有 highlights 段（不同于 Cubox）。

只要在 adapter 内消化掉这些差异，下游 Triager / Distiller / Linker / Writer
可以一行都不改 —— 这就是抽象的意义。如果直接在 processor 里 ``if
source_type == "webclip"`` 就破坏了 v0.1 的契约（详见 docs/MINDFORGE_PROTOCOL.md）。

边界
----
- **不访问网络**：只读本地 .md，绝不重新抓取页面；
- **不重写源文件**：``00-Inbox/WebClips/`` 永远只读；
- frontmatter 缺失也允许（整文件视为正文，title 退化为文件名 / 首行 H1）。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import frontmatter

from .base import SourceAdapter, SourceDocument, compute_content_hash

# 常见 webclip 工具的 frontmatter 别名 → 标准字段
_TITLE_KEYS = ("title", "Title", "name", "标题")
_URL_KEYS = ("source", "source_url", "url", "URL", "page_url", "原文链接")
_AUTHOR_KEYS = ("author", "byline", "creator", "作者")
_TAGS_KEYS = ("tags", "tag", "标签", "categories")
_CREATED_KEYS = ("created", "created_at", "date", "publish_time", "publishTime", "发布时间")
_CAPTURED_KEYS = ("captured_at", "savedAt", "saved_at", "clipped_at", "clipDate")

_FIRST_H1 = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)


class WebClipMarkdownAdapter(SourceAdapter):
    """把 ``00-Inbox/WebClips/*.md`` 解析为统一的 SourceDocument。"""

    name = "WebClipMarkdownAdapter"
    source_type = "webclip_markdown"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        return path.lower().endswith(".md")

    def load(self, path: str) -> SourceDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"WebClipMarkdownAdapter: 文件不存在 {p}")

        post = frontmatter.load(str(p))
        meta: dict = dict(post.metadata or {})
        body = post.content or ""

        # title 优先级：frontmatter > 正文首个 H1 > 文件名
        title = _pick_str(meta, _TITLE_KEYS)
        if not title:
            m = _FIRST_H1.search(body)
            if m:
                title = m.group(1).strip()
        if not title:
            title = p.stem

        author = _pick_str(meta, _AUTHOR_KEYS)
        source_url = _pick_str(meta, _URL_KEYS)
        tags = _pick_tags(meta, _TAGS_KEYS)
        created_at = _pick_dt(meta, _CREATED_KEYS)
        captured_at = _pick_dt(meta, _CAPTURED_KEYS)

        source_id = "sha1:" + hashlib.sha1(path.encode("utf-8")).hexdigest()

        # 仅放真正影响 LLM 输出的元信息，避免每次时间戳变化都让 hash 失效
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


def _pick_str(meta: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if k in meta and meta[k] is not None:
            s = str(meta[k]).strip()
            if s:
                return s
    return None


def _pick_tags(meta: dict, keys: tuple[str, ...]) -> list[str]:
    for k in keys:
        if k in meta and meta[k] is not None:
            v = meta[k]
            if isinstance(v, str):
                return [t.strip().lstrip("#") for t in v.split(",") if t.strip()]
            if isinstance(v, list):
                return [str(t).strip().lstrip("#") for t in v if str(t).strip()]
    return []


def _pick_dt(meta: dict, keys: tuple[str, ...]) -> datetime | None:
    from datetime import date as _date

    for k in keys:
        if k in meta and meta[k] is not None:
            v = meta[k]
            if isinstance(v, datetime):
                return v
            # PyYAML 把 ``2025-04-01`` 解析为 datetime.date；统一升级到 datetime
            if isinstance(v, _date):
                return datetime(v.year, v.month, v.day)
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    continue
    return None


__all__ = ["WebClipMarkdownAdapter"]
