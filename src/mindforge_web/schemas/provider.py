"""Provider, Config, Setup, and Home status schemas.

中文学习型说明：这些 schema 涵盖 provider 就绪状态、LLM 配置编辑、
setup 向导、home status dashboard、workflow 配置等 Web adapter 层的核心
契约。所有字段只暴露安全的配置视图（key name + presence），不承载 secret value。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from mindforge_web.schemas.common import NextAction, StatusItem, StatusLevel


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


class ProviderReadinessResponse(BaseModel):
    """v2.5 U4 Provider Readiness Center — 独立 provider 就绪状态 API 响应。

    中文学习型说明：基于 provider_readiness.py 的 build_readiness_report +
    model_setup_readiness，返回所有 provider 的就绪状态，不包含 API key 值。
    """
    active_profile: str
    opt_in_state: str
    model_setup: str = "needs_setup"
    model_setup_label: str = "needs setup"
    can_run_real_smoke: bool
    provider_mode: str = "fake"
    aliases: list[ProviderAliasStatus]
    blockers: list[str] = Field(default_factory=list)
    invariants: dict[str, bool] = Field(default_factory=dict)


class ProviderStatusResponse(BaseModel):
    """GET /api/provider/status — 安全脱敏的 provider 连接状态。

    只返回 redacted/masked 信息，绝不包含 API key 明文、Authorization header 或 raw secret。
    """
    provider_type: str | None = None
    model: str | None = None
    configured: bool = False
    verified: bool = False
    verification_status: Literal["not_verified", "verified", "failed"] = "not_verified"
    masked_key: str | None = None
    base_url_host: str | None = None
    base_url_path: str | None = None
    last_checked_at: str | None = None
    last_error: str | None = None
    provider_mode: Literal["fake", "real"] = "fake"
    can_run_real_smoke: bool = False


class TestConnectionRequest(BaseModel):
    model_id: str = Field(description="要测试的模型 alias")


class TestConnectionResponse(BaseModel):
    ok: bool
    message: str
    verification_status: Literal["not_verified", "verified", "failed"] = "not_verified"
    last_checked_at: str | None = None
    last_error: str | None = None
    latency_ms: int | None = None


class UsageReportResponse(BaseModel):
    """GET /api/usage/report — 本地使用摘要，不上传，不追踪。

    local-only，无遥测，不收集 secret。缺失数据展示为 empty/not available。
    """
    generated_at: str
    total_cards: int = 0
    approved_count: int = 0
    draft_count: int = 0
    total_sources: int = 0
    wiki_sections: int = 0
    search_available: bool = False
    provider_configured: bool = False
    provider_verified: bool = False
    provider_verification_status: str = "not_verified"
    provider_mode: str = "fake"
    recent_runs: int = 0
    backend_gaps: list[str] = Field(default_factory=list)


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
