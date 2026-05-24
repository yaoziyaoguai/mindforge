"""Pydantic schemas for MindForge Local Console API.

中文学习型说明：这些 schema 是 Web 边界的公开契约。它们只描述可安全给
浏览器的字段，尤其是 env/config 状态只能表达 key name + presence，不能
承载 secret value。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


StatusLevel = Literal["ok", "info", "warn", "error"]


class NextAction(BaseModel):
    label: str
    description: str
    command: str | None = None
    href: str | None = None
    action_key: str | None = None  # 稳定展示映射键，前端据此做本地化。可选，缺省时前端 fallback 到 label
    description_key: str | None = None  # action.description 本地化键，与 action_key 同模式。可选，缺省时前端 fallback 到原始 description


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
    active_profile: str  # legacy: 现在使用 llm.models/default_model/routing 模型路由体系
    opt_in_state: str
    model_setup: str = "needs_setup"
    model_setup_label: str = "needs setup"
    can_run_real_smoke: bool
    provider_mode: Literal["fake", "real"] = "fake"
    aliases: list[ProviderAliasStatus]
    blockers: list[str] = Field(default_factory=list)


class SetProviderModeRequest(BaseModel):
    mode: Literal["fake", "real"]


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
    api_key_env_configured: bool = False
    api_key_secret_present: bool = False
    api_key_masked_value: str | None = None
    api_key_status_label: str
    base_url_env: str | None = None
    base_url_env_present: bool = False
    base_url_env_status: Literal["present", "missing", "not_configured"] = "not_configured"
    effective_base_url: str | None = None
    base_url_source: Literal["env", "config_default", "missing"] = "missing"
    model_env: str | None = None
    model_env_present: bool = False
    model_env_status: Literal["present", "missing", "not_configured"] = "not_configured"
    effective_model: str | None = None
    model_source: Literal["env", "config_default", "missing"] = "missing"


class EditableModelConfig(BaseModel):
    model_id: str
    type: str
    base_url: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    api_key_optional: bool = False
    api_key_status: Literal["present", "missing", "hidden"]
    api_key_env_configured: bool = False
    api_key_secret_present: bool = False
    api_key_masked_value: str | None = None
    api_key_status_label: str
    api_key_source: Literal["local_secret", "env", "missing", "demo"] = "missing"
    is_demo_model: bool = False
    base_url_env: str | None = None
    model_env: str | None = None
    effective_base_url: str | None = None
    base_url_source: Literal["env", "config_default", "missing"] = "missing"
    effective_model: str | None = None
    model_source: Literal["env", "config_default", "missing"] = "missing"


class ResolvedWorkflowModelConfig(BaseModel):
    workflow_step: str
    model_id: str
    type: str
    base_url: str | None = None
    model: str | None = None


class ProcessingWorkflowStep(BaseModel):
    """单个 workflow step 的只读展示视图 —— 组合 strategy + prompt + model routing。"""
    id: str
    label: str
    purpose: str
    model_id: str
    prompt_id: str
    prompt_version: str
    prompt_description: str = ""
    can_view_prompt: bool = True


class ProcessingWorkflowConfig(BaseModel):
    """Processing workflow 的完整配置视图。"""
    active_strategy_id: str
    active_strategy_label: str
    active_strategy_description: str
    active_strategy_status: str = "built-in"
    available_strategies: list[dict] = Field(default_factory=list)
    workflow_steps: list[ProcessingWorkflowStep] = Field(default_factory=list)


class EditableLLMConfig(BaseModel):
    active_provider: str
    available_providers: list[str]
    providers: dict[str, EditableProviderConfig]
    readiness: ProviderStatus
    configured_model_ids: list[str] = Field(default_factory=list)
    configured_models: dict[str, EditableModelConfig] = Field(default_factory=dict)
    default_model: str | None = None
    routing: dict[str, str] = Field(default_factory=dict)
    routing_is_explicit: bool = False
    resolved_per_step_models: dict[str, ResolvedWorkflowModelConfig] = Field(default_factory=dict)
    processing_workflow: ProcessingWorkflowConfig | None = None
    legacy_config_detected: bool = False
    validation_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EditableCuboxConfig(BaseModel):
    export_path: str | None = None
    import_path: str | None = None
    token_status: Literal["present", "missing", "hidden"]


class EditableWikiConfig(BaseModel):
    """Wiki 可编辑配置。

    mode 为 deprecated/compatibility 字段。MindForge Web UI 只展示 LLM synthesis
    作为主路径，deterministic 仅保留为内部 fallback / 测试路径，不在普通用户
    可选项中暴露。此字段仍在 API response 中返回（兼容旧前端），但 Setup 页面
    不再将其作为用户可选 generation mode。
    """
    mode: str = "deterministic"  # deprecated: compatibility fallback, not user-facing
    model: str | None = None
    auto_rebuild_on_approve: bool = False


class WikiRebuildRequest(BaseModel):
    """Wiki rebuild API body；前端按钮必须显式传 mode，避免回落到配置值。"""

    mode: Literal["deterministic", "llm"] | None = None


class SetupEditableConfigResponse(BaseModel):
    config_path: str
    normalized_on_save: bool
    vault: EditableVaultConfig
    llm: EditableLLMConfig
    wiki: EditableWikiConfig | None = None
    cubox: EditableCuboxConfig
    watch_summary: StatusItem


class SetupProviderPatch(BaseModel):
    default_base_url: str | None = None
    default_model: str | None = None
    api_key_env: str | None = None
    base_url_env: str | None = None
    model_env: str | None = None


class SetupModelPatch(BaseModel):
    type: str | None = None
    base_url: str | None = None
    model: str | None = None
    api_key_env: str | None = None
    api_key_optional: bool | None = None
    base_url_env: str | None = None
    model_env: str | None = None
    # API key 由用户在前端输入，后端写入 secret store；永远不出现在 response 中。
    api_key: str | None = None
    # "keep"（默认）— 保留已有 secret；"clear" — 显式删除；"update" — 用新值覆盖。
    api_key_action: Literal["keep", "clear", "update"] | None = None


class SetupConfigPatch(BaseModel):
    vault_root: str | None = None
    create_vault: bool = False
    active_provider: str | None = None
    providers: dict[str, SetupProviderPatch] = Field(default_factory=dict)
    default_model: str | None = None
    models: dict[str, SetupModelPatch] = Field(default_factory=dict)
    routing: dict[str, str] = Field(default_factory=dict)
    wiki_mode: str | None = Field(default=None, description="deprecated: compatibility fallback; Web UI no longer sets this field")
    wiki_model: str | None = None
    wiki_auto_rebuild_on_approve: bool | None = None
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


class HealthIssueResponse(BaseModel):
    code: str
    severity: str
    message: str
    suggested_action: str
    reason: str = ""
    affected_card_ids: list[str] = Field(default_factory=list)


class HealthReportResponse(BaseModel):
    summary: str
    stats: dict[str, int] = Field(default_factory=dict)
    issues: list[HealthIssueResponse] = Field(default_factory=list)
    maintenance_suggestions: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    ok: bool
    app: str = "MindForge Local Console"
    local_only: bool = True
    report: HealthReportResponse | None = None


class SourceStatus(BaseModel):
    source_type: str
    adapter: str
    inbox_subdir: str
    file_glob: str
    enabled: bool
    path: str
    source_path_view: SourcePathViewModel | None = None
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
    source_path_view: SourcePathViewModel | None = None
    path_type: Literal["file", "folder"]
    is_default: bool
    kind: Literal["default", "user-added"]
    status: str
    added_at: str
    last_seen_at: str | None = None
    last_processed_at: str | None = None
    last_scan_at: str | None = None
    next_scan_at: str | None = None
    frequency: str = "manual"
    due_status: Literal["Due", "Not due", "Manual"] = "Manual"
    fingerprint: str | None = None
    can_delete: bool
    error: str | None = None
    recursive: bool = False
    supported_file_count: int = 0
    processed_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    skipped_reason_summary: dict[str, int] = Field(default_factory=dict)
    diff_counts: dict[str, int] = Field(default_factory=dict)
    generated_knowledge_status: str = "No generated knowledge"
    generated_card_count: int = 0
    generated_card_paths: list[str] = Field(default_factory=list)
    status_label: str = "Watching"
    active_run_id: str | None = None
    last_run_id: str | None = None
    last_run_started_at: str | None = None
    last_run_finished_at: str | None = None
    processing_status: str | None = None
    last_run_summary: dict[str, int] | None = None
    last_message: str | None = None
    last_error: str | None = None
    generated_draft_count: int = 0


class WatchSourcesResponse(BaseModel):
    vault_root: str
    registry_path: str
    watched_sources: list[WatchedSourceResponse]
    next_actions: list[NextAction]


class IngestionRequest(BaseModel):
    path: str
    frequency: str | None = None
    recursive: bool | None = None
    process_now: bool = True


class FrequencyUpdateRequest(BaseModel):
    frequency: str


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
    run_id: str | None = None
    processing_status: str | None = None
    skip_reasons: list[str] = Field(default_factory=list)
    error_message: str | None = None


class ProcessingRunResponse(BaseModel):
    run_id: str
    source_ref: str
    source_path: str | None = None
    source_path_view: SourcePathViewModel | None = None
    mode: str
    status: Literal["queued", "running", "succeeded", "skipped", "failed", "partial_failed"]
    started_at: str
    last_heartbeat_at: str | None = None
    finished_at: str | None = None
    current_step: str
    summary: dict[str, int] = Field(default_factory=dict)
    draft_ids: list[str] = Field(default_factory=list)
    message: str
    skip_reasons: list[str] = Field(default_factory=list)
    error_type: str | None = None
    error_message: str | None = None
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
    source_path: str | None = None
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
    fallback_provider_note: str | None = None
    # M1 quality 字段（来自 frontmatter；旧卡片无 quality 块时为 None）
    quality_score: int | None = None
    quality_level: str | None = None
    # 中文学习型说明：后端生成的 source path 安全视图；前端只展示，不做安全决策。
    source_path_view: SourcePathViewModel | None = None


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


class LocalGraphNodeResponse(BaseModel):
    id: str
    type: Literal["card", "source", "wiki_section", "tag"]
    label: str
    href: str | None = None
    card_count: int | None = None


class LocalGraphEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    reason: str
    label: str


class LocalGraphResponse(BaseModel):
    center_id: str
    center_type: Literal["card", "source", "wiki_section", "tag"]
    nodes: list[LocalGraphNodeResponse] = Field(default_factory=list)
    edges: list[LocalGraphEdgeResponse] = Field(default_factory=list)


class RelatedCardReasonResponse(BaseModel):
    reason: str
    label: str
    detail: str
    strength: float
    # v2.1: multi-hop 信息
    hop_distance: int = 1
    via_path: list[str] = Field(default_factory=list)


class RelatedCardResponse(BaseModel):
    card: LibraryCardResponse
    reasons: list[RelatedCardReasonResponse] = Field(default_factory=list)


class LibraryCardDetailResponse(BaseModel):
    card: LibraryCardResponse
    body: str | None = None
    local_graph: LocalGraphResponse | None = None
    related_cards: list[RelatedCardResponse] = Field(default_factory=list)


# -- v0.6 Graph API -----------------------------------------------------------


class RelationEvidenceResponse(BaseModel):
    """图中边的可解释证据。"""
    reason: str
    evidence: str
    strength: float
    detail: dict = Field(default_factory=dict)


class GraphNodeResponse(BaseModel):
    id: str
    type: Literal["card", "source", "wiki_section", "tag", "concept"]
    label: str
    href: str | None = None
    card_count: int = 0


class GraphEdgeResponse(BaseModel):
    source_id: str
    target_id: str
    edge_type: Literal[
        "derived_from", "mentions", "shares_tag",
        "related_by_source", "related_by_wiki_section",
        "similar_title_or_term", "approval_state_of",
        "links_to", "wiki_section_reference",
    ]
    evidence: RelationEvidenceResponse


class GraphResponse(BaseModel):
    center_id: str
    center_type: Literal["card", "source", "wiki_section", "tag", "concept"]
    depth: int
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    edges: list[GraphEdgeResponse] = Field(default_factory=list)


class GraphEdgeDetailResponse(BaseModel):
    source_id: str
    target_id: str
    edges: list[GraphEdgeResponse] = Field(default_factory=list)


# -- U3 Provenance Trail ------------------------------------------------------

class ProvenanceTrailSource(BaseModel):
    source_id: str | None = None
    source_title: str | None = None


class ProvenanceTrailSiblingCard(BaseModel):
    card_id: str
    title: str
    quality_level: str | None = None
    quality_score: float | None = None


class ProvenanceTrailSection(BaseModel):
    title: str
    card_count: int


class ProvenanceTrailRelatedSource(BaseModel):
    """与当前 source 通过共享 tags/wiki_sections 关联的其他 source。"""
    source_id: str
    source_title: str | None = None
    card_count: int
    shared_tags: list[str] = Field(default_factory=list)
    shared_wiki_sections: list[str] = Field(default_factory=list)


class ProvenanceTrailResponse(BaseModel):
    card_id: str
    source: ProvenanceTrailSource = Field(default_factory=ProvenanceTrailSource)
    sibling_cards: list[ProvenanceTrailSiblingCard] = Field(default_factory=list)
    wiki_sections: list[ProvenanceTrailSection] = Field(default_factory=list)
    related_sources: list[ProvenanceTrailRelatedSource] = Field(default_factory=list)


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


class ExportCardsRequest(BaseModel):
    card_ids: list[str]
    format: str = "markdown"  # "markdown" | "json" | "opml"


class ExportCardsResponse(BaseModel):
    markdown: str = ""
    json_data: str = Field(default="", alias="json")
    opml: str = ""
    format: str = "markdown"
    card_count: int = 0


class ImportCardRequest(BaseModel):
    title: str
    body: str
    source_name: str = ""


class ImportCardResponse(BaseModel):
    id: str
    title: str
    rel_path: str
    status: str
    created_at: str


# ── v2.4 U1 Folder Import ──────────────────────


class FolderImportPreviewRequest(BaseModel):
    """扫描指定文件夹，dry-run 预览可导入的 .md 文件。"""
    folder_path: str


class _FolderImportPreviewFile(BaseModel):
    """单个 .md 文件的预览信息。"""
    index: int
    filename: str
    title: str
    body_preview: str  # 前 200 字符预览
    size_bytes: int
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None  # 非空表示该文件无法导入


class FolderImportPreviewResponse(BaseModel):
    folder_path: str
    total_files: int
    importable_count: int
    files: list[_FolderImportPreviewFile]
    folder_warning: str | None = None


class FolderImportRequest(BaseModel):
    """确认批量导入文件夹中的指定文件。"""
    folder_path: str
    indices: list[int]  # 选择导入的文件索引（来自 preview）


class _FolderImportResultItem(BaseModel):
    """单个文件导入结果。"""
    index: int
    filename: str
    status: str  # "created" | "skipped" | "failed"
    card_id: str | None = None
    title: str | None = None
    error: str | None = None


class FolderImportResponse(BaseModel):
    folder_path: str
    results: list[_FolderImportResultItem]
    created_count: int
    skipped_count: int
    failed_count: int


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


class SourcePathViewModel(BaseModel):
    """后端生成的 source path 安全视图 —— 前端只展示，不做安全决策。

    中文学习型说明：path_kind 由后端根据 allowlisted roots 计算，
    前端根据 can_copy_full_path / can_reveal_in_finder 禁用按钮。
    outside_allowed_roots 时不展示完整 absolute path。
    """

    display_source_name: str | None = None
    """展示用的 source 名称（basename 或脱敏路径）。"""

    display_path: str | None = None
    """展示路径。outside 时仅显示 basename，不暴露完整路径。"""

    path_kind: Literal[
        "workspace",
        "registered_source",
        "outside_allowed_roots",
        "not_available",
        "unknown",
    ] = "unknown"
    """路径分类：workspace / registered_source / outside_allowed_roots /
    not_available / unknown。"""

    full_path_available: bool = False
    """完整 absolute path 是否对用户可见。"""

    can_copy_full_path: bool = False
    """是否允许 Copy full absolute path。"""

    can_copy_display_path: bool = False
    """是否允许 Copy display path（always true if display_path 存在）。"""

    can_reveal_in_finder: bool = False
    """是否允许 Reveal in Finder。"""

    safety_label: str | None = None
    """安全标签（如 \"Workspace\" / \"Registered Source\" / \"External\"）。"""

    warning: str | None = None
    """安全警告文案。outside 时说明路径不在 workspace 或已注册 source root 内。"""


