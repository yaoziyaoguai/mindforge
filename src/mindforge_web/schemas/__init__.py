"""Pydantic schemas for MindForge Local Console API.

中文学习型说明：这些 schema 是 Web 边界的公开契约。它们只描述可安全给
浏览器的字段，尤其是 env/config 状态只能表达 key name + presence，不能
承载 secret value。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from mindforge_web.schemas.common import NextAction, SourcePathViewModel, StatusItem, StatusLevel  # noqa: E402, F401
from mindforge_web.schemas.provider import (  # noqa: E402, F401
    ConfigStatusResponse,
    EditableCuboxConfig,
    EditableLLMConfig,
    EditableModelConfig,
    EditableProviderConfig,
    EditableVaultConfig,
    EditableWikiConfig,
    EnvKeyStatus,
    HomeStatusResponse,
    ProcessingWorkflowConfig,
    ProcessingWorkflowStep,
    ProviderAliasStatus,
    ProviderReadinessResponse,
    ProviderStatus,
    RecallStatus,
    ResolvedWorkflowModelConfig,
    SafetySummary,
    SetProviderModeRequest,
    SetupConfigPatch,
    SetupConfigUpdateResponse,
    SetupEditableConfigResponse,
    SetupModelPatch,
    SetupProviderPatch,
    SetupValidationResponse,
    VaultStatus,
    WikiRebuildRequest,
    WorkspaceStatus,
)


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


from mindforge_web.schemas.source import (  # noqa: E402, F401
    FrequencyUpdateRequest,
    IngestionActionResponse,
    IngestionRequest,
    IngestionSummaryStatus,
    ProcessingRunResponse,
    SourcesResponse,
    SourceStatus,
    WatchedSourceResponse,
    WatchSourcesResponse,
)


from mindforge_web.schemas.library import (  # noqa: E402, F401
    LibraryCardDetailResponse,
    LibraryCardResponse,
    LibraryCardsResponse,
    LibraryStatsResponse,
    LocalGraphEdgeResponse,
    LocalGraphNodeResponse,
    LocalGraphResponse,
    RelatedCardReasonResponse,
    RelatedCardResponse,
)


from mindforge_web.schemas.graph import (  # noqa: E402, F401
    GraphEdgeDetailResponse,
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    RelationEvidenceResponse,
)

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


# Import/Export schemas — 已提取到 schemas/import_export.py，此处 re-export 保持 backward compatibility。
# 中文学习型说明：所有 from mindforge_web.schemas import ExportCardsRequest 等 import 路径不受影响。
from mindforge_web.schemas.import_export import (  # noqa: E402, F401
    BatchImportCardItem,
    BatchImportCardRequest,
    BatchImportCardResponse,
    ExportCardsRequest,
    ExportCardsResponse,
    FolderImportPreviewRequest,
    FolderImportPreviewResponse,
    FolderImportRequest,
    FolderImportResponse,
    ImportCardRequest,
    ImportCardResponse,
    _FolderImportPreviewFile,
    _FolderImportResultItem,
    _PotentialDuplicateResponse,
)


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


from mindforge_web.schemas.recall import RecallHit, RecallResponse  # noqa: E402, F401


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
    # v3.3 新增
    representative_card_ids: list[str] = Field(default_factory=list)
    source_coverage: float = 0.0
    evidence_detail: str = ""


class KnowledgeCommunitiesResponse(BaseModel):
    communities: list[KnowledgeCommunityResponse]


# ============================================================================
# v3.3 Topic Synthesis schemas
# ============================================================================


class TopicMemberCommunityResponse(BaseModel):
    """Topic 内的成员社区引用。"""
    community_type: str
    shared_entity: str
    member_count: int
    quality_score: float


class KnowledgeTopicResponse(BaseModel):
    """知识主题 — v3.3 交叉社区合成。"""
    topic_id: str
    topic_name: str
    community_count: int
    total_card_count: int
    card_ids: list[str]
    member_communities: list[TopicMemberCommunityResponse]
    representative_card_ids: list[str]
    evidence: str


class KnowledgeTopicsResponse(BaseModel):
    topics: list[KnowledgeTopicResponse]


# ============================================================================
# Dogfood + Lifecycle schemas — 已提取到 schemas/dogfood_lifecycle.py，此处 re-export 保持 backward compatibility。
from mindforge_web.schemas.dogfood_lifecycle import (  # noqa: E402, F401
    DogfoodReportResponse,
    DogfoodTrendPoint,
    LifecycleResponse,
    SourceLifecycleItem,
)
from mindforge_web.schemas.review import (  # noqa: E402, F401
    ApprovalResponse,
    ApproveRequest,
    DraftDetailResponse,
    DraftsResponse,
    DraftSummary,
    RejectRequest,
)

from mindforge_web.schemas.sensemaking import (  # noqa: E402, F401
    SensemakingBridgeNodeResponse,
    SensemakingCardEvolutionResponse,
    SensemakingCardEvolutionStepResponse,
    SensemakingCommunitySubgraphResponse,
    SensemakingEvidenceTrailItemResponse,
    SensemakingEvidenceTrailResponse,
    SensemakingOrphanIslandResponse,
    SensemakingResponse,
    SensemakingSourceInfluenceResponse,
)
