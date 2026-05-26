"""Review & Approval API schemas.

中文学习型说明：这些 schema 定义主路径中 Draft → Review → Approval 的 Web API
契约。DraftSummary 被 Library 复用展示已审批卡片的基本信息，ApprovalResponse
确保 explicit approval 语义不被破坏。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from mindforge_web.schemas.common import NextAction, SourcePathViewModel, StatusItem


class DraftSummary(BaseModel):
    id: str | None
    title: str | None
    path: str
    rel_path: str
    status: str
    track: str | None
    projects: list[str]
    tags: list[str]
    source_type: str | None
    source_id: str | None = None
    source_title: str | None
    source_path: str | None = None
    source_archive_path: str | None = None
    source_content_hash: str | None = None
    value_score: int | None
    profile: str | None = None
    provider: str | None = None
    strategy_id: str | None = None
    strategy_label: str | None = None
    strategy_note: str | None = None
    strategy_canonical_id: str | None = None
    strategy_version: str | None = None
    schema_version: str | None = None
    prompt_version: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    stage_models: dict[str, Any] = Field(default_factory=dict)
    run_id: str | None = None
    created_at: str | None = None
    approved_at: str | None = None
    updated_at: str | None = None
    source_path_view: SourcePathViewModel | None = None


class DraftsResponse(BaseModel):
    drafts: list[DraftSummary]
    scan_errors: list[StatusItem]
    empty_state: NextAction | None = None


class DraftDetailResponse(BaseModel):
    draft: DraftSummary
    frontmatter: dict[str, Any]
    body: str
    source_context: dict[str, Any]
    approval_required: bool = True


class ApproveRequest(BaseModel):
    confirm: bool
    reviewed_source: bool
    reason: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class ApprovalResponse(BaseModel):
    ok: bool
    status: str
    message: str
    card_path: str | None = None
    previous_status: str | None = None
    new_status: str | None = None
    idempotent: bool = False
    index_updated: bool = False
    index_path: str | None = None
    index_error: str | None = None