class PathActionRequest(BaseModel):
    path: str


class RevealRequest(BaseModel):
    """安全的 object-reference reveal 请求 —— 不接受 raw path。

    中文学习型说明：前端传 card_id 或 draft_id，后端自行查找对象并校验权限，
    不信任用户提供的 path 字符串。extra="forbid" 确保传入 path 等额外字段时
    返回 422 而非静默忽略。
    """

    model_config = {"extra": "forbid"}

    card_id: str | None = None
    draft_id: str | None = None

    @model_validator(mode="after")
    def _exactly_one_ref(self) -> "RevealRequest":
        """card_id 和 draft_id 必须二选一，不能同时传也不能都不传。"""
        if (self.card_id is not None) == (self.draft_id is not None):
            raise ValueError("exactly one of card_id or draft_id is required")
        return self


class PathActionResponse(BaseModel):
    ok: bool
    action: Literal["copy", "reveal"]
    path: str
    path_type: Literal["file", "folder"]
    message: str
    command: list[str] = Field(default_factory=list)
    # 中文学习型说明：path_kind 让前端在 action 执行前后都能判断安全性，
    # 避免"提示 outside 但仍提供 Reveal"的截图问题。
    path_kind: Literal[
        "workspace",
        "registered_source",
        "outside_allowed_roots",
        "not_available",
        "unknown",
    ] = "unknown"


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
    # v0.6 R6: graph context enrichment（context=graph 时填充）
    graph_neighbor_count: int | None = None
    graph_shared_tag_count: int | None = None


