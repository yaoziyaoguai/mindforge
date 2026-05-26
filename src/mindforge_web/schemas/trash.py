"""Trash / Recycle Bin schemas.

中文学习型说明：这些 schema 涵盖回收站的卡片列表、详情、操作请求/响应
等 Trash 页面的核心契约。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TrashCardResponse(BaseModel):
    trash_rel_path: str
    title: str
    previous_status: str
    original_path: str
    trashed_at: str
    track: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_title: str | None = None


class TrashListResponse(BaseModel):
    trashed_cards: list[TrashCardResponse]
    trash_dir: str


class TrashActionRequest(BaseModel):
    trash_rel_path: str = ""
    confirm: bool = False


class TrashDetailResponse(BaseModel):
    card: TrashCardResponse
    frontmatter: dict[str, Any] = Field(default_factory=dict)
    body: str | None = None


class TrashActionResponse(BaseModel):
    ok: bool
    action: str  # "moved_to_trash" | "restored"
    message: str
    card_id: str | None = None
    previous_status: str | None = None
    restored_path: str | None = None
    conflict_resolved: bool = False
