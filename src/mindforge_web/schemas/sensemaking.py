"""Sensemaking Workspace schemas — lab/internal.

中文学习型说明：这些 schema 是 Sensemaking Workspace 的 API 响应契约，
包含桥接节点、孤立岛屿、证据溯源、源影响路径、卡片演化路径、社区子图。
注意：Sensemaking 是 lab/internal 功能，不是主路径产品。
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SensemakingBridgeNodeResponse(BaseModel):
    """v4.0: 桥接节点 — 连接多个社区的关键卡片。"""
    card_id: str
    card_title: str
    connecting_communities: list[str] = Field(default_factory=list)
    community_count: int


class SensemakingOrphanIslandResponse(BaseModel):
    """v4.0: 孤立岛屿 — 无共享关系的卡片群。"""
    card_ids: list[str] = Field(default_factory=list)
    card_titles: list[str] = Field(default_factory=list)
    size: int
    is_true_orphan: bool


class SensemakingEvidenceTrailItemResponse(BaseModel):
    """v4.0: 证据溯源项。"""
    evidence_type: str
    evidence_label: str
    description: str


class SensemakingEvidenceTrailResponse(BaseModel):
    """v4.0: 边的完整溯源链。"""
    source_id: str
    source_title: str
    target_id: str
    target_title: str
    trail_items: list[SensemakingEvidenceTrailItemResponse] = Field(default_factory=list)
    total_shared_entities: int


class SensemakingSourceInfluenceResponse(BaseModel):
    """v4.0: 源文档影响传播路径。"""
    source_id: str
    source_label: str
    direct_cards: list[str] = Field(default_factory=list)
    direct_card_titles: list[str] = Field(default_factory=list)
    influenced_cards: list[str] = Field(default_factory=list)
    influenced_card_titles: list[str] = Field(default_factory=list)
    total_reach: int


class SensemakingCardEvolutionStepResponse(BaseModel):
    """v4.0: 卡片演化步骤。"""
    card_id: str
    card_title: str
    tags: list[str] = Field(default_factory=list)
    wiki_sections: list[str] = Field(default_factory=list)


class SensemakingCardEvolutionResponse(BaseModel):
    """v4.0: 同源卡片演化路径。"""
    source_id: str
    source_label: str
    steps: list[SensemakingCardEvolutionStepResponse] = Field(default_factory=list)
    step_count: int


class SensemakingCommunitySubgraphResponse(BaseModel):
    """v4.0: 社区子图摘要。"""
    community_type: str
    community_label: str
    member_card_ids: list[str] = Field(default_factory=list)
    member_card_titles: list[str] = Field(default_factory=list)
    member_count: int
    internal_edge_count: int
    bridge_card_ids: list[str] = Field(default_factory=list)


class SensemakingResponse(BaseModel):
    """v4.0: 综合 sensemaking 分析结果。

    中文学习型说明：包含桥接节点、孤立岛屿、证据溯源、源影响路径、
    卡片演化路径、社区子图等全部 sensemaking 维度的分析结果。
    用于 Graph-backed Sensemaking Workspace 的数据驱动。
    """
    center_card_id: str
    center_card_title: str
    bridge_nodes: list[SensemakingBridgeNodeResponse] = Field(default_factory=list)
    orphan_islands: list[SensemakingOrphanIslandResponse] = Field(default_factory=list)
    evidence_trails: list[SensemakingEvidenceTrailResponse] = Field(default_factory=list)
    source_influence: SensemakingSourceInfluenceResponse | None = None
    card_evolution: SensemakingCardEvolutionResponse | None = None
    community_subgraphs: list[SensemakingCommunitySubgraphResponse] = Field(default_factory=list)
    total_cards_analyzed: int = 0
