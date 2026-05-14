"""v0.2 PlainMarkdownAdapter — 普通 Markdown 笔记的 v0.2 adapter wrapper。

与 v0.1 ``plain_markdown.PlainMarkdownAdapter`` 的关系
--------------------------------------------------------

- v0.1 adapter 是现有主链路使用的实现（``load() -> SourceDocument``）。
- v0.2 adapter 是同一行为的 v0.2 接口包装（``load() -> AdapterResult``）。
- 两者输出等价的 SourceDocument；v0.2 版本将 skip/fail 路径提升为
  AdapterResult 三态，不再通过 bare exception 表达。
- v0.1 characterization tests 确保行为不回退；本 adapter 的测试确保
  v0.2 接口正确包装了等价行为。

RFC_0001 §5.5 要求 PlainMarkdownAdapter 行为保持不变。
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import frontmatter

from mindforge.sources.adapter_result import AdapterResult, SkipReason
from mindforge.sources.base import SourceDocument, compute_content_hash
from mindforge.sources.source_adapter import SourceAdapter


class PlainMarkdownAdapter(SourceAdapter):
    """把本地 .md / .markdown 文件解析为 SourceDocument，通过 AdapterResult 返回。

    v0.2 三态契约：
    - 文件不存在 → AdapterResult.failed
    - 非 Markdown 后缀 → AdapterResult.skipped
    - 合法 Markdown → AdapterResult.loaded
    """

    name = "PlainMarkdownAdapter"
    source_type = "plain_markdown"

    # ------------------------------------------------------------------
    # can_handle：按 .md / .markdown 后缀识别（大小写不敏感）
    # ------------------------------------------------------------------

    def can_handle(self, path: str) -> bool:
        suffix = Path(path).suffix.lower()
        return suffix in (".md", ".markdown")

    # ------------------------------------------------------------------
    # load：三态返回 AdapterResult
    # ------------------------------------------------------------------

    def load(self, path: str) -> AdapterResult:
        p = Path(path)

        # -- 文件不存在 → failed ------------------------------------------
        if not p.exists():
            return AdapterResult(
                status="failed",
                error_message=f"FileNotFoundError: {p}",
            )

        # -- 不支持的格式 → skipped ---------------------------------------
        if not self.can_handle(path):
            return AdapterResult(
                status="skipped",
                skip_reason=SkipReason.UNSUPPORTED_FORMAT,
            )

        # -- 合法 Markdown → loaded ---------------------------------------
        try:
            doc = self._build_document(p)
            return AdapterResult(status="loaded", document=doc)
        except Exception as exc:
            return AdapterResult(
                status="failed",
                error_message=f"{type(exc).__name__}: {exc}",
            )

    # ------------------------------------------------------------------
    # 内部：构造 SourceDocument（逻辑与 v0.1 PlainMarkdownAdapter 等价）
    # ------------------------------------------------------------------

    def _build_document(self, p: Path) -> SourceDocument:
        """解析 Markdown 文件并构造 SourceDocument。

        逻辑与 v0.1 ``plain_markdown.PlainMarkdownAdapter.load()`` 等价，
        确保两个 adapter 对相同输入产生相同 SourceDocument。
        """
        post = frontmatter.load(str(p))
        meta: dict = dict(post.metadata or {})
        body: str = post.content or ""

        title = _coerce_str(meta.get("title")) or p.stem
        author = _coerce_str(meta.get("author"))
        source_url = _coerce_str(meta.get("source_url") or meta.get("url"))
        tags = _coerce_tags(meta.get("tags"))
        created_at = _coerce_dt(meta.get("created_at") or meta.get("created"))
        captured_at = _coerce_dt(meta.get("captured_at"))

        source_id = "sha1:" + hashlib.sha1(str(p).encode("utf-8")).hexdigest()

        key_meta = {
            "title": title,
            "source_url": source_url,
            "author": author,
        }
        content_hash = compute_content_hash(body, key_meta)

        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=str(p),
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


# ---------------------------------------------------------------------------
# 辅助函数（与 v0.1 plain_markdown.py 完全一致）
# ---------------------------------------------------------------------------


def _coerce_str(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _coerce_tags(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
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
