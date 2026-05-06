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


class EditableVaultConfig(BaseModel):
    root: str
    exists: bool
    inbox_exists: bool
    cards_exists: bool
    projects_exists: bool


class EditableProviderConfig(BaseModel):
    name: str
    type: str
    default_base_url: str | None = None
    default_model: str | None = None
    api_key_env: str | None = None
    api_key_status: Literal["present", "missing", "hidden"]
    base_url_env: str | None = None
    base_url_env_present: bool = False
    model_env: str | None = None
    model_env_present: bool = False


class EditableLLMConfig(BaseModel):
    active_provider: str
    available_providers: list[str]
    providers: dict[str, EditableProviderConfig]
    readiness: ProviderStatus


class EditableCuboxConfig(BaseModel):
    export_path: str | None = None
    import_path: str | None = None
    token_status: Literal["present", "missing", "hidden"]


class SetupEditableConfigResponse(BaseModel):
    config_path: str
    normalized_on_save: bool
    vault: EditableVaultConfig
    llm: EditableLLMConfig
    cubox: EditableCuboxConfig
    watch_summary: StatusItem


class SetupProviderPatch(BaseModel):
    default_base_url: str | None = None
    default_model: str | None = None
    api_key_env: str | None = None
    base_url_env: str | None = None
    model_env: str | None = None


class SetupConfigPatch(BaseModel):
    vault_root: str | None = None
    create_vault: bool = False
    active_provider: str | None = None
    providers: dict[str, SetupProviderPatch] = Field(default_factory=dict)
    cubox_export_path: str | None = None
    cubox_import_path: str | None = None


class SetupValidationResponse(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SetupConfigUpdateResponse(BaseModel):
    ok: bool
    message: str
    status: ConfigStatusResponse
    editable: SetupEditableConfigResponse


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
    processed_count: int = 0
    pending_files: list[str] = Field(default_factory=list)
    processed_files: list[str] = Field(default_factory=list)
    display_status: str
    generated_knowledge_status: str
    generated_card_count: int = 0
    generated_card_paths: list[str] = Field(default_factory=list)
    next_action: NextAction | None = None


class WatchedSourceResponse(BaseModel):
    id: str
    path: str
    path_type: Literal["file", "folder"]
    is_default: bool
    kind: Literal["default", "user-added"]
    status: str
    added_at: str
    last_seen_at: str | None = None
    last_processed_at: str | None = None
    fingerprint: str | None = None
    can_delete: bool
    error: str | None = None


class WatchSourcesResponse(BaseModel):
    vault_root: str
    registry_path: str
    watched_sources: list[WatchedSourceResponse]
    next_actions: list[NextAction]


class IngestionRequest(BaseModel):
    path: str


class IngestionActionResponse(BaseModel):
    ok: bool
    mode: str
    target: str
    counts: dict[str, int]
    message: str
    added_to_registry: bool
    registry_path: str | None = None
    watch_id: str | None = None
    source_deleted: bool = False
    cards_deleted: bool = False
    next_actions: list[NextAction] = Field(default_factory=list)


class IngestionSummaryStatus(BaseModel):
    primary_entry: str
    safety_note: str
    advanced_note: str


class SourcesResponse(BaseModel):
    sources: list[SourceStatus]
    bucket_counts: dict[str, dict[str, int]] = Field(default_factory=dict)
    watched_sources: list[WatchedSourceResponse] = Field(default_factory=list)
    available_imports: list[StatusItem]
    ingestion: IngestionSummaryStatus
    next_actions: list[NextAction]


class LibraryCardResponse(BaseModel):
    id: str | None
    title: str | None
    status: str
    status_explanation: str
    track: str | None
    source_type: str | None
    source_id: str | None = None
    adapter_name: str | None
    source_title: str | None
    source_path: str | None
    source_content_hash: str | None = None
    source_archive_path: str | None
    source_missing: bool
    profile: str | None
    provider: str | None
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
    rel_path: str
    fake_provider_note: str | None = None


class LibraryStatsResponse(BaseModel):
    vault_root: str
    cards_dir: str
    total_cards: int
    by_status: dict[str, int]
    by_track: dict[str, int]
    by_provider: dict[str, int]
    recent_count: int
    index_path: str
    index_exists: bool
    next_action: str


class LibraryCardsResponse(BaseModel):
    stats: LibraryStatsResponse
    cards: list[LibraryCardResponse]


class LibraryCardDetailResponse(BaseModel):
    card: LibraryCardResponse
    body: str | None = None


class CardBodyUpdateRequest(BaseModel):
    body: str


class CardBodyUpdateResponse(BaseModel):
    ok: bool
    status: str
    message: str
    card_path: str
    rel_path: str | None = None
    index_updated: bool = False
    index_path: str | None = None
    index_error: str | None = None


class WorkflowSummaryResponse(BaseModel):
    vault_root: str
    cards_dir: str
    inbox_pending_count: int
    processed_source_count: int
    ai_draft_count: int
    human_approved_count: int
    index: RecallStatus
    provider: ProviderStatus
    source_bucket_counts: dict[str, dict[str, int]]
    next_actions: list[NextAction]


class UnavailableResponse(BaseModel):
    available: bool = False
    reason: str
    next_action: NextAction


class PathActionRequest(BaseModel):
    path: str


class PathActionResponse(BaseModel):
    ok: bool
    action: Literal["copy", "reveal"]
    path: str
    path_type: Literal["file", "folder"]
    message: str
    command: list[str] = Field(default_factory=list)


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
    index_updated: bool = False
    index_path: str | None = None
    index_error: str | None = None


class RecallHit(BaseModel):
    score: float
    title: str | None
    card_ref: str | None = None
    detail_href: str | None = None
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
