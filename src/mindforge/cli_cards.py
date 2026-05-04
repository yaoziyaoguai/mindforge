"""CLI card rendering helpers.

中文学习型说明：这些 helper 只服务 CLI adapter 的安全输出：把
``CardSummary`` 压成 frontmatter 白名单 dict、格式化日期、hash query、
过滤 telemetry 字段、写 CLI JSON 文件。它们不读卡片正文、不碰 source raw
text、不属于 domain/service 层，因此不放进 ``utils`` 或 ``common``。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

import typer

from .cli_runtime import console


def card_to_safe_dict(c) -> dict:  # type: ignore[no-untyped-def]
    return {
        "id": c.id,
        "title": c.title,
        "path": c.rel_path,
        "status": c.status,
        "track": c.track,
        "projects": list(c.projects),
        "tags": list(c.tags),
        "source_type": c.source_type,
        "source_url": c.source_url,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "reviewed_at": c.reviewed_at.isoformat() if c.reviewed_at else None,
        "review_after": c.review_after.isoformat() if c.review_after else None,
        "review_count": c.review_count,
        "last_review_result": c.last_review_result,
        "value_score": c.value_score,
    }


def safe_date(dt) -> str:  # type: ignore[no-untyped-def]
    if dt is None:
        return "-"
    return dt.date().isoformat()


def hash_keyword(kw: str | None) -> tuple[bool, str]:
    if not kw:
        return False, ""
    return True, hashlib.sha256(kw.encode("utf-8")).hexdigest()[:8]


def filters_dict(**kwargs: object) -> dict[str, object]:
    return {k: v for k, v in kwargs.items() if v not in (None, (), [])}


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except ValueError as e:
        console.print(f"[red]日期解析失败：{s!r}: {e}[/red]")
        raise typer.Exit(code=2) from e


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
