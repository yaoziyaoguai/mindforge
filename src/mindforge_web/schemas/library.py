"""Library, Card, and Local Graph schemas.

中文学习型说明：这些 schema 涵盖知识卡片列表、卡片详情、本地图谱预览、
关联卡片等 Library 主页面的核心契约。LocalGraph 是 Library 内嵌的轻量
确定性图谱预览，不是完整的 /graph API（后者属于 lab/internal）。
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from mindforge_web.schemas.common import SourcePathViewModel


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


# ── Saved Views ────────────────────────────────────────────────────────


class SavedViewResponse(BaseModel):
    id: str
    name: str
    status_filter: str = "all"
    track_filter: str = "all"
    source_type_filter: str = "all"
    quality_filter: str = "all"
    sort_by: str = "newest"
    created_at: str = ""


class SavedViewsListResponse(BaseModel):
    views: list[SavedViewResponse]


class SaveViewRequest(BaseModel):
    id: str
    name: str
    status_filter: str = "all"
    track_filter: str = "all"
    source_type_filter: str = "all"
    quality_filter: str = "all"
    sort_by: str = "newest"


# ── Collections ────────────────────────────────────────────────────────


class CollectionResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    card_refs: list[str] = Field(default_factory=list)
    rule_tags: list[str] = Field(default_factory=list)
    created_at: str = ""


class CollectionsListResponse(BaseModel):
    collections: list[CollectionResponse]


class CreateCollectionRequest(BaseModel):
    id: str
    name: str
    description: str = ""
    rule_tags: list[str] = Field(default_factory=list)


class CollectionCardsRequest(BaseModel):
    card_refs: list[str]
