"""ChatExportAdapter — 解析 ChatGPT / Claude / Copilot 等 AI 对话导出的 Markdown。

为什么是独立 adapter？
======================
对话有"角色 + turn"这种结构性元信息（user / assistant / system），如果不在
adapter 层解析出来，下游 LLM 加工就只能把整个对话当成"一坨文本"。但这些
元信息**不**应该污染 SourceDocument 主结构 —— 它们走 ``metadata['turns']``
（统计字段，比如 turn_count / role_counts），保持 ``raw_text`` 仍是统一
markdown，让下游加工模块"无感知"。

为什么 raw_text 仍然只是 markdown？
-----------------------------------
v0.1 的契约：**所有 source_type 共享同一个 raw_text 形状**。Triager/Distiller
不应分支 ``if source_type == "chat_export": ...``。对话格式的细节由 adapter
吃掉，下游永远看到统一的 markdown。

安全
----
ChatExport 经常包含敏感内容（API key、私人项目名、客户数据）。我们的安全
策略不是在 adapter 层做"内容脱敏推断"（误判风险大），而是：

1. **scan/process 命令的字段白名单**：runs/*.jsonl 与 telemetry.jsonl 只记录
   元数据（source_id / source_path / content_hash 等），永远不写 raw_text；
2. ``mindforge approve`` 是显式人审闸门：AI 卡片默认 ai_draft，进入长期记忆
   前必须人工过目；
3. 用户应**自行**在 capture 阶段不把含敏感字段的对话拖进 inbox。

支持的 role 检测启发式（按优先级）
----------------------------------
1. 二级标题：``## User`` / ``## Assistant`` / ``## ChatGPT`` / ``## Claude``
   / ``## Copilot`` / ``## System``（中英 + 大小写不敏感）；
2. 加粗角色行：``**user:**`` / ``**assistant**：``；
3. 全部识别失败 → 把整个 body 当作 plain chat text，``turn_count=0``，
   不报错（"识别不了 role 也不要失败" 的硬约束）。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

import frontmatter

from .base import SourceAdapter, SourceDocument, compute_content_hash

_TITLE_KEYS = ("title", "Title", "name", "subject", "标题")
_URL_KEYS = ("source", "source_url", "url", "URL")
_AUTHOR_KEYS = ("author", "model", "assistant", "作者")
_TAGS_KEYS = ("tags", "tag", "标签")
_CREATED_KEYS = ("created", "created_at", "date", "exported_at", "导出时间")

# role 同义词 → 标准角色
_ROLE_ALIASES: dict[str, str] = {
    "user": "user",
    "you": "user",
    "human": "user",
    "me": "user",
    "用户": "user",
    "assistant": "assistant",
    "chatgpt": "assistant",
    "gpt": "assistant",
    "claude": "assistant",
    "copilot": "assistant",
    "ai": "assistant",
    "助手": "assistant",
    "system": "system",
    "系统": "system",
}

# `## User` / `## Assistant` 等
_HEADING_ROLE = re.compile(
    r"^##\s+([A-Za-z\u4e00-\u9fff]+)\s*$",
    re.MULTILINE,
)
# 加粗角色行：``**Name**:`` / ``**Name**：`` / ``**Name:**`` / ``**Name：**``
# 冒号既可以在 ``**`` 内也可以在外（不同导出工具风格不同）。
_BOLD_ROLE = re.compile(
    r"^\*\*\s*([A-Za-z\u4e00-\u9fff]+)\s*[:：]?\s*\*\*\s*[:：]?\s*$",
    re.MULTILINE,
)


class ChatExportAdapter(SourceAdapter):
    """把 ``00-Inbox/ChatExports/*.md`` 解析为 SourceDocument。"""

    name = "ChatExportAdapter"
    source_type = "chat_export"  # type: ignore[assignment]

    def can_handle(self, path: str) -> bool:
        return path.lower().endswith(".md")

    def load(self, path: str) -> SourceDocument:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"ChatExportAdapter: 文件不存在 {p}")

        post = frontmatter.load(str(p))
        meta: dict = dict(post.metadata or {})
        body = post.content or ""

        title = _pick_str(meta, _TITLE_KEYS) or p.stem
        author = _pick_str(meta, _AUTHOR_KEYS)
        source_url = _pick_str(meta, _URL_KEYS)
        tags = _pick_tags(meta, _TAGS_KEYS)
        created_at = _pick_dt(meta, _CREATED_KEYS)

        # role 检测仅产出统计元信息；正文不被改写。
        role_counts = _count_roles(body)
        turn_count = sum(role_counts.values())

        source_id = "sha1:" + hashlib.sha1(path.encode("utf-8")).hexdigest()
        key_meta = {
            "title": title,
            "source_url": source_url,
            "turn_count": turn_count,
        }
        content_hash = compute_content_hash(body, key_meta)

        chat_meta: dict = {
            "frontmatter": meta,
            "turn_count": turn_count,
            "role_counts": role_counts,
            "role_detection": "ok" if turn_count > 0 else "degraded_plain_text",
        }

        return SourceDocument(
            source_id=source_id,
            source_type=self.source_type,
            source_path=path,
            title=title,
            author=author,
            source_url=source_url,
            created_at=created_at,
            captured_at=None,
            tags=tags,
            highlights=[],
            raw_text=body,
            metadata=chat_meta,
            content_hash=content_hash,
        )


# ---------------------------------------------------------------------------
# role 检测
# ---------------------------------------------------------------------------


def _count_roles(body: str) -> dict[str, int]:
    """返回 ``{"user": n, "assistant": m, "system": k}``，缺角色不报错。"""
    counts: dict[str, int] = {"user": 0, "assistant": 0, "system": 0}
    for pattern in (_HEADING_ROLE, _BOLD_ROLE):
        for m in pattern.finditer(body):
            tag = m.group(1).strip().lower()
            std = _ROLE_ALIASES.get(tag)
            if std:
                counts[std] += 1
    return counts


# ---------------------------------------------------------------------------
# frontmatter 取值辅助（与 webclip / cubox 一致的最小集）
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


__all__ = ["ChatExportAdapter"]