class RecallResponse(BaseModel):
    query: str
    hits: list[RecallHit]
    index: RecallStatus
    warnings: list[str] = Field(default_factory=list)
    empty_state: NextAction | None = None


# -- v0.6 R6 Discovery Context ------------------------------------------------


class DiscoveryCardRefResponse(BaseModel):
    card_id: str
    title: str
    relation_reason: str
    relation_strength: float
    evidence: str


class DiscoverySectionRefResponse(BaseModel):
    section_title: str
    card_count: int


class DiscoveryTagRefResponse(BaseModel):
    tag: str
    card_count: int


class DiscoverySourceRefResponse(BaseModel):
    source_id: str
    card_count: int


class DiscoveryCommunityRefResponse(BaseModel):
    community_type: str  # "source", "tag", "wiki_section"
    shared_entity: str
    member_count: int
    description: str


class DiscoveryContextResponse(BaseModel):
    center_card_id: str
    center_card_title: str
    direct_matches: list[DiscoveryCardRefResponse] = Field(default_factory=list)
    neighbor_cards: list[DiscoveryCardRefResponse] = Field(default_factory=list)
    wiki_sections: list[DiscoverySectionRefResponse] = Field(default_factory=list)
    shared_tags: list[DiscoveryTagRefResponse] = Field(default_factory=list)
    shared_sources: list[DiscoverySourceRefResponse] = Field(default_factory=list)
    communities: list[DiscoveryCommunityRefResponse] = Field(default_factory=list)
    # v2.1
    reasoning: str = ""
    estimated_token_count: int = 0


