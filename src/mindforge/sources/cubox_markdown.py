"""CuboxMarkdownAdapter — 解析 Cubox 官方 Obsidian 插件同步生成的 Markdown。

Cubox 插件支持自定义模板，所以 frontmatter 字段名因人而异；本 adapter 用一份
**容错的字段映射表**（v0.1 hard-code，未来可抽到 ``configs/sources/cubox_frontmatter_map.yaml``）。

设计要点
--------
1. **字段映射的所有 fallback 在本文件内**，下游永不感知 Cubox 的 frontmatter 形状。
2. **Highlights 解析**：识别常见 Markdown 二级标题 ``## Highlights`` / ``## 划线`` /
   ``## 笔记`` 段，按 ``> 引用`` 段为单元拆出 Highlight 列表。
3. **content_hash** 的 key_metadata 仅包含真正影响加工结果的字段（url / title /
   author），不含时间戳。

不在 v0.1 范围内
----------------
- 不去访问 Cubox API（绕过 Obsidian 插件直连 API 是 v0.2+ 的事）；
- 不重写 / 删除原始 .md 文件（``00-Inbox/`` 永远只读）。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import frontmatter

from .base import Highlight, SourceAdapter, SourceDocument, compute_content_hash

# Cubox 模板常见 frontmatter 字段名 → 标准字段
_TITLE_KEYS = ("title", "Title", "name", "标题")
_URL_KEYS = ("url", "source_url", "source", "link", "URL", "网址")
_AUTHOR_KEYS = ("author", "creator", "byline", "作者")
_TAGS_KEYS = ("tags", "tag", "标签")
_CREATED_KEYS = ("created", "created_at", "publish_time", "publishTime", "date", "发布时间")
_CAPTURED_KEYS = ("captured_at", "savedAt", "saved_at", "addedAt", "added_at", "收藏时间")

# Highlights 段标题（中英 + 常见变体）
_HIGHLIGHTS_HEADINGS = re.compile(
    r"^##\s+(highlights?|划线|笔记|高亮|notes?|annotations?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


class CuboxMarkdownAdapter(SourceAdapter):
    """把 Cubox 同步过来的 Markdown 文件解析为 SourceDocument。"""

    name = "CuboxMarkdownAdapter"
    source_type = "cubox_markdown"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        """仅匹配 .md 后缀且含 Cubox 特征 frontmatter 或 highlights 段。

        普通本地 markdown 不该被标成 cubox_markdown；这里不做全量 YAML 解析，
        只做轻量字符串探测：检查文件前 2KB 是否含 Cubox 特有 frontmatter key
        或 highlights 标题。
        """
        if not path.lower().endswith(".md"):
            return False
        p = Path(path)
        if not p.exists():
            return False
        try:
            head = p.read_text(encoding="utf-8")[:2048]
        except (OSError, UnicodeDecodeError):
            return False
        # Cubox 特征 frontmatter key：URL / source / link / 网址
        cubox_keys = ("url:", "source_url:", "source:", "link:", "URL:", "网址:")
        if any(k in head for k in cubox_keys):
            return True
        # Cubox highlights 段标题
        if _HIGHLIGHTS_HEADINGS.search(head):
            return True
        return False

    def load(self, path: str) -> SourceDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Cubox Markdown 文件不存在：{p}。请检查 inbox 路径。")

        post = frontmatter.load(str(p))
        meta: dict = dict(post.metadata or {})
        body = post.content or ""

        title = _pick_str(meta, _TITLE_KEYS) or p.stem
        author = _pick_str(meta, _AUTHOR_KEYS)
        source_url = _pick_str(meta, _URL_KEYS)
        tags = _pick_tags(meta, _TAGS_KEYS)
        created_at = _pick_dt(meta, _CREATED_KEYS)
        captured_at = _pick_dt(meta, _CAPTURED_KEYS)

        highlights = _extract_highlights(body)

        source_id = "sha1:" + hashlib.sha1(path.encode("utf-8")).hexdigest()

        # hash 关键字段：标题 / URL / 作者会影响 LLM 输出
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
            highlights=highlights,
            raw_text=body,
            metadata={"frontmatter": meta},
            content_hash=content_hash,
        )


# ---------------------------------------------------------------------------
# frontmatter 字段提取辅助（容错）
# ---------------------------------------------------------------------------


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
    for k in keys:
        if k in meta and meta[k] is not None:
            v = meta[k]
            if isinstance(v, datetime):
                return v
            if isinstance(v, str):
                try:
                    return datetime.fromisoformat(v.replace("Z", "+00:00"))
                except ValueError:
                    continue
    return None


# ---------------------------------------------------------------------------
# Highlights 解析
# ---------------------------------------------------------------------------


def _extract_highlights(body: str) -> list[Highlight]:
    """从正文中拉出 Highlights 段，按"引用块 + 可选注释"切成 Highlight 列表。

    简化策略（v0.1）：
    - 找到第一个匹配的 highlights 标题；
    - 从此处往后到下一个 ``##`` 标题之前的所有内容视为 highlights 区；
    - 该区按"以 ``>`` 起始的连续段落"切片，每段为一个 Highlight；
    - 紧随 ``>`` 段后的非 ``>`` 文本若存在，归到该 Highlight 的 ``note``。

    不追求完美：能覆盖 80% 常见 Cubox 模板即可，剩余靠人工编辑。
    """
    m = _HIGHLIGHTS_HEADINGS.search(body)
    if not m:
        return []

    region = body[m.end():]
    # 截到下一个 ## 标题前
    next_h = re.search(r"^##\s+", region, re.MULTILINE)
    if next_h:
        region = region[: next_h.start()]

    highlights: list[Highlight] = []
    current_quote: list[str] = []
    pending_note: list[str] = []
    # 状态机：IDLE / IN_QUOTE / AFTER_QUOTE_BLANK / IN_NOTE
    state = "IDLE"

    def flush() -> None:
        nonlocal state
        if not current_quote:
            current_quote.clear()
            pending_note.clear()
            state = "IDLE"
            return
        text = "\n".join(line.lstrip("> ").rstrip() for line in current_quote).strip()
        note = "\n".join(pending_note).strip() or None
        if text:
            highlights.append(Highlight(text=text, note=note))
        current_quote.clear()
        pending_note.clear()
        state = "IDLE"

    for line in region.splitlines():
        if line.startswith(">"):
            # 遇到新 quote：若在 AFTER_QUOTE_BLANK 或 IN_NOTE，先 flush 上一条
            if state in ("AFTER_QUOTE_BLANK", "IN_NOTE"):
                flush()
            current_quote.append(line)
            state = "IN_QUOTE"
        elif line.strip() == "":
            if state == "IN_QUOTE":
                state = "AFTER_QUOTE_BLANK"
            elif state == "IN_NOTE":
                flush()
            # IDLE / AFTER_QUOTE_BLANK 状态下的空行忽略
        else:
            # 非空、非 quote 文本行
            if state in ("IN_QUOTE", "AFTER_QUOTE_BLANK", "IN_NOTE"):
                pending_note.append(line.strip())
                state = "IN_NOTE"
            # IDLE 状态下的杂散文本忽略

    flush()
    return highlights


__all__ = ["CuboxMarkdownAdapter"]
