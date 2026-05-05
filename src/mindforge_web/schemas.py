"""Pydantic schemas for MindForge Local Console API.

中文学习型说明：这些 schema 是 Web 边界的公开契约。它们只描述可安全给
浏览器的字段，尤其是 env/config 状态只能表达 key name + presence，不能
承载 secret value。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


StatusLevel = Literal["ok", "info", "warn", "error"]


class NextAction(BaseModel):
    label: str
    description: str
    command: str | None = None
    href: str | None = None


class StatusItem(BaseModel):
    key: str
    label: str
    status: StatusLevel
    value: str
    detail: str | None = None
    next_action: NextAction | None = None


class EnvKeyStatus(BaseModel):
    name: str
    configured: bool
    sources: list[str] = Field(default_factory=list)


class ProviderAliasStatus(BaseModel):
    alias: str
    type: str
    in_active_profile: bool
    api_key_env: str | None = None
    api_key_present: bool
    base_url_env_present: bool


class ProviderStatus(BaseModel):
    active_profile: str
    opt_in_state: str
    can_run_real_smoke: bool
    aliases: list[ProviderAliasStatus]
    blockers: list[str] = Field(default_factory=list)


class SafetySummary(BaseModel):
    local_only: bool
    host: str
    vault_path: str
    vault_status: StatusLevel
    provider_state: str
    env_status: StatusLevel
    write_mode: Literal["read_only", "explicit_approval_required"]
    pending_drafts_count: int
    warnings: list[str] = Field(default_factory=list)


class WorkspaceStatus(BaseModel):
    config_path: str
    state_path: str
    state_exists: bool
    state_item_count: int
    source_counts: dict[str, int]
    status_counts: dict[str, int]


class VaultStatus(BaseModel):
    path: str
    exists: bool
    inbox_exists: bool
    cards_exists: bool
    projects_exists: bool
    approved_card_count: int
    draft_card_count: int
    scan_error_count: int
    is_real_environment: bool


class RecallStatus(BaseModel):
    index_path: str
    index_exists: bool
    approved_card_count: int
    available: bool
    next_action: NextAction | None = None


class HomeStatusResponse(BaseModel):
    safety: SafetySummary
    workspace: WorkspaceStatus
    vault: VaultStatus
    provider: ProviderStatus
    env_keys: list[EnvKeyStatus]
    recall: RecallStatus
    cards_by_status: dict[str, int]
    next_actions: list[NextAction]


class ConfigStatusResponse(BaseModel):
    safety: SafetySummary
    config_path: str
    configured_keys: list[EnvKeyStatus]
    missing_keys: list[EnvKeyStatus]
    provider: ProviderStatus
    cubox: StatusItem
    vault: VaultStatus
    checklist: list[StatusItem]
    next_actions: list[NextAction]


class HealthResponse(BaseModel):
    ok: bool
    app: str = "MindForge Local Console"
    local_only: bool = True


class SourceStatus(BaseModel):
    source_type: str
    adapter: str
    inbox_subdir: str
    file_glob: str
    enabled: bool
    path: str
    exists: bool
    file_count: int
    error_count: int = 0
    next_action: NextAction | None = None


class SourcesResponse(BaseModel):
    sources: list[SourceStatus]
    available_imports: list[StatusItem]
    next_actions: list[NextAction]


class UnavailableResponse(BaseModel):
    available: bool = False
    reason: str
    next_action: NextAction


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
    source_title: str | None
    value_score: int | None
    created_at: str | None = None
    updated_at: str | None = None


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


class RecallHit(BaseModel):
    score: float
    title: str | None
    rel_path: str
    status: str
    track: str | None
    projects: list[str]
    tags: list[str]
    source_type: str | None
    why_this_matched: str


class RecallResponse(BaseModel):
    query: str
    hits: list[RecallHit]
    index: RecallStatus
    warnings: list[str] = Field(default_factory=list)
    empty_state: NextAction | None = None


class ApiError(BaseModel):
    error: str
    message: str
    next_action: str | None = None