# ============================================================================
# Trash schemas
# ============================================================================


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


class ApiError(BaseModel):
    error: str
    message: str
    next_action: str | None = None


# ---------------------------------------------------------------------------
# M1 Quality schemas — SDD §4.1
# ---------------------------------------------------------------------------

class QualityRubricScoreResponse(BaseModel):
    dimension: str
    score: float
    max_score: float = 1.0
    notes: str = ""


class QualityWarningResponse(BaseModel):
    code: str
    severity: str
    message: str
    suggestion: str = ""


class CardQualityResponse(BaseModel):
    card_id: str
    overall_level: str  # "high" | "medium" | "low"
    overall_level_label: str  # "高质量" | "中质量" | "低质量"
    overall_score: float
    rubric_scores: list[QualityRubricScoreResponse]
    warnings: list[QualityWarningResponse]
    card_type: str | None = None
    regenerate_suggestion: str | None = None
    split_candidate: bool = False
    merge_candidate: bool = False


# ============================================================================
# M4 Source Location / Provenance schemas — SDD §8
# ============================================================================


class SourceLocationResponse(BaseModel):
    source_type: str
    heading_path: list[str] | None = None
    line_start: int | None = None
    line_end: int | None = None
    page_number: int | None = None
    paragraph_start: int | None = None
    paragraph_end: int | None = None
    css_selector: str | None = None
    display: str


# ── v1.2 Knowledge Community ──────────────────────


class SubCommunityRefResponse(BaseModel):
    """子社区引用 — v2.1 多层级分组。"""
    community_type: str  # "source" | "tag" | "wiki_section"
    shared_entity: str
    member_count: int


class CommunityOverlapResponse(BaseModel):
    """社区重叠信息 — v2.1 共享成员交叉检测。"""
    community_type: str
    shared_entity: str
    shared_member_count: int
    shared_member_ids: list[str]


class KnowledgeCommunityResponse(BaseModel):
    community_type: str  # "source" | "tag" | "wiki_section"
    shared_entity: str
    member_count: int
    member_card_ids: list[str]
    description: str
    # v2.1 新增
    sub_communities: list[SubCommunityRefResponse] = Field(default_factory=list)
    overlap_with: list[CommunityOverlapResponse] = Field(default_factory=list)
    quality_score: float = 0.0


class KnowledgeCommunitiesResponse(BaseModel):
    communities: list[KnowledgeCommunityResponse]
